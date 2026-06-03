#!/usr/bin/env python3
"""
Fetch metrics from Google Scholar and update dashboard.html.

Updates ALL auto-marked sections:
  - Metric cards + stat rows
  - Impact Momentum cards
  - Publications/year bar chart
  - Citations/year line chart
  - Avg-cites/paper trajectory
  - Journal vs Conference doughnut
  - Authorship stacked bar + stat row
  - Collaboration horizontal bar
  - Top-cited horizontal bar
  - Top-cited papers table
  - CPP insight text
  - All "last updated" dates

Usage:
    pip install scholarly
    python3 scripts/update_dashboard.py
"""

import re
import sys
import math
from collections import defaultdict, Counter
from datetime import datetime

SCHOLAR_ID     = "T0UW1swAAAAJ"
DASHBOARD_HTML = "dashboard.html"
START_YEAR     = 2021

SELF_NAMES     = ["Haohui Lu", "H Lu", "Lu, Haohui", "Lu, H"]

# Known A* / top-tier venue substrings (case-insensitive)
TOP_TIER_VENUES = [
    "ICLR", "EMNLP", "NeurIPS", "ICML", "ACL", "NAACL",
    "CVPR", "ICCV", "ECCV", "KDD", "WWW", "SIGIR", "AAAI", "IJCAI",
]
# Venue substrings that indicate a conference (not journal)
CONF_KEYWORDS = TOP_TIER_VENUES + [
    "Conference", "Symposium", "Proceedings", "Workshop", "Congress",
    "ACSW", "Australasian", "International Joint",
]


# ── helpers ──────────────────────────────────────────────────────────────────

def is_self(name: str) -> bool:
    return any(s.lower() in name.lower() for s in SELF_NAMES)


def is_first_author(author_str: str) -> bool:
    if not author_str:
        return False
    first = author_str.split(" and ")[0].strip()
    # Also handle comma-separated "Lu, H, Uddin, S, ..."
    if not first:
        first = author_str.split(",")[0].strip()
    return is_self(first)


def is_conference(venue: str) -> bool:
    v = venue.lower()
    return any(k.lower() in v for k in CONF_KEYWORDS)


def is_top_tier(venue: str) -> bool:
    v = venue.lower()
    return any(k.lower() in v for k in TOP_TIER_VENUES)


def abbreviate_name(full: str) -> str:
    """'Shahadat Uddin' → 'S. Uddin'"""
    parts = full.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {parts[-1]}"
    return full


def short_title(title: str, year: str, max_len: int = 28) -> str:
    """Make a compact bar-chart label: 'KNN Variants (2022)'"""
    words = title.split()
    label = []
    for w in words:
        candidate = " ".join(label + [w])
        if len(candidate) <= max_len:
            label.append(w)
        else:
            break
    return (" ".join(label) or title[:max_len]) + f" ({year})"


def js_list(values) -> str:
    return "[" + ", ".join(str(v) for v in values) + "]"


def js_str_list(values) -> str:
    escaped = [v.replace("'", "\\'") for v in values]
    return "[" + ", ".join(f"'{v}'" for v in escaped) + "]"


def years_label(years) -> str:
    cur = datetime.now().year
    return "[" + ", ".join(f"'{y}*'" if y == cur else f"'{y}'" for y in years) + "]"


def replace_id(html: str, elem_id: str, new_text: str) -> str:
    return re.sub(
        rf'(<[^>]+\bid="{re.escape(elem_id)}"[^>]*>)[^<]*(</)',
        rf'\g<1>{new_text}\2',
        html,
    )


def replace_js_line(html: str, tag: str, new_line: str) -> str:
    return re.sub(
        rf'[^\n]*//\s*@@AUTO:{re.escape(tag)}@@',
        new_line,
        html,
    )


def replace_block(html: str, start_marker: str, end_marker: str, new_content: str) -> str:
    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
    replacement = start_marker + "\n" + new_content + "\n  " + end_marker
    return re.sub(pattern, replacement, html, flags=re.DOTALL)


