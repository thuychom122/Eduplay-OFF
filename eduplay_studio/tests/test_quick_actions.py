import os
import sys
import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication, QMainWindow


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _StubSettings:
    def __init__(self, recent=None):
        self._recent = list(recent or [])
        self.tracked = []

    def get_recent_projects(self):
        return list(self._recent)

    def add_recent_project(self, pid, name=""):
        self.tracked.append((pid, name))

    def get(self, key, default=None):
        return default

    def set(self, key, value):
        pass

    def get_language(self):
        return "vi"


class _FakePlayer:
    def __init__(self):
        self.loaded = []
        self.selected = []

    def load_project_game(self, project_data):
        self.loaded.append(project_data)

    def _set_selected_project(self, meta):
        self.selected.append(meta)


def _make_drawer():
    from eduplay.ui.widgets.left_nav_drawer import LeftNavDrawer

    drawer = LeftNavDrawer()
    drawer.set_language("vi")
    return drawer


def _make_window(recent=None):
    from eduplay.ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.settings_manager = _StubSettings(recent=recent)
    window._shown = []
    window._loaded_by_id = {}
    window.show_screen = lambda name: window._shown.append(name)
    window._load_project_by_id = lambda pid: window._loaded_by_id.get(pid)
    window.player_screen = _FakePlayer()
    return window


class TestDrawerQuickButtons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_buttons_emit_play_recent_and_screenshot(self):
        drawer = _make_drawer()
        self.assertEqual(drawer.btn_recent.property("actionKey"), "play_recent")
        self.assertEqual(drawer.btn_publish.property("actionKey"), "screenshot")
        self.assertEqual(drawer.btn_resume.property("actionKey"), "resume")

        received = []
        drawer.quick_action_requested.connect(received.append)
        drawer.btn_recent.click()
        drawer.btn_publish.click()
        drawer.btn_resume.click()
        self.assertEqual(received, ["play_recent", "screenshot", "resume"])

    def test_buttons_show_vietnamese_labels(self):
        drawer = _make_drawer()
        self.assertIn("Chơi", drawer.btn_recent.property("displayText"))
        self.assertIn("Chụp", drawer.btn_publish.property("displayText"))


class TestQuickActionHandlers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_play_recent_opens_player_with_latest_project(self):
        window = _make_window(recent=[{"id": "p1"}, {"id": "p0"}])
        window._loaded_by_id = {"p1": {"id": "p1", "name": "Demo"}}
        window._handle_left_nav_quick_action("play_recent")
        self.assertEqual(window._shown, ["player"])
        self.assertEqual(window.player_screen.loaded, [{"id": "p1", "name": "Demo"}])
        self.assertEqual(window.player_screen.selected, [{"id": "p1"}])

    def test_play_recent_without_projects_falls_back_to_browser(self):
        window = _make_window(recent=[])
        with mock.patch(
            "eduplay.ui.main_window.QMessageBox.information", return_value=None
        ) as fake_info:
            window._handle_left_nav_quick_action("play_recent")
        self.assertEqual(window._shown, ["browser"])
        self.assertEqual(window.player_screen.loaded, [])
        fake_info.assert_called_once()

    def test_play_recent_with_stale_recents_warns_not_found(self):
        window = _make_window(recent=[{"id": "ghost1"}, {"id": "ghost2"}])
        with mock.patch(
            "eduplay.ui.main_window.QMessageBox.information", return_value=None
        ) as fake_info:
            window._handle_left_nav_quick_action("play_recent")
        self.assertEqual(window._shown, ["browser"])
        args, _kwargs = fake_info.call_args
        self.assertTrue(str(args[1]).strip())
        self.assertTrue(str(args[2]).strip())

    def test_screenshot_minimizes_first_then_schedules_overlay(self):
        from PySide6.QtCore import QTimer

        window = _make_window()
        scheduled = []
        real_single_shot = QTimer.singleShot
        QTimer.singleShot = staticmethod(lambda ms, fn: scheduled.append((ms, fn)))
        try:
            window._handle_left_nav_quick_action("screenshot")
        finally:
            QTimer.singleShot = real_single_shot
        self.assertTrue(window.isMinimized())
        self.assertEqual(len(scheduled), 1)
        self.assertEqual(scheduled[0][0], 450)

    def test_screenshot_launches_snipping_overlay(self):
        window = _make_window()
        with mock.patch("os.startfile", create=True) as fake_start:
            window._launch_snipping_overlay()
        fake_start.assert_called_once_with("ms-screenclip:")

    def test_screenshot_falls_back_to_snipping_tool(self):
        window = _make_window()
        with mock.patch("os.startfile", create=True, side_effect=OSError("nope")):
            with mock.patch("subprocess.Popen") as fake_popen:
                window._launch_snipping_overlay()
        fake_popen.assert_called_once_with(["SnippingTool.exe", "/clip"])

    def test_opening_project_tracks_recent(self):
        window = _make_window()
        window._track_recent_project({"id": "p9", "name": "Bai 9"})
        self.assertEqual(window.settings_manager.tracked, [("p9", "Bai 9")])
        window._track_recent_project(None)
        window._track_recent_project({})
        window._track_recent_project({"name": "noname"})
        self.assertEqual(window.settings_manager.tracked, [("p9", "Bai 9")])

    def test_browser_open_funnels_through_editor_opener(self):
        window = _make_window()
        called = []
        window._open_editor_for_project = lambda data: called.append(data)
        window.on_project_selected({"id": "p1", "name": "Demo"})
        self.assertEqual(called, [{"id": "p1", "name": "Demo"}])

    def test_player_record_recent_persists(self):
        from eduplay.ui.screens.player_screen import PlayerScreen

        with mock.patch(
            "eduplay.core.settings_manager.SettingsManager"
        ) as fake_mgr_cls:
            PlayerScreen._record_recent_project(object(), {"id": "px", "name": "X"})
        fake_mgr_cls.assert_called_once_with()
        fake_mgr_cls.return_value.add_recent_project.assert_called_once_with("px", "X")

    def test_player_load_records_successful_opens(self):
        import inspect

        from eduplay.ui.screens.player_screen import PlayerScreen

        src = inspect.getsource(PlayerScreen.load_project_game)
        self.assertGreaterEqual(src.count("_record_recent_project(project_data)"), 5)


if __name__ == "__main__":
    unittest.main()
