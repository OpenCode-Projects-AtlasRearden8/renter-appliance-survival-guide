"""Tests for the Renter Appliance Survival Guide build pipeline.

Run with:  python3 -m unittest discover -s tests -v
"""

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
sys_path_added = False
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))
    sys_path_added = True

import build  # noqa: E402  (needs ROOT on sys.path, handled above)


class TestDocsSource(unittest.TestCase):
    """Every source document should be complete and well-formed."""

    def setUp(self):
        self.md_slugs = sorted(p.stem for p in DOCS_DIR.glob("*.md"))

    def test_required_documents_exist(self):
        expected = {item["slug"] for item in build.NAV_PAGES}
        missing = expected - set(self.md_slugs)
        self.assertEqual(missing, set(), f"missing docs: {missing}")

    def test_every_doc_starts_with_h1_title(self):
        for fp in sorted(DOCS_DIR.glob("*.md")):
            with self.subTest(doc=fp.name):
                first_heading = next(
                    (line for line in fp.read_text(encoding="utf-8").splitlines()
                     if line.startswith("# ")), None)
                self.assertIsNotNone(
                    first_heading, f"{fp.name} has no '# Title' heading")

    def test_unique_page_titles(self):
        titles = {}
        for fp in sorted(DOCS_DIR.glob("*.md")):
            title = build.extract_title(fp.read_text(encoding="utf-8"))
            self.assertNotIn(title, titles,
                             f"'{title}' used by both {titles.get(title)} and {fp.name}")
            titles[title] = fp.name

    def test_no_stray_non_ascii_script_marks(self):
        # Legit punctuation (em-dashes, curly quotes) is fine; accidental
        # CJK/Cyrillic characters from editing slips are not.
        for fp in sorted(DOCS_DIR.glob("*.md")):
            text = fp.read_text(encoding="utf-8")
            stray = re.findall(r"[\u4e00-\u9fff\u3040-\u30ff\u0400-\u04ff]", text)
            self.assertEqual(
                stray, [], f"{fp.name} contains stray non-English characters: {stray}")


class TestLinkRewriting(unittest.TestCase):
    def test_existing_md_link_rewritten_to_html(self):
        out = build.internal_links_to_html("see [home](index.md) please")
        self.assertEqual(out, "see [home](index.html) please")

    def test_known_doc_link_rewritten(self):
        out = build.internal_links_to_html("read [glossary](glossary.md)")
        self.assertEqual(out, "read [glossary](glossary.html)")

    def test_missing_target_left_untouched(self):
        out = build.internal_links_to_html("read [nope](not-a-doc.md)")
        self.assertEqual(out, "read [nope](not-a-doc.md)")

    def test_external_links_untouched(self):
        text = "visit [Hub](https://example.com/page.md) and [elsewhere](x.md) ok"
        out = build.internal_links_to_html(text)
        self.assertIn("(https://example.com/page.md)", out)

    def test_all_doc_crosslinks_resolve(self):
        # Any .md link appearing in docs/ should point at a doc that exists,
        # so the generated site never 404s on internal links.
        pattern = re.compile(r"\]\(([^)#]+\.md)\)")
        for fp in sorted(DOCS_DIR.glob("*.md")):
            for target in pattern.findall(fp.read_text(encoding="utf-8")):
                slug = Path(target).stem
                self.assertIn(
                    slug, {p.stem for p in DOCS_DIR.glob("*.md")},
                    f"{fp.name} links to missing doc {target}")


class TestConvertMarkdown(unittest.TestCase):
    def test_heading_conversion(self):
        self.assertIn("<h2>", build.convert_markdown("## Hello"))

    def test_table_conversion(self):
        html = build.convert_markdown("| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertIn("<table>", html)
        self.assertIn("<td>2</td>", html)

    def test_task_list_becomes_checkboxes(self):
        html = build.convert_markdown("- [x] done item\n- [ ] open item")
        self.assertIn('<input type="checkbox" checked>', html)
        self.assertIn('<input type="checkbox">', html)
        self.assertNotIn("[x] done", html)


class TestBuildPage(unittest.TestCase):
    def setUp(self):
        self.md = DOCS_DIR / "index.md"
        self.page = build.build_page("index", self.md.read_text(encoding="utf-8"))

    def test_has_doctype_and_title(self):
        self.assertTrue(self.page.startswith("<!DOCTYPE html>"))
        title = build.extract_title(self.md.read_text(encoding="utf-8"))
        self.assertIn(f"<title>{title}", self.page)

    def test_nav_contains_all_pages_once(self):
        nav_start = self.page.index('<nav class="sidebar"')
        nav_end = self.page.index('</nav>')
        nav_block = self.page[nav_start:nav_end]
        for item in build.NAV_PAGES:
            self.assertEqual(
                nav_block.count(f'href="{item["slug"]}.html"'), 1,
                f"nav missing or duplicated: {item['slug']}")

    def test_current_page_marked(self):
        self.assertIn('class="current"', self.page)

    def test_footer_credit(self):
        self.assertIn("Asdale Dynamics, LLC", self.page)

    def test_safety_disclaimer_present(self):
        self.assertIn("not a substitute", self.page)

    def test_no_html_escaping_breakage(self):
        # Titles containing & or < should be escaped in <title> and nav.
        page = build.build_page("glossary", (DOCS_DIR / "glossary.md").read_text(encoding="utf-8"))
        self.assertIn("Glossary", page)


class TestFullSiteBuild(unittest.TestCase):
    """End-to-end: build the real docs/ into a temp dir."""

    def test_build_site_produces_pages_and_assets(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "site"
            pages = build.build_site(output_dir=out)
            slugs = [p.stem for p in pages]
            expected = [item["slug"] for item in build.NAV_PAGES]
            self.assertEqual(slugs, sorted(expected))
            for page in pages:
                self.assertGreater(
                    page.stat().st_size, 500, f"{page.name} looks empty")
            self.assertTrue((out / "style.css").exists())
            self.assertGreater((out / "style.css").stat().st_size, 500)

    def test_index_links_to_every_page(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "site"
            build.build_site(output_dir=out)
            index = (out / "index.html").read_text(encoding="utf-8")
            # The index body link-lists every chapter/tool page.
            for item in build.NAV_PAGES:
                slug = item["slug"]
                self.assertIn(
                    f'{slug}.html', index,
                    f"index.html does not link to {slug}")

    def test_broken_source_errors_clearly(self):
        empty_dir = Path(tempfile.mkdtemp())  # cleaned below
        try:
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "site"
                with self.assertRaises(SystemExit):
                    build.build_site(docs_dir=empty_dir, output_dir=out)
        finally:
            import shutil
            shutil.rmtree(empty_dir)


if __name__ == "__main__":
    unittest.main()