# ── data fetch ───────────────────────────────────────────────────────────────

def fetch_data():
    try:
        from scholarly import scholarly
    except ImportError:
        print("ERROR: scholarly not installed. Run: pip install scholarly")
        sys.exit(1)

    print(f"Fetching author profile {SCHOLAR_ID}...")
    author = scholarly.search_author_id(SCHOLAR_ID)
    scholarly.fill(author, sections=["basics", "indices", "counts", "publications"])
    total = len(author["publications"])
    print(f"Fetched {total} publications. Filling per-publication details...")

    pubs = []
    for i, pub in enumerate(author["publications"], 1):
        # Per-pub fill is required to populate author lists + venue, which the
        # author-profile fill leaves empty. Needed for first-author rate, venue
        # split, collaboration chart, and top-tier detection.
        try:
            scholarly.fill(pub, sections=["bib"])
        except Exception as e:  # noqa: BLE001 — keep going on transient failures
            print(f"  WARN: could not fill pub {i}/{total}: {e}")
        bib = pub.get("bib", {})
        pubs.append({
            "title":     bib.get("title", ""),
            "author":    bib.get("author", ""),
            "venue":     (bib.get("journal") or bib.get("conference")
                          or bib.get("booktitle") or bib.get("venue") or ""),
            "year":      str(bib.get("pub_year", "")),
            "citations": pub.get("num_citations", 0),
            "url":       pub.get("pub_url", ""),
        })
        if i % 10 == 0 or i == total:
            print(f"  filled {i}/{total}")

    return {
        "total_citations": author.get("citedby",   0),
        "hindex":          author.get("hindex",    0),
        "i10index":        author.get("i10index",  0),
        "cites_per_year":  author.get("cites_per_year", {}),
        "publications":    pubs,
    }


# ── computation ──────────────────────────────────────────────────────────────

def compute_series(data):
    cur = datetime.now().year
    years = list(range(START_YEAR, cur + 1))

    by_year = defaultdict(int)
    for pub in data["publications"]:
        if pub["year"] and pub["year"].isdigit():
            by_year[int(pub["year"])] += 1
    pubs_per_year = [by_year.get(y, 0) for y in years]

    cpy = data["cites_per_year"]
    cites_per_year = [cpy.get(y, 0) for y in years]

    cum_pubs = cum_cites = 0
    cpp = []
    for i in range(len(years)):
        cum_pubs  += pubs_per_year[i]
        cum_cites += cites_per_year[i]
        cpp.append(round(cum_cites / cum_pubs, 1) if cum_pubs else 0.0)

    return years, pubs_per_year, cites_per_year, cpp


def authorship_series(data, years):
    """Split pubs by year into first-author vs co-author."""
    first_by_year  = defaultdict(int)
    coauth_by_year = defaultdict(int)
    first_total = coauth_total = 0

    for pub in data["publications"]:
        y = pub["year"]
        if not (y and y.isdigit()):
            continue
        y = int(y)
        if is_first_author(pub.get("author", "")):
            first_by_year[y] += 1
            first_total += 1
        else:
            coauth_by_year[y] += 1
            coauth_total += 1

    return (
        [first_by_year.get(y, 0) for y in years],
        [coauth_by_year.get(y, 0) for y in years],
        first_total,
        coauth_total,
    )


def venue_split(data):
    """Count journal vs conference papers."""
    journals = conferences = 0
    for pub in data["publications"]:
        if is_conference(pub.get("venue", "")):
            conferences += 1
        else:
            journals += 1
    return journals, conferences


def top_collaborators(data, n=7):
    collab_count = Counter()
    for pub in data["publications"]:
        author_str = pub.get("author", "")
        if not author_str:
            continue
        authors = [a.strip() for a in author_str.split(" and ")]
        for a in authors:
            if not is_self(a):
                collab_count[a] += 1

    top = collab_count.most_common(n)
    labels = [abbreviate_name(name) for name, _ in top]
    counts = [cnt for _, cnt in top]
    return labels, counts


