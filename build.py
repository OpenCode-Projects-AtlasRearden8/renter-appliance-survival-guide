#!/usr/bin/env python3
"""Build the Renter Appliance Survival Guide static site.

Converts the Markdown files in docs/ into a self-contained static HTML
site (default output: site/). No network access required: everything is
built locally from the files in this repository.

Usage:
    python3 build.py                # build into ./site
    python3 build.py --output DIR   # build into DIR
    python3 build.py --open         # build, then print the index file path
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    import markdown as markdown_lib
except ImportError:  # pragma: no cover - handled with a friendly message
    markdown_lib = None

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
DEFAULT_OUTPUT = ROOT / "site"

MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "smarty"]
MARKDOWN_EXTENSION_CONFIGS: Dict[str, dict] = {}

# Site structure shown in the sidebar, in this exact order.
NAV_PAGES: List[Dict[str, str]] = [
    {"slug": "index", "title": "Home"},
    {"slug": "how-to-use", "title": "How to Use This Guide"},
    {"slug": "dishwasher", "title": "Dishwasher"},
    {"slug": "washer", "title": "Washer"},
    {"slug": "dryer", "title": "Dryer"},
    {"slug": "fridge", "title": "Refrigerator"},
    {"slug": "hvac", "title": "HVAC Basics"},
    {"slug": "reset-basics", "title": "Reset Basics"},
    {"slug": "replace-vs-keep", "title": "Replace vs. Keep"},
    {"slug": "error-code-log-sheet", "title": "Error-Code Log Sheet"},
    {"slug": "call-a-pro-checklist", "title": "Call-a-Pro Checklist"},
    {"slug": "glossary", "title": "Glossary"},
]

# Sidebar pages after these slugs start a new visual section (chapters ->
# tools & reference). CSS adds extra space above their nav entries.
SECTION_BREAKS = {"reset-basics", "error-code-log-sheet"}


def checkbox_inputs(body: str) -> str:
    """Turn '[ ]'/'[x]' list items into real HTML checkboxes.

    Markdown task-list syntax (- [ ]) renders as plain text in stock
    python-markdown; this little pass makes printed checklists usable.
    """
    def replace(match: "re.Match[str]") -> str:
        checked = " checked" if match.group(1) == "x" else ""
        return f"<li><input type=\"checkbox\"{checked}> "
    return re.sub(r"<li>\[( |x)\] ?", replace, body)


def convert_markdown(text: str) -> str:
    """Convert Markdown source to an HTML body fragment."""
    if markdown_lib is None:
        raise SystemExit(
            "The 'markdown' package is required to build this site.\n"
            "Install it with:  python3 -m pip install markdown\n"
            "Then run build.py again."
        )
    body = markdown_lib.markdown(
        text, extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
    return checkbox_inputs(body)


def extract_title(md_text: str) -> str:
    """Return the first '# ' heading, or a fallback title."""
    for line in md_text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return "Renter Appliance Survival Guide"


def internal_links_to_html(md_text: str) -> str:
    """Rewrite relative .md links pointing at built pages as .html links.

    Only links to slugs that exist in docs/ are rewritten; external
    http(s) links and absolute links are left untouched.
    """
    def replace(match: "re.Match[str]") -> str:
        target = match.group(2)
        slug = Path(target).stem
        if not target.lower().startswith(("http://", "https://", "/")) and \
                (DOCS_DIR / f"{slug}.md").exists():
            return f"[{match.group(1)}]({slug}.html)"
        return match.group(0)

    return re.sub(r"\[([^\]]+)\]\(([^)]+\.md)\)", replace, md_text)


def build_page(
    slug: str,
    md_text: str,
    *,
    site_url_prefix: str = "",
) -> str:
    """Render one Markdown document into a full HTML page string."""
    md_text = internal_links_to_html(md_text)
    title = extract_title(md_text)
    body = convert_markdown(md_text)

    nav_items: List[str] = []
    for item in NAV_PAGES:
        is_current = item["slug"] == slug
        classes = []
        if is_current:
            classes.append("current")
        if item["slug"] in SECTION_BREAKS:
            classes.append("section-start")
        nav_items.append(
            f'        <li><a href="{site_url_prefix}{item["slug"]}.html"'
            + (f' class="{" ".join(classes)}"' if classes else "")
            + f">{html.escape(item['title'])}</a></li>"
        )

    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Renter Appliance Survival Guide</title>
<meta name="description" content="A friendly, plain-English manual for dishwasher, washer, dryer, refrigerator, and HVAC care: what error codes really mean, what to clean monthly, when to call a pro, and reset basics.">
<link rel="stylesheet" href="{site_url_prefix}style.css">
</head>
<body>
<div class="layout">
  <header class="masthead">
    <p class="site-title"><a href="{site_url_prefix}index.html">The Renter Appliance Survival Guide</a></p>
    <p class="site-tagline">Appliances, decoded. No toolbox confidence required.</p>
    <p class="site-credit">by Asdale Dynamics, LLC</p>
  </header>
  <nav class="sidebar" aria-label="Chapters">
    <ul>
{chr(10).join(nav_items)}
    </ul>
  </nav>
  <main class="content" id="main">
{body}
  </main>
  <footer class="footer">
    <p><strong>The Renter Appliance Survival Guide</strong> — general education, not a substitute for your appliance's manual or a licensed technician. Safety first: gas smells, burning smells, and water near power are <a href="{site_url_prefix}call-a-pro-checklist.html">call-a-pro</a> territory.</p>
    <p>© 2026 Asdale Dynamics, LLC · MIT licensed · <a href="https://dylanasdale.github.io">dylanasdale.github.io</a></p>
  </footer>
</div>
</body>
</html>
"""
    return template


