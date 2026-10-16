import json
import os
import sys
import unittest

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QWidget


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


SCREENS = ("browser", "new_project", "player", "editor", "editor_quiz", "editor_fishing")

# onboarding.* keys wired by _SCREEN_GUIDE_SPECS (must exist in all langs).
ONBOARDING_KEYS = [
    "onboarding.step_sidebar",
    "onboarding.step_chat",
    "onboarding.step_help",
    "onboarding.step_settings",
    "onboarding.browser.edit.back",
    "onboarding.browser.edit.search",
    "onboarding.browser.edit.filter",
    "onboarding.browser.edit.import",
    "onboarding.browser.edit.refresh",
    "onboarding.new_project.back",
    "onboarding.new_project.name",
    "onboarding.new_project.desc",
    "onboarding.new_project.type",
    "onboarding.new_project.create",
    "onboarding.player.list.back",
    "onboarding.editor.header.back",
    "onboarding.editor.header.save",
    "onboarding.editor.header.preview",
    "onboarding.editor.header.export_web",
    "onboarding.editor.header.export_html",
    "onboarding.editor.questions.add",
    "onboarding.editor.questions.import",
    "onboarding.editor.questions.list",
    "onboarding.editor.questions.tabs",
]


class _StubSettings:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def get_language(self):
        return self._data.get("app_language", "en")


class _FakeSignal:
    def __init__(self):
        self._cb = None

    def connect(self, cb):
        self._cb = cb


def _make_window():
    from eduplay.ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.settings_manager = _StubSettings()
    window._startup_home_fade_done = True
    window._startup_overlay = None
    window._pending_first_run_onboarding = False
    return window


def _make_screen(widgets):
    screen = QWidget()
    for name, widget in widgets.items():
        setattr(screen, name, widget)
        widget.setParent(screen)
        widget.show()
    screen.show()
    return screen


def _patched_overlay_module():
    import eduplay.ui.widgets.coach_marks_overlay as overlay_mod

    created = []

    class FakeOverlay:
        def __init__(self, parent, marks, lang="en", **kwargs):
            created.append({"marks": marks, "lang": lang})
            self.finished = _FakeSignal()

        def show(self):
            pass

        def raise_(self):
            pass

        def activateWindow(self):
            pass

    real_cls = overlay_mod.CoachMarksOverlay
    overlay_mod.CoachMarksOverlay = FakeOverlay
    return overlay_mod, real_cls, created