def top_cited_bar(data, n=5):
    top = sorted(data["publications"], key=lambda p: p["citations"], reverse=True)[:n]
    labels = [short_title(p["title"], p["year"]) for p in top]
    counts = [p["citations"] for p in top]
    return labels, counts


# ── HTML section generators ───────────────────────────────────────────────────

def momentum_html(data, years, pubs_per_year, cites_per_year, cpp,
                  first_total, coauth_total):
    cur       = datetime.now().year
    prev      = cur - 1
    month     = datetime.now().month
    month_abbr= datetime.now().strftime("%b")

    cur_cites  = data["cites_per_year"].get(cur,  0)
    prev_cites = data["cites_per_year"].get(prev, 0)
    cpm        = round(cur_cites / month, 1) if month else 0

    # Is current year on pace to beat last year?
    pace_vs_prev = (cur_cites / month * 12) if month else 0
    beating_prev = pace_vs_prev > prev_cites

    # Top paper
    top_pub      = sorted(data["publications"],
                          key=lambda p: p["citations"], reverse=True)[0]
    top_cites    = top_pub["citations"]
    total_cites  = data["total_citations"]
    top_pct      = round(top_cites / total_cites * 100, 1) if total_cites else 0

    # Growth multiplier: latest cpp / first NON-ZERO cpp (early years often 0)
    first_cpp   = next((v for v in cpp if v > 0), 0)
    latest_cpp  = cpp[-1]
    multiplier  = round(latest_cpp / first_cpp) if first_cpp > 0 else "?"

    # Venue breakdown for journal %
    journals, conferences = venue_split(data)
    n_total = len(data["publications"])
    journal_pct = round(journals / n_total * 100) if n_total else 0

    # First-author rate
    if first_total + coauth_total > 0:
        fa_pct = round(first_total / (first_total + coauth_total) * 100)
        fa_note = f"{first_total} of {first_total + coauth_total} papers as lead author"
    else:
        fa_pct  = "—"
        fa_note = "Author data unavailable"

    # Top-tier conferences
    top_tier_pubs = [p for p in data["publications"] if is_top_tier(p.get("venue",""))]
    tt_count = len(top_tier_pubs)
    tt_names = " + ".join(
        next((k for k in TOP_TIER_VENUES if k.lower() in p["venue"].lower()), "?")
        for p in top_tier_pubs[:3]
    ) or "—"

    colors = ["var(--accent)", "var(--a2)", "var(--a3)", "var(--a4)", "var(--a5)", "var(--a6)"]
    cards  = [
        {
            "num":   cpm,
            "label": f"Citations per month (Jan–{month_abbr} {cur})",
            "note":  "↑ On pace to beat last year" if beating_prev else "→ Tracking previous year pace",
            "cls":   "note-up" if beating_prev else "note-info",
            "color": colors[0],
        },
        {
            "num":   f"{top_cites:,}",
            "label": f"Citations for top paper",
            "note":  f"{top_pct}% of all citations from 1 paper",
            "cls":   "note-info",
            "color": colors[1],
        },
        {
            "num":   f"{multiplier}×",
            "label": f"Growth in avg citations/paper since {START_YEAR}",
            "note":  f"{first_cpp} → {latest_cpp} citations per paper",
            "cls":   "note-up",
            "color": colors[2],
        },
        {
            "num":   f"{journal_pct}%",
            "label": "Papers in journals (vs. conferences)",
            "note":  f"{journals} journals · {conferences} conferences",
            "cls":   "note-up",
            "color": colors[3],
        },
        {
            "num":   f"{fa_pct}%" if fa_pct != "—" else "—",
            "label": "First-author publication rate",
            "note":  fa_note,
            "cls":   "note-info",
            "color": colors[4],
        },
        {
            "num":   tt_count,
            "label": f"Top-tier venue papers ({tt_names})",
            "note":  "A* rated in CORE ranking",
            "cls":   "note-up",
            "color": colors[5],
        },
    ]

    rows = []
    for c in cards:
        rows.append(
            f'  <div class="momentum-card">\n'
            f'    <div class="momentum-num" style="color:{c["color"]}">{c["num"]}</div>\n'
            f'    <div class="momentum-label">{c["label"]}</div>\n'
            f'    <div class="momentum-note {c["cls"]}">{c["note"]}</div>\n'
            f'  </div>'
        )
    return '<div class="momentum-grid">\n' + "\n".join(rows) + "\n  </div>"


