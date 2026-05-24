#!/usr/bin/env python3
"""
Fetch metrics from Google Scholar and update dashboard.html.

Updates:
  - 5 metric cards (publications, citations, h-index, i10-index, avg cites/paper)
  - Chart data arrays (publications/year, citations/year, avg-cites/paper trajectory)
  - Top-cited papers table (top 5 by citation count)
  - "Last updated" text in hero and footer

Usage:
    pip install scholarly
    python3 scripts/update_dashboard.py
"""

import re
import sys
import time
from collections import defaultdict
from datetime import datetime

SCHOLAR_ID    = "T0UW1swAAAAJ"
DASHBOARD_HTML = "dashboard.html"
START_YEAR    = 2021   # first year to show in charts


# ── helpers ──────────────────────────────────────────────────────────────────

def fetch_data():
    try:
        from scholarly import scholarly
    except ImportError:
        print("ERROR: scholarly not installed. Run: pip install scholarly")
        sys.exit(1)

    print(f"Fetching author profile {SCHOLAR_ID}...")
    author = scholarly.search_author_id(SCHOLAR_ID)
    scholarly.fill(author, sections=["basics", "indices", "counts", "publications"])

    total  = len(author["publications"])
    pubs   = []
    for i, pub in enumerate(author["publications"], 1):
        print(f"  Filling pub {i}/{total}...", end="\r", flush=True)
        try:
            scholarly.fill(pub)
            time.sleep(0.4)
        except Exception as e:
            print(f"\n  Warning: could not fill pub #{i}: {e}")
        bib = pub.get("bib", {})
        venue = (bib.get("journal") or bib.get("conference")
                 or bib.get("booktitle") or "")
        pubs.append({
            "title":     bib.get("title", ""),
            "author":    bib.get("author", ""),
            "venue":     venue,
            "year":      str(bib.get("pub_year", "")),
            "citations": pub.get("num_citations", 0),
            "url":       pub.get("pub_url", ""),
        })
    print(f"\nFetched {total} publications.")
    return {
        "total_citations": author.get("citedby",   0),
        "hindex":          author.get("hindex",    0),
        "i10index":        author.get("i10index",  0),
        "cites_per_year":  author.get("cites_per_year", {}),
        "publications":    pubs,
    }


def compute_series(data):
    """Build year-indexed arrays for the charts."""
    current_year = datetime.now().year
    years = list(range(START_YEAR, current_year + 1))

    # publications per year
    by_year = defaultdict(int)
    for pub in data["publications"]:
        if pub["year"] and pub["year"].isdigit():
            by_year[int(pub["year"])] += 1
    pubs_per_year = [by_year.get(y, 0) for y in years]

    # citations per year (from Scholar's own per-year counts)
    cpy = data["cites_per_year"]
    cites_per_year = [cpy.get(y, 0) for y in years]

    # cumulative avg citations/paper
    cum_pubs = cum_cites = 0
    cpp = []
    for i, y in enumerate(years):
        cum_pubs  += pubs_per_year[i]
        cum_cites += cites_per_year[i]
        cpp.append(round(cum_cites / cum_pubs, 1) if cum_pubs else 0.0)

    return years, pubs_per_year, cites_per_year, cpp


def top5_table_html(pubs):
    """Generate the <tbody> rows for the top-cited papers table."""
    rank_classes = ["rank-gold", "rank-silver", "rank-bronze", "", ""]
    top = sorted(pubs, key=lambda p: p["citations"], reverse=True)[:5]
    max_cites = top[0]["citations"] if top else 1

    rows = []
    for i, pub in enumerate(top):
        pct   = round(pub["citations"] / max_cites * 100, 1)
        rank_cls = f'class="rank {rank_classes[i]}"' if rank_classes[i] else 'class="rank"'
        title = pub["title"] or "Untitled"
        author = pub["author"] or ""
        author = re.sub(
            r'\b(H Lu|Haohui Lu)\b',
            r'<strong>\1</strong>',
            author,
        )
        venue = f"<em>{pub['venue']}</em>" if pub["venue"] else ""
        year  = pub["year"] or "?"
        rows.append(f"""\
        <tr>
          <td {rank_cls}>{i+1}</td>
          <td>
            <div class="paper-title">{title}</div>
            <div class="paper-meta">{author}{' · ' + venue if venue else ''}</div>
            <div class="progress-wrap"><div class="progress-bar"><div class="progress-fill" style="width:{pct}%;"></div></div></div>
          </td>
          <td style="text-align:center;"><span class="year-badge">{year}</span></td>
          <td style="text-align:right; padding-right:20px;"><div class="cites-big">{pub['citations']:,}</div><div class="cites-lbl">citations</div></td>
        </tr>""")
    return "\n".join(rows)


