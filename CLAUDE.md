# Academic Personal Website — Haohui Lu

Personal academic website for Dr. Haohui Lu, Research Fellow at the Molly Wardaguga Institute, Charles Darwin University, Australia. Currently recruiting PhD candidates in AI for Health.

## Tech Stack

Plain HTML + CSS (no build step, no framework). Single-page `index.html` with embedded styles.

## Commands

- **Dev:** Open `index.html` directly in a browser (no server needed), or `python3 -m http.server 8080`
- **Deploy:** `git push origin main` (GitHub Pages or Netlify — TBD)

## Site Structure

Single file: `index.html` — sections linked via anchor IDs:
- `#about` — Bio, photo, social links, recruiting notice
- `#research` — Three research area cards
- `#publications` — Grouped by year, numbered
- `#experience` — Academic + education + industry timelines
- `#teaching` — USyd casual academic table
- `#contact` — Email, address, profiles

Static assets (to be added):
- `static/files/cv.pdf` — CV download (keep this path stable)
- `static/files/photo.jpg` — Profile photo (swap the placeholder initials in `.photo-placeholder`)

## About Haohui

- Title: Research Fellow, Molly Wardaguga Institute, Faculty of Health, CDU
- Email: haohui.lu[at]cdu.edu.au
- PhD: Data Science, University of Sydney (conferred March 2024)
- Thesis: "Chronic Disease Prediction using Graph Machine Learning"
- Research areas: Graph ML, LLMs, AI in Healthcare, Indigenous Data Sovereignty
- Profiles: Google Scholar, ResearchGate, LinkedIn, CDU Research Profile

## Content Conventions

- Publications sorted by year (descending), numbered sequentially top-to-bottom
- First-author papers get `badge-first` badge; distinguish journal (`badge-jour`) vs conference (`badge-conf`)
- Citation format: Author(s), "Title", *Journal/Conference*, Volume, Pages, Year
- Use `href` anchors for DOIs — do not hardcode full DOI strings in visible text
- Email must remain obfuscated in HTML: `haohui.lu [at] cdu.edu.au` — never render as a mailto link
- Tone: professional academic, no marketing language
- Indigenous Data Sovereignty work should be mentioned sensitively and accurately
- Last updated: April 2026

## Placeholders to Replace

- Profile photo: uncomment `<img>` in `.photo-placeholder` and remove the initials `HL`
- Social profile URLs: update `href` on Google Scholar, ResearchGate, LinkedIn, CDU Profile links
- Publication entries: replace placeholder titles/authors/venues with real citation data and DOI links
- Teaching course codes/years: verify against actual teaching records
- Education university names marked `[TBA]`
- Industry company name marked `[TBA]`
- PhD supervisor names marked `[TBA]`

## Warnings

- Do NOT edit any auto-generated `public/` or `_site/` directory
- Publications list is the source of truth — avoid duplicating data across files
- PhD recruiting notice must appear prominently on the homepage