def cpp_insight_html(cpp, years):
    # Use the first NON-ZERO cpp year as the baseline (early years are often 0).
    first_idx  = next((i for i, v in enumerate(cpp) if v > 0), 0)
    first_year = years[first_idx]
    last_year  = years[-1]
    first_val  = cpp[first_idx]
    last_val   = cpp[-1]
    mult       = round(last_val / first_val) if first_val > 0 else "?"

    # Find steepest rise: largest single-year increase
    diffs = [(years[i+1], cpp[i+1] - cpp[i]) for i in range(len(cpp)-1)]
    steepest = max(diffs, key=lambda x: x[1]) if diffs else (years[1], 0)

    return (
        "        <ul>\n"
        f"          <li>{first_year}: {first_val} avg cites/paper → {last_year}: {last_val} ({mult}× growth)</li>\n"
        f"          <li>Steepest rise in {steepest[0]} as papers accumulated citations</li>\n"
        f"          <li>New papers need 1–2 years to accumulate significant citations</li>\n"
        "        </ul>"
    )


def top5_table_html(data):
    rank_classes = ["rank-gold", "rank-silver", "rank-bronze", "", ""]
    top = sorted(data["publications"], key=lambda p: p["citations"], reverse=True)[:5]
    max_cites = top[0]["citations"] if top else 1

    rows = []
    for i, pub in enumerate(top):
        pct      = round(pub["citations"] / max_cites * 100, 1)
        rank_cls = f'class="rank {rank_classes[i]}"' if rank_classes[i] else 'class="rank"'
        title    = pub["title"] or "Untitled"
        author   = pub.get("author", "")
        for sn in SELF_NAMES:
            author = re.sub(rf'\b{re.escape(sn)}\b', f'<strong>{sn}</strong>', author)
        venue    = f"<em>{pub['venue']}</em>" if pub["venue"] else ""
        year     = pub["year"] or "?"
        rows.append(
            f'        <tr>\n'
            f'          <td {rank_cls}>{i+1}</td>\n'
            f'          <td>\n'
            f'            <div class="paper-title">{title}</div>\n'
            f'            <div class="paper-meta">{author}{" · " + venue if venue else ""}</div>\n'
            f'            <div class="progress-wrap"><div class="progress-bar">'
            f'<div class="progress-fill" style="width:{pct}%;"></div></div></div>\n'
            f'          </td>\n'
            f'          <td style="text-align:center;"><span class="year-badge">{year}</span></td>\n'
            f'          <td style="text-align:right; padding-right:20px;">'
            f'<div class="cites-big">{pub["citations"]:,}</div>'
            f'<div class="cites-lbl">citations</div></td>\n'
            f'        </tr>'
        )
    return "\n".join(rows)


# ── main update ──────────────────────────────────────────────────────────────