def build_site(docs_dir: Path = DOCS_DIR, output_dir: Path = DEFAULT_OUTPUT) -> List[Path]:
    """Build the full static site. Returns the list of HTML files written."""
    if not docs_dir.is_dir():
        raise SystemExit(f"Docs directory not found: {docs_dir}")

    md_files = sorted(docs_dir.glob("*.md"))
    if not md_files:
        raise SystemExit(f"No Markdown files found in {docs_dir}")

    # Every page in NAV_PAGES must have a source document (index.md builds
    # index.html).
    by_slug = {p.stem: p for p in md_files}
    missing = [item["slug"] for item in NAV_PAGES if item["slug"] not in by_slug]
    if missing:
        raise SystemExit(f"Missing docs for nav entries: {', '.join(missing)}")
    # And every document that isn't in the nav would be orphaned on the site.
    orphaned = sorted(set(by_slug) - {item["slug"] for item in NAV_PAGES})
    if orphaned:
        raise SystemExit(f"Docs not wired into NAV_PAGES: {', '.join(orphaned)}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for slug, source in by_slug.items():
        md_text = source.read_text(encoding="utf-8")
        html_page = build_page(slug, md_text)
        target = output_dir / f"{slug}.html"
        target.write_text(html_page, encoding="utf-8")

    copy_assets(output_dir)
    return sorted(output_dir.glob("*.html"))


ASSETS: Dict[str, str] = {}

STYLE_CSS = """:root {
  --ink: #22303a;
  --paper: #fbf9f5;
  --card: #ffffff;
  --accent: #1d7d8c;
  --accent-dark: #14596a;
  --warn: #b3492e;
  --line: #e4ded3;
  --soft: #f2eee6;
  --radius: 10px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: "Georgia", "Iowan Old Style", serif;
  font-size: 17px;
  line-height: 1.65;
  color: var(--ink);
  background: var(--paper);
}
.layout {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px 60px;
}
.masthead {
  padding: 34px 0 18px;
  border-bottom: 3px double var(--line);
  margin-bottom: 24px;
}
.site-title { margin: 0; font-size: 1.55em; }
.site-title a { color: var(--ink); text-decoration: none; }
.site-title a:hover { color: var(--accent); }
.site-tagline { margin: 6px 0 0; font-style: italic; color: #5c6b76; }
.site-credit { margin: 4px 0 0; font-size: 0.85em; color: #8a959e; }
.layout { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 30px; }
.masthead { grid-column: 1 / -1; }
.sidebar {
  position: sticky;
  top: 16px;
  align-self: start;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 10px;
}
.sidebar ul { list-style: none; margin: 0; padding: 0; }
.sidebar li { margin: 2px 0; }
.sidebar a {
  display: block;
  padding: 6px 12px;
  border-radius: 7px;
  color: #3c4a54;
  text-decoration: none;
  font-size: 0.92em;
}
.sidebar a:hover { background: var(--soft); }
.sidebar a.current { background: var(--accent); color: #fff; font-weight: bold; }
.sidebar a.section-start { margin-top: 12px; border-top: 1px dashed var(--line); padding-top: 12px; }
.content {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 28px 34px;
}
.content h1 { font-size: 1.7em; margin: 0 0 18px; line-height: 1.25; }
.content h2 {
  margin-top: 2em;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
  font-size: 1.25em;
}
.content h3 { margin-top: 1.8em; font-size: 1.08em; color: var(--accent-dark); }
.content code {
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 1px 6px;
  font-size: 0.85em;
  font-family: "Menlo", "Consolas", monospace;
  color: #14425a;
}
.content pre { background: var(--soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 18px; overflow-x: auto; }
.content pre code { border: none; background: none; padding: 0; }
.content table { border-collapse: collapse; width: 100%; margin: 1.2em 0; font-size: 0.93em; }
.content th, .content td { border: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; }
.content th { background: var(--soft); }
.content tr:nth-child(even) td { background: #fcfaf7; }
.content blockquote {
  margin: 1.4em 0;
  padding: 12px 20px;
  border-left: 5px solid var(--accent);
  background: var(--soft);
  border-radius: 0 var(--radius) var(--radius) 0;
  font-style: italic;
}
.content blockquote p { margin: 0.4em 0; }
.content a { color: var(--accent-dark); }
.content a:hover { color: var(--accent); }
.content li { margin: 0.35em 0; }
.content input[type="checkbox"] { margin-right: 4px; }
.content strong em, .content em strong { color: var(--warn); }
.footer {
  grid-column: 1 / -1;
  margin-top: 40px;
  border-top: 3px double var(--line);
  padding-top: 16px;
  font-size: 0.85em;
  color: #6b7780;
}
@media (max-width: 860px) {
  .layout { display: block; }
  .sidebar { position: static; margin-bottom: 20px; }
  .content { padding: 20px; }
}
"""


def copy_assets(output_dir: Path) -> None:
    """Write static assets (CSS) into the output directory."""
    (output_dir / "style.css").write_text(STYLE_CSS, encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Renter Appliance Survival Guide static site."
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help="Output directory (default: ./site)",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Print the path of the built index.html after building.",
    )
    args = parser.parse_args(argv)

    pages = build_site(output_dir=args.output)
    print(f"Built {len(pages)} pages into {args.output}")
    if args.open:
        index = args.output / "index.html"
        print(f"Open this file in a browser: file://{index.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
