import inspect
import json
import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestDeviceNoticeI18n(unittest.TestCase):
    def test_device_notice_keys_in_all_languages(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n")
        )
        for lang in ("en", "vi", "fr", "de", "es"):
            with open(os.path.join(base_dir, f"{lang}.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in ("common.device_notice_title", "common.device_notice_body"):
                self.assertIn(key, data, f"Missing key '{key}' in {lang}.json")
                self.assertTrue(data[key].strip())


class TestDeviceNoticeWiring(unittest.TestCase):
    def test_classic_template_has_notice_block(self):
        from eduplay.core import export_service as es_mod

        src = inspect.getsource(es_mod.ExportService._generate_quiz_game_html)
        self.assertIn("device_notice_title", src)
        self.assertIn("device_notice_body", src)
        self.assertIn("device-notice", src)

    def test_fishing_template_has_notice_block(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        path = os.path.join(base, "assets_bundle", "templates_fish", "fishing_game.html")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("i18n_device_notice_title", content)
        self.assertIn("i18n_device_notice_body", content)

    def test_millionaire_exports_inject_notice(self):
        from eduplay.core import export_service as es_mod

        for name in ("export_millionaire_single_file", "_generate_millionaire_html"):
            src = inspect.getsource(getattr(es_mod.ExportService, name))
            self.assertIn("edu-device-notice", src, f"{name} must inject the notice")
            self.assertIn("common.device_notice_body", src)


if __name__ == "__main__":
    unittest.main()