def update_html(data, years, pubs_per_year, cites_per_year, cpp):
    with open(DASHBOARD_HTML, "r", encoding="utf-8") as f:
        content = f.read()

    cur         = datetime.now().year
    prev        = cur - 1
    month       = datetime.now().month
    month_abbr  = datetime.now().strftime("%b")
    month_year  = datetime.now().strftime("%B %Y")
    total_pubs  = len(data["publications"])
    total_cites = data["total_citations"]
    avg_cites   = round(total_cites / total_pubs, 1) if total_pubs else 0
    prev_cites  = data["cites_per_year"].get(prev, 0)
    cur_cites   = data["cites_per_year"].get(cur,  0)

    # Authorship
    first_py, coauth_py, first_total, coauth_total = authorship_series(data, years)

    # Peak year for publications
    peak_val  = max(pubs_per_year)
    peak_year = years[pubs_per_year.index(peak_val)]

    # Citation growth rate prev-2 → prev
    prev2_cites = data["cites_per_year"].get(prev - 1, 0)
    if prev2_cites > 0:
        growth_pct = round((prev_cites - prev2_cites) / prev2_cites * 100)
        growth_str = f"+{growth_pct}%" if growth_pct >= 0 else f"{growth_pct}%"
    else:
        growth_str = "—"

    # Projected full-year citations
    projected = round(cur_cites / month * 12) if month else cur_cites

    # Venue split
    journals, conferences = venue_split(data)

    # Collaborators
    collab_labels, collab_counts = top_collaborators(data)

    # Top cited bar
    tc_labels, tc_counts = top_cited_bar(data)

    # ── metric card IDs ──────────────────────────────────────────────────────
    for eid, val in [
        ("m-pubs",             str(total_pubs)),
        ("m-cites",            f"{total_cites:,}"),
        ("m-hindex",           str(data["hindex"])),
        ("m-i10",              str(data["i10index"])),
        ("m-avg",              str(avg_cites)),
        ("m-pubs-range",       f"{min(years)} – {max(years)}"),
        ("m-cites-prev",       f"+{prev_cites:,} in {prev}"),
        ("m-avg-date",         f"as of {month_year}"),
        ("dash-updated",       month_year),
        ("dash-footer-updated",month_year),
        # stat rows
        ("s-total-pubs",       str(total_pubs)),
        ("s-avg-per-year",     str(round(total_pubs / len(years), 1))),
        ("s-peak-year",        str(peak_val)),
        ("s-total-cites-r",    f"{total_cites:,}"),
        ("s-growth-rate",      growth_str),
        ("s-projected",        f"~{projected:,}"),
        ("s-topics-n",         f"n = {total_pubs}"),
        # authorship stat row
        ("s-first-author",     str(first_total) if first_total > 0 else "—"),
        ("s-coauthor",         str(coauth_total) if coauth_total > 0 else "—"),
        ("s-lead-rate",
            f"{round(first_total/(first_total+coauth_total)*100)}%"
            if (first_total + coauth_total) > 0 else "—"),
    ]:
        content = replace_id(content, eid, val)

    # peak year label and growth-rate label
    content = replace_id(content, "s-peak-year-lbl",   f"Peak ({peak_year})")
    content = replace_id(content, "s-growth-rate-lbl", f"{prev-1}→{prev}")
    content = replace_id(content, "s-projected-lbl",   f"{cur} Projected")

    # card-sub notes
    content = replace_id(content, "s-partial-year-note",
                         f"{cur}* = partial year (Jan–{month_abbr})")
    content = replace_id(content, "s-cites-projected-note",
                         f"{cur}* = Jan–{month_abbr}, projected ~{projected:,}")

    # ── JS YEARS array ────────────────────────────────────────────────────────
    content = re.sub(
        r"const YEARS = \[.*?\]; // @@AUTO:years@@",
        f"const YEARS = {years_label(years)}; // @@AUTO:years@@",
        content,
    )

    # ── pubs per year chart ───────────────────────────────────────────────────
    colors = ["'#2563eb'"] * (len(years) - 1) + ["'#93c5fd'"]
    content = replace_js_line(content, "pubs-per-year",
        f"        data: {js_list(pubs_per_year)}, // @@AUTO:pubs-per-year@@")
    content = replace_js_line(content, "pubs-colors",
        f"        backgroundColor: {js_list(colors)}, // @@AUTO:pubs-colors@@")

    # ── citations per year chart ───────────────────────────────────────────────
    content = replace_js_line(content, "cites-per-year",
        f"        data: {js_list(cites_per_year)}, // @@AUTO:cites-per-year@@")
    content = replace_js_line(content, "cites-tooltip",
        f"        tooltip: {{ callbacks: {{ label: ctx => `${{ctx.parsed.y}} "
        f"citations${{ctx.dataIndex===YEARS.length-1?' (Jan–{month_abbr} only)':''}}` }} }} "
        f"// @@AUTO:cites-tooltip@@")

    # ── avg cpp chart ─────────────────────────────────────────────────────────
    content = replace_js_line(content, "cpp-by-year",
        f"        data: {js_list(cpp)}, // @@AUTO:cpp-by-year@@")

    # ── venue type doughnut ───────────────────────────────────────────────────
    venue_labels = [f"Journal Articles ({journals})", f"Conference Papers ({conferences})"]
    content = replace_js_line(content, "venue-type-labels",
        f"      labels: {js_str_list(venue_labels)}, // @@AUTO:venue-type-labels@@")
    content = replace_js_line(content, "venue-type-data",
        f"        data: {js_list([journals, conferences])}, // @@AUTO:venue-type-data@@")

    # ── authorship stacked bar ────────────────────────────────────────────────
    content = replace_js_line(content, "first-per-year",
        f"          data: {js_list(first_py)}, // @@AUTO:first-per-year@@")
    content = replace_js_line(content, "coauthor-per-year",
        f"          data: {js_list(coauth_py)}, // @@AUTO:coauthor-per-year@@")

    # ── collaboration chart ───────────────────────────────────────────────────
    if collab_labels:
        content = replace_js_line(content, "collab-labels",
            f"      labels: {js_str_list(collab_labels)}, // @@AUTO:collab-labels@@")
        content = replace_js_line(content, "collab-data",
            f"        data: {js_list(collab_counts)}, // @@AUTO:collab-data@@")

    # ── top-cited bar chart ───────────────────────────────────────────────────
    content = replace_js_line(content, "topcited-labels",
        f"      labels: {js_str_list(tc_labels)}, // @@AUTO:topcited-labels@@")
    content = replace_js_line(content, "topcited-data",
        f"        data: {js_list(tc_counts)}, // @@AUTO:topcited-data@@")

    # ── impact momentum block ─────────────────────────────────────────────────
    mom_html = momentum_html(data, years, pubs_per_year, cites_per_year, cpp,
                             first_total, coauth_total)
    content = replace_block(content,
                            "<!-- AUTO-MOMENTUM-START -->",
                            "<!-- AUTO-MOMENTUM-END -->",
                            "  " + mom_html)

    # ── cpp insight text ──────────────────────────────────────────────────────
    insight = cpp_insight_html(cpp, years)
    content = replace_block(content,
                            "<!-- AUTO-CPP-INSIGHT-START -->",
                            "<!-- AUTO-CPP-INSIGHT-END -->",
                            insight)

    # ── top-cited papers table ────────────────────────────────────────────────
    new_tbody = (
        "      <!-- AUTO-TOP-CITED-START -->\n"
        "      <tbody>\n"
        + top5_table_html(data) + "\n"
        "      </tbody>\n"
        "      <!-- AUTO-TOP-CITED-END -->"
    )
    content = re.sub(
        r"<!-- AUTO-TOP-CITED-START -->.*?<!-- AUTO-TOP-CITED-END -->",
        new_tbody, content, flags=re.DOTALL,
    )

    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"dashboard.html fully updated. Date: {month_year}.")


def main():
    data = fetch_data()
    years, pubs_per_year, cites_per_year, cpp = compute_series(data)
    update_html(data, years, pubs_per_year, cites_per_year, cpp)


if __name__ == "__main__":
    main()
