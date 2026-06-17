#!/usr/bin/env python3
"""
Fetch publications from Google Scholar and update index.html.

Uses a single author-profile fill (no per-publication round-trips).

Usage:
    pip install scholarly
    python3 scripts/update_publications.py
"""

import re
import sys
from collections import defaultdict
from datetime import datetime

SCHOLAR_ID   = "T0UW1swAAAAJ"
INDEX_HTML   = "index.html"
AUTHOR_NAMES = ["H Lu", "Haohui Lu", "Lu, H", "Lu, Haohui"]

PUB_START = "<!-- AUTO-PUBS-START -->"
PUB_END   = "<!-- AUTO-PUBS-END -->"


def fetch_publications():
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
        # author-profile fill leaves empty.
        try:
            scholarly.fill(pub, sections=["bib"])
        except Exception as e:  # noqa: BLE001 — keep going on transient failures
            print(f"  WARN: could not fill pub {i}/{total}: {e}")
        bib = pub.get("bib", {})
        pubs.append({
            "title":  bib.get("title", ""),
            "author": bib.get("author", ""),
            "venue":  (bib.get("journal") or bib.get("conference")
                       or bib.get("booktitle") or bib.get("venue") or ""),
            "year":   str(bib.get("pub_year", "")),
            "url":    pub.get("pub_url", ""),
        })
        if i % 10 == 0 or i == total:
            print(f"  filled {i}/{total}")
    return pubs


def abbreviate_author(name):
    """'Syed Talal Ahmad' -> 'ST Ahmad'; 'Haohui Lu' -> 'H Lu'."""
    parts = name.strip().split()
    if len(parts) < 2:
        return name.strip()
    initials = "".join(p[0] for p in parts[:-1] if p)
    return f"{initials} {parts[-1]}"


def format_authors(author_str):
    """Scholar joins authors with ' and '. Abbreviate + comma-separate, bold self."""
    if not author_str:
        return ""
    names = [abbreviate_author(a) for a in author_str.split(" and ")]
    joined = ", ".join(names)
    for name in AUTHOR_NAMES:
        joined = re.sub(
            r'(?<![A-Za-z])' + re.escape(name) + r'(?![A-Za-z])',
            f'<b>{name}</b>',
            joined,
        )
    return joined


def format_pub_item(pub):
    authors = format_authors(pub["author"])
    title   = pub["title"].replace('"', "&quot;")
    venue   = pub["venue"]
    year    = pub["year"]

    parts = [authors, f'"{title}"']
    if venue:
        parts.append(f"<em>{venue}</em>")
    if year:
        parts.append(year)

    item = ", ".join(parts) + "."
    if pub["url"]:
        item += (
            f' <a class="pub-link" href="{pub["url"]}"'
            f' target="_blank" rel="noopener">[link]</a>'
        )
    return f'        <li class="pub-item">{item}</li>'


def build_pubs_html(pubs):
    by_year = defaultdict(list)
    for pub in pubs:
        by_year[pub["year"] or "Unknown"].append(pub)

    lines = []
    for year in sorted(by_year, reverse=True):
        lines += [
            f"    <!-- {year} -->",
            '    <div class="year-group">',
            f'      <div class="year-label">{year}</div>',
            '      <ol class="pub-list">',
        ]
        for pub in by_year[year]:
            lines.append(format_pub_item(pub))
        lines += ["      </ol>", "    </div>", ""]
    return "\n".join(lines)


def update_html(pubs):
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        content = f.read()

    new_block = PUB_START + "\n" + build_pubs_html(pubs) + "\n    " + PUB_END
    pattern = re.escape(PUB_START) + r".*?" + re.escape(PUB_END)
    if not re.search(pattern, content, flags=re.DOTALL):
        print("ERROR: sentinel comments not found in index.html")
        sys.exit(1)
    content = re.sub(pattern, new_block, content, flags=re.DOTALL)

    month_year = datetime.now().strftime("%B %Y")
    content = re.sub(r"Updated: \w+ \d{4}", f"Updated: {month_year}", content)

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"index.html updated. Footer date set to {month_year}.")


def main():
    pubs = fetch_publications()
    update_html(pubs)


if __name__ == "__main__":
    main()
