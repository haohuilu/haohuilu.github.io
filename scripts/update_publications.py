#!/usr/bin/env python3
"""
Fetch publications from Google Scholar and update index.html.

Usage:
    pip install scholarly
    python3 scripts/update_publications.py
"""

import re
import sys
import time
from collections import defaultdict
from datetime import datetime

SCHOLAR_ID = "T0UW1swAAAAJ"
INDEX_HTML = "index.html"
# Any of these strings in the author field gets bolded
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
    scholarly.fill(author, sections=["publications"])

    pubs = []
    total = len(author["publications"])
    for i, pub in enumerate(author["publications"], 1):
        print(f"  Filling publication {i}/{total}...", end="\r")
        try:
            scholarly.fill(pub)
            time.sleep(0.5)  # be polite
        except Exception as e:
            print(f"\n  Warning: could not fill pub #{i}: {e}")
        bib = pub.get("bib", {})
        venue = bib.get("journal") or bib.get("conference") or bib.get("booktitle") or ""
        pubs.append({
            "title":  bib.get("title", ""),
            "author": bib.get("author", ""),
            "venue":  venue,
            "volume": bib.get("volume", ""),
            "number": bib.get("number", ""),
            "pages":  bib.get("pages", ""),
            "year":   str(bib.get("pub_year", "")),
            "url":    pub.get("pub_url", ""),
        })
    print(f"\nFetched {len(pubs)} publications.")
    return pubs


def bold_self(author_str):
    """Wrap the site author's name in <b> tags wherever it appears."""
    for name in AUTHOR_NAMES:
        author_str = re.sub(
            r'(?<![A-Za-z])' + re.escape(name) + r'(?![A-Za-z])',
            f'<b>{name}</b>',
            author_str,
        )
    return author_str


def format_pub_item(pub):
    authors = bold_self(pub["author"])
    title   = pub["title"].replace('"', "&quot;")
    venue   = pub["venue"]
    year    = pub["year"]

    parts = [authors, f'"{title}"']
    if venue:
        parts.append(f"<em>{venue}</em>")
    if pub["volume"]:
        parts.append(pub["volume"])
    if pub["number"]:
        parts.append(f'({pub["number"]})')
    if pub["pages"]:
        parts.append(pub["pages"])
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

    # Replace publications block
    new_block = PUB_START + "\n" + build_pubs_html(pubs) + "\n    " + PUB_END
    pattern = re.escape(PUB_START) + r".*?" + re.escape(PUB_END)
    if not re.search(pattern, content, flags=re.DOTALL):
        print("ERROR: sentinel comments not found in index.html")
        sys.exit(1)
    content = re.sub(pattern, new_block, content, flags=re.DOTALL)

    # Update footer date
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