def js_list(values):
    """Format a Python list as a compact JS array literal."""
    return "[" + ", ".join(str(v) for v in values) + "]"


def years_label(years):
    """Format year labels, marking the current year with *."""
    current = datetime.now().year
    labels  = [f"'{y}*'" if y == current else f"'{y}'" for y in years]
    return "[" + ", ".join(labels) + "]"


def update_html(data, years, pubs_per_year, cites_per_year, cpp):
    with open(DASHBOARD_HTML, "r", encoding="utf-8") as f:
        content = f.read()

    total_pubs = len(data["publications"])
    total_cites = data["total_citations"]
    avg_cites   = round(total_cites / total_pubs, 1) if total_pubs else 0
    month_year  = datetime.now().strftime("%B %Y")
    prev_year   = datetime.now().year - 1
    prev_cites  = data["cites_per_year"].get(prev_year, 0)

    # ── metric card values ────────────────────────────────────────────────
    def replace_id(html, elem_id, new_text):
        return re.sub(
            rf'(<[^>]+\bid="{re.escape(elem_id)}"[^>]*>)[^<]*(</)',
            rf'\g<1>{new_text}\2',
            html,
        )

    content = replace_id(content, "m-pubs",       str(total_pubs))
    content = replace_id(content, "m-cites",       f"{total_cites:,}")
    content = replace_id(content, "m-hindex",      str(data["hindex"]))
    content = replace_id(content, "m-i10",         str(data["i10index"]))
    content = replace_id(content, "m-avg",         str(avg_cites))
    content = replace_id(content, "m-pubs-range",  f"{min(years)} – {max(years)}")
    content = replace_id(content, "m-cites-prev",  f"+{prev_cites:,} in {prev_year}")
    content = replace_id(content, "m-avg-date",    f"as of {month_year}")
    content = replace_id(content, "dash-updated",  month_year)
    content = replace_id(content, "dash-footer-updated", month_year)

    # ── JS chart data ─────────────────────────────────────────────────────
    def replace_js(html, tag, new_value):
        return re.sub(
            rf'(//\s*@@AUTO:{re.escape(tag)}@@)',
            lambda m: m.group(0),   # keep comment intact
            re.sub(
                rf'[^\n]*//\s*@@AUTO:{re.escape(tag)}@@',
                f'        data: {new_value}, // @@AUTO:{tag}@@',
                html,
            )
        )

    # Build per-year colors: last year is lighter (partial year)
    colors = ["'#2563eb'"] * (len(years) - 1) + ["'#93c5fd'"]
    colors_str = "[" + ", ".join(colors) + "]"

    content = re.sub(
        r"const YEARS = \[.*?\]; // @@AUTO:years@@",
        f"const YEARS = {years_label(years)}; // @@AUTO:years@@",
        content,
    )
    content = re.sub(
        r"data: \[.*?\], // @@AUTO:pubs-per-year@@",
        f"data: {js_list(pubs_per_year)}, // @@AUTO:pubs-per-year@@",
        content,
    )
    content = re.sub(
        r"backgroundColor: \[.*?\], // @@AUTO:pubs-colors@@",
        f"backgroundColor: {colors_str}, // @@AUTO:pubs-colors@@",
        content,
    )
    content = re.sub(
        r"data: \[.*?\], // @@AUTO:cites-per-year@@",
        f"data: {js_list(cites_per_year)}, // @@AUTO:cites-per-year@@",
        content,
    )
    content = re.sub(
        r"data: \[.*?\], // @@AUTO:cpp-by-year@@",
        f"data: {js_list(cpp)}, // @@AUTO:cpp-by-year@@",
        content,
    )

    # ── top-cited papers table ────────────────────────────────────────────
    new_tbody = (
        "      <!-- AUTO-TOP-CITED-START -->\n"
        "      <tbody>\n"
        + top5_table_html(data["publications"]) + "\n"
        "      </tbody>\n"
        "      <!-- AUTO-TOP-CITED-END -->"
    )
    content = re.sub(
        r"<!-- AUTO-TOP-CITED-START -->.*?<!-- AUTO-TOP-CITED-END -->",
        new_tbody,
        content,
        flags=re.DOTALL,
    )

    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"dashboard.html updated. Date: {month_year}.")


def main():
    data = fetch_data()
    years, pubs_per_year, cites_per_year, cpp = compute_series(data)
    update_html(data, years, pubs_per_year, cites_per_year, cpp)


if __name__ == "__main__":
    main()