class TestScreenGuidesI18n(unittest.TestCase):
    def test_guide_keys_exist_in_all_languages(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n")
        )
        for lang in ("en", "vi", "fr", "de", "es"):
            with open(os.path.join(base_dir, f"{lang}.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            for screen in SCREENS:
                for idx in (1, 2, 3):
                    key = f"guide.{screen}.{idx}"
                    self.assertIn(key, data, f"Missing key '{key}' in {lang}.json")
                    self.assertTrue(data[key].strip())


class TestScreenGuideMarks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_browser_marks_from_visible_widgets(self):
        window = _make_window()
        window.browser_screen = _make_screen(
            {
                "back_btn": QPushButton("back"),
                "search_input": QLabel("search"),
                "filter_combo": QPushButton("filter"),
                "open_btn": QPushButton("open"),
                "rename_btn": QPushButton("rename"),
                "del_btn": QPushButton("del"),
                "menu_btn": QPushButton("menu"),
                "import_btn": QPushButton("import"),
                "refresh_btn": QPushButton("refresh"),
            }
        )
        marks = window._screen_guide_marks("browser", "en")
        self.assertEqual(len(marks), 9)
        for _, text in marks:
            self.assertTrue(text.strip())

    def test_hidden_widgets_are_skipped(self):
        window = _make_window()
        hidden = QPushButton("import")
        window.browser_screen = _make_screen(
            {
                "back_btn": QPushButton("back"),
                "search_input": QLabel("search"),
                "filter_combo": QPushButton("filter"),
                "open_btn": QPushButton("open"),
                "rename_btn": QPushButton("rename"),
                "del_btn": QPushButton("del"),
                "menu_btn": QPushButton("menu"),
                "import_btn": hidden,
                "refresh_btn": QPushButton("refresh"),
            }
        )
        hidden.hide()
        marks = window._screen_guide_marks("browser", "en")
        self.assertEqual(len(marks), 8)

    def test_nested_widget_paths(self):
        window = _make_window()
        left_panel = QWidget()
        add_btn = QPushButton("add")
        setattr(left_panel, "add_btn", add_btn)
        add_btn.setParent(left_panel)
        add_btn.show()
        left_panel.show()
        editor = QWidget()
        editor.left_panel = left_panel
        left_panel.setParent(editor)
        for name in (
            "back_btn",
            "save_btn",
            "preview_btn",
            "export_web_btn",
            "export_html_btn",
        ):
            btn = QPushButton(name)
            setattr(editor, name, btn)
            btn.setParent(editor)
            btn.show()
        import_btn = QPushButton("import")
        setattr(left_panel, "import_btn", import_btn)
        import_btn.setParent(left_panel)
        import_btn.show()
        questions_list = QLabel("list")
        setattr(left_panel, "questions_list", questions_list)
        questions_list.setParent(left_panel)
        questions_list.show()
        tab_widget = QLabel("tabs")
        setattr(left_panel, "tab_widget", tab_widget)
        tab_widget.setParent(left_panel)
        tab_widget.show()
        editor.show()
        window.editor_screen = editor
        marks = window._screen_guide_marks("editor", "en")
        self.assertEqual(len(marks), 9)

    def test_unknown_screen_returns_no_marks(self):
        window = _make_window()
        self.assertEqual(window._screen_guide_marks("nope", "en"), [])

    def test_guide_shows_once_then_seen_flag_blocks(self):
        window = _make_window()
        window.browser_screen = _make_screen(
            {
                "search_input": QLabel("search"),
                "open_btn": QPushButton("open"),
                "import_btn": QPushButton("import"),
            }
        )
        overlay_mod, real_cls, created = _patched_overlay_module()
        try:
            window._maybe_show_screen_guide("browser")
            self.assertEqual(len(created), 1)
            self.assertEqual(len(created[0]["marks"]), 3)
            window.settings_manager.set("guides.browser.seen", True)
            window._maybe_show_screen_guide("browser")
            self.assertEqual(len(created), 1)
        finally:
            overlay_mod.CoachMarksOverlay = real_cls

    def test_global_dismiss_blocks_guide(self):
        window = _make_window()
        window.browser_screen = _make_screen({"search_input": QLabel("s")})
        window.settings_manager.set("onboarding.dismissed", True)
        overlay_mod, real_cls, created = _patched_overlay_module()
        try:
            window._maybe_show_screen_guide("browser")
        finally:
            overlay_mod.CoachMarksOverlay = real_cls
        self.assertEqual(created, [])

    def test_step_by_step_next_then_done_on_last(self):
        from eduplay.ui.widgets.coach_marks_overlay import CoachMarksOverlay

        parent = QWidget()
        parent.resize(800, 600)
        targets = []
        for i in range(3):
            lbl = QLabel(f"t{i}", parent)
            lbl.setGeometry(100, 100 + i * 120, 160, 48)
            lbl.show()
            targets.append(lbl)
        parent.show()

        overlay = CoachMarksOverlay(
            parent, [(t, f"tip{i}") for i, t in enumerate(targets)], lang="vi", group_size=1
        )
        # Page 0/2: only "Tiếp tục" shows, "Xong" stays hidden.
        self.assertFalse(overlay._next_btn.isHidden())
        self.assertTrue(overlay._done_btn.isHidden())

        overlay._on_next_clicked()
        # Page 1/2: still stepping.
        self.assertFalse(overlay._next_btn.isHidden())
        self.assertTrue(overlay._done_btn.isHidden())

        overlay._on_next_clicked()
        # Page 2/2 (last): only "Xong" shows; "Tiếp tục" hides.
        self.assertTrue(overlay._next_btn.isHidden())
        self.assertFalse(overlay._done_btn.isHidden())

        received = []
        overlay.finished.connect(received.append)
        overlay._on_done_clicked()
        self.assertEqual(received, [False])

    def test_guide_marks_use_vietnamese_text(self):
        window = _make_window()
        window.player_screen = _make_screen(
            {
                "back_btn": QPushButton("back"),
                "project_combo": QPushButton("combo"),
                "open_file_btn": QPushButton("file"),
                "open_btn": QPushButton("open"),
                "reload_btn": QPushButton("reload"),
            }
        )
        marks = window._screen_guide_marks("player", "vi")
        self.assertEqual(len(marks), 5)
        self.assertTrue(any("dự án" in text for _, text in marks))

    def test_wired_onboarding_keys_exist_in_all_languages(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n")
        )
        for lang in ("en", "vi", "fr", "de", "es"):
            with open(os.path.join(base_dir, f"{lang}.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in ONBOARDING_KEYS:
                self.assertIn(key, data, f"Missing key '{key}' in {lang}.json")
                self.assertTrue(data[key].strip())

    def test_every_spec_key_resolves_to_real_text(self):
        """Regression guard: every i18n key referenced by
        _SCREEN_GUIDE_SPECS must exist (non-empty) in all 5 locales,
        otherwise the overlay would render the raw key string.
        """
        import eduplay.ui.main_window as mw_mod

        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n")
        )
        locales = {}
        for lang in ("en", "vi", "fr", "de", "es"):
            with open(os.path.join(base_dir, f"{lang}.json"), "r", encoding="utf-8") as f:
                locales[lang] = json.load(f)
        for screen, (_attr, items) in mw_mod._SCREEN_GUIDE_SPECS.items():
            self.assertTrue(items, f"Empty spec for {screen}")
            for _widget_attr, key in items:
                for lang in ("en", "vi", "fr", "de", "es"):
                    self.assertIn(key, locales[lang], f"Missing key '{key}' ({screen}) in {lang}.json")
                    self.assertTrue(
                        locales[lang][key].strip(), f"Empty key '{key}' ({screen}) in {lang}.json"
                    )


if __name__ == "__main__":
    unittest.main()
