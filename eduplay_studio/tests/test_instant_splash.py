import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestInstantSplash(unittest.TestCase):
    def test_module_is_stdlib_only(self):
        src = Path(__file__).resolve().parent.parent / "eduplay" / "core" / "instant_splash.py"
        text = src.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("import ") or s.startswith("from "):
                self.assertNotIn("PySide6", s)
                self.assertNotIn("eduplay", s)
        before = set(sys.modules.keys())
        import eduplay.core.instant_splash as spl
        after = set(sys.modules.keys())
        new_mods = {m for m in (after - before) if m.startswith("PySide6")}
        self.assertEqual(new_mods, set())
        # import khong tu tao thread
        time.sleep(0.1)
        splash_threads = [t for t in __import__("threading").enumerate() if t.name == "eduplay-instant-splash"]
        self.assertEqual(splash_threads, [])

    def test_disabled_by_env_is_noop(self):
        import eduplay.core.instant_splash as spl
        with mock.patch.dict(os.environ, {"EDUPLAY_NO_SPLASH": "1"}):
            self.assertTrue(spl._disabled())
            self.assertFalse(spl.show())
            spl.set_status("hello")
            spl.set_progress(50)
            t0 = time.monotonic()
            spl.finish()
            self.assertLess(time.monotonic() - t0, 2.0)

    def test_disabled_by_preview_runner_argv(self):
        import eduplay.core.instant_splash as spl
        with mock.patch.object(sys, "argv", ["app.exe", "--preview-runner"]):
            self.assertTrue(spl._disabled())
            self.assertFalse(spl.show())

    def test_helpers_never_raise_without_show(self):
        import eduplay.core.instant_splash as spl
        with mock.patch.dict(os.environ, {"EDUPLAY_NO_SPLASH": "1"}):
            spl.set_status("x")
            spl.set_progress("y")
            spl.finish("done")
            self.assertIsInstance(spl._resource_path("eduplay", "nope.png"), str)

    def test_splash_size_is_locked(self):
        src = Path(__file__).resolve().parent.parent / "eduplay" / "core" / "instant_splash.py"
        text = src.read_text(encoding="utf-8", errors="ignore")
        # khoa cung kich thuoc: minsize+maxsize+resizable(False) o ca luc mo lan ket thuc
        self.assertGreaterEqual(text.count("maxsize"), 2)
        self.assertIn("resizable(False, False)", text)
        # tat co gian theo noi dung (overrideredirect bo qua min/maxsize
        # cua window manager nen phai khoa tu frame ben trong)
        self.assertIn("pack_propagate(False)", text)
        # chu trang thai co wraplength + rong co dinh de no day gian cua so
        self.assertIn("wraplength", text)

    def test_splash_never_calls_quit_inside_timer_callback(self):
        """GOC CRASH: Tk_Quit() trong after-callback tren thread phu lam Tcl
        mat rang async handler -> 'Tcl_AsyncDelete' + abort khi thoat."""
        src = Path(__file__).resolve().parent.parent / "eduplay" / "core" / "instant_splash.py"
        text = src.read_text(encoding="utf-8", errors="ignore")

        # Kiem tra CA LUU CALL trong code that (docstring/comment khong duoc
        # anh huong) bang ast cho chac chan.
        import ast

        tree = ast.parse(text)
        bad_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "quit" and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "root":
                        bad_calls.append(node.lineno)
        self.assertEqual(
            bad_calls, [], "khong duoc goi root.quit() tu after-callback tren thread phu"
        )

        # phai co lop an toan: abort job + atexit join
        self.assertIn('kind == "abort"', text)
        self.assertIn("_abort_and_join", text)
        self.assertIn("_atexit.register", text)

    def test_splash_i18n_covers_5_langs(self):
        import eduplay.core.instant_splash as spl
        for lang in ("vi", "en", "fr", "es", "de"):
            self.assertIn(lang, spl.STRINGS)
            for key in ("starting", "loading_ui", "opening", "done"):
                val = spl.STRINGS[lang].get(key)
                self.assertTrue(isinstance(val, str) and val.strip(), f"{lang}.{key}")
                self.assertEqual(spl.tr(key, lang), val)
        self.assertEqual(spl._normalize_lang("vi_VN"), "vi")
        self.assertEqual(spl._normalize_lang("fr-FR"), "fr")
        self.assertEqual(spl._normalize_lang("xx"), "en")
        self.assertEqual(spl._normalize_lang(""), "en")

    def test_splash_i18n_json_keys_exist(self):
        import json
        base = Path(__file__).resolve().parent.parent / "eduplay" / "resources" / "i18n"
        for lang in ("vi", "en", "fr", "es", "de"):
            data = json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("splash.starting", "splash.loading_ui", "splash.opening", "splash.done"):
                self.assertTrue(str(data.get(key) or "").strip(), f"{lang}:{key}")

    def test_splash_hide_reshow_are_thread_safe_noops(self):
        import eduplay.core.instant_splash as spl
        with self.subTest("no show -> no crash"):
            with mock.patch.dict(os.environ, {"EDUPLAY_NO_SPLASH": "1"}):
                spl.hide()
                spl.reshow()
                spl.set_status_key("starting")
        with self.subTest("real show -> hide/reshow/finish sequence"):
            splash = spl
            splash.show()
            time.sleep(0.3)
            splash.hide()
            time.sleep(0.2)
            splash.reshow()
            time.sleep(0.2)
            splash.finish()
            time.sleep(0.2)

    def test_resource_path_finds_icon(self):
        import eduplay.core.instant_splash as spl
        p = spl._resource_path("eduplay", "resources", "icons", "icon.png")
        self.assertTrue(p.endswith("icon.png"))
        self.assertTrue(os.path.exists(p))


if __name__ == "__main__":
    unittest.main()
