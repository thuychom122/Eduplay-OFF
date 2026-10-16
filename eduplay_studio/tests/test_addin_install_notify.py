import inspect
import json
import os
import sys
import unittest

from PySide6.QtWidgets import QApplication, QMainWindow


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _StubSettings:
    def __init__(self):
        self._data = {"notifications.system_enabled": True}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def get_language(self):
        return self._data.get("app_language", "vi")


def _make_window():
    from eduplay.ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.settings_manager = _StubSettings()
    window._tray_icon = None
    return window


class TestAddinInstallNotifyI18n(unittest.TestCase):
    def test_installed_toast_key_in_all_languages(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n")
        )
        for lang in ("en", "vi", "fr", "de", "es"):
            with open(os.path.join(base_dir, f"{lang}.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            key = "settings.addin.installed_toast"
            self.assertIn(key, data, f"Missing key '{key}' in {lang}.json")
            self.assertTrue(data[key].strip())


class TestAddinInstallNotifyFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_notify_helper_never_raises_headless(self):
        window = _make_window()
        window._notify_addin_installed()
        window.show_system_notification("", "Đã cài Add-ins", "info", force=True)

    def test_manual_flow_uses_win_toast_not_inapp_dialog(self):
        from eduplay.ui.widgets import settings_dialog as dlg_mod

        src = inspect.getsource(dlg_mod.SettingsDialog._install_ppt_addin_manual)
        # success path hands off to the Windows toast helper...
        self.assertIn("_notify_addin_installed_win", src)
        # ...and shows no in-app information dialog anymore.
        self.assertNotIn("QMessageBox.information", src)
        # ...but failures still warn.
        self.assertIn("QMessageBox.warning", src)

    def test_manual_flow_only_toasts_fresh_installs(self):
        from eduplay.ui.widgets import settings_dialog as dlg_mod

        src = inspect.getsource(dlg_mod.SettingsDialog._install_ppt_addin_manual)
        self.assertIn("_was_installed", src)
        self.assertIn("detect_installed", src)


if __name__ == "__main__":
    unittest.main()
