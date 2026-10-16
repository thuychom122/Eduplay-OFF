import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _read(rel):
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(os.path.join(base, rel), "r", encoding="utf-8") as f:
        return f.read()


class TestGameScrollAndFavicon(unittest.TestCase):
    def test_classic_intro_scrolls(self):
        from eduplay.core import export_service as es_mod
        import inspect

        src = inspect.getsource(es_mod.ExportService._generate_quiz_game_html)
        self.assertIn(".intro-screen{", src)
        self.assertIn("overflow-y:auto", src)

    def test_fishing_start_overlay_scrolls(self):
        content = _read(os.path.join("assets_bundle", "templates_fish", "fishing_game.html"))
        self.assertIn('id="start-overlay"', content)
        self.assertIn("overflow-y:auto", content)
        self.assertIn("max-height:94vh", content)
        self.assertIn("padding:12px 12px 64px", content)

    def test_millionaire_menu_scrolls(self):
        content = _read(os.path.join("assets_bundle", "millionaire", "index.html"))
        self.assertIn("#mainMenu{", content)
        self.assertIn("overflow-y: auto", content)
        self.assertIn("padding-bottom: 120px", content)
        # footer auto-hide watcher also covers the menu scroller
        self.assertIn("getElementById('mainMenu')", content)
        self.assertIn("mm.scrollTop", content)
        self.assertIn("mm.addEventListener('scroll'", content)

    def test_viewer_pages_have_favicon(self):
        base = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "firebase_hosting"))
        for name in ("firebase_viewer.html", "index.html"):
            with open(os.path.join(base, name), "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn('rel="icon"', content, name)


if __name__ == "__main__":
    unittest.main()
