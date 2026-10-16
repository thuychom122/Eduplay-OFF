import inspect
import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _StubLeftPanel:
    def __init__(self, payload):
        self._payload = dict(payload)

    def _build_settings_payload(self):
        return dict(self._payload)


class _StubCenterPanel:
    def __init__(self):
        self.loaded = []

    def load_project(self, project):
        self.loaded.append(True)


def _make_editor(project):
    from eduplay.ui.screens.editor_screen import EditorScreen

    editor = EditorScreen.__new__(EditorScreen)
    editor.current_project = project
    editor.center_panel = _StubCenterPanel()
    editor.left_panel = None
    return editor


class TestMusicAutoApply(unittest.TestCase):
    def test_pending_combo_state_folds_into_config(self):
        window = _make_editor(
            {"game_config": {"background_music_mode": "builtin_1",
                             "background_music": "assets/sound/background.mp3"},
             "questions": []}
        )
        window.left_panel = _StubLeftPanel({
            "default_question_time": 30,
            "is_millionaire": False,
            "music_mode": "builtin_2",
            "custom_music_path": "",
            "randomize_questions": True,
            "auto_points_enabled": True,
            "export_mode": "student",
        })
        window._apply_pending_settings_to_project()
        cfg = window.current_project["game_config"]
        self.assertEqual(cfg.get("background_music_mode"), "builtin_2")
        self.assertEqual(cfg.get("background_music"), "assets/sound/background2.mp3")

    def test_random_mode_folds_without_executing_choice(self):
        window = _make_editor({"game_config": {}, "questions": []})
        window.left_panel = _StubLeftPanel({
            "default_question_time": 30,
            "is_millionaire": False,
            "music_mode": "random_builtin",
            "custom_music_path": "",
            "randomize_questions": True,
            "auto_points_enabled": True,
            "export_mode": "student",
        })
        window._apply_pending_settings_to_project()
        cfg = window.current_project["game_config"]
        # random resolves at apply time to one of the two builtins
        self.assertIn(cfg.get("background_music"),
                      ("assets/sound/background.mp3", "assets/sound/background2.mp3"))

    def test_preview_and_export_and_save_apply_pending_first(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        for name in ("open_preview_window", "on_export_html", "on_export_web",
                     "on_export_native", "on_export_exe", "save_project"):
            src = inspect.getsource(getattr(EditorScreen, name))
            self.assertIn("_apply_pending_settings_to_project", src,
                          f"{name} must auto-apply settings first")


if __name__ == "__main__":
    unittest.main()
