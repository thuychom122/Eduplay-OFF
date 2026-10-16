"""Hieu nang: khoi dong nhanh + ton trong cau hinh "giam chuyen dong".

1) THU VIEN NANG phai LAZY: app mo len khong duoc nap openpyxl/docx/fitz/
   cryptography (chi nap khi nguoi dung that su can).
2) Cai dat "reduce_motion" phai ap dung cho MOT HIEU UNG nao, khong phai
   rieng animation credits.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

STUDIO = Path(__file__).resolve().parent.parent

HEAVY = ("openpyxl", "docx", "fitz", "cryptography.hazmat.primitives.ciphers.aead")


def _run(code: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["EDUPLAY_NO_SPLASH"] = "1"
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=180, cwd=str(STUDIO), env=env,
    )


class TestLazyHeavyImports(unittest.TestCase):
    def test_heavy_libs_not_loaded_on_startup(self):
        code = (
            "import sys, os\n"
            "sys.path.insert(0, '.')\n"
            "import eduplay.ui.main_window\n"
            "print(','.join(m for m in %r if m in sys.modules))\n" % (HEAVY,)
        )
        res = _run(code)
        self.assertEqual(res.returncode, 0, res.stderr[-800:])
        loaded = [m for m in res.stdout.strip().split(",") if m]
        self.assertEqual(
            loaded, [], f"phai nap lazy, thu vien nang dang bi nap: {loaded}"
        )

    def test_import_service_flags_do_not_import_libs(self):
        code = (
            "import sys\n"
            "sys.path.insert(0, '.')\n"
            "from eduplay.core import import_service as s\n"
            "print(bool(s.DOCX_AVAILABLE), bool(s.PDF_AVAILABLE), bool(s.XLSX_AVAILABLE))\n"
            "loaded = [m for m in ('openpyxl','docx','fitz') if m in sys.modules]\n"
            "print(','.join(loaded) if loaded else 'NONE')\n"
        )
        res = _run(code)
        self.assertEqual(res.returncode, 0, res.stderr[-800:])
        lines = res.stdout.strip().splitlines()
        flags = [f.strip() for f in lines[0].split()]
        self.assertEqual(
            flags, ["True", "True", "True"],
            f"co thu vien bi thieu (import .doc/.pdf/.xlsx se hong): {lines}",
        )
        self.assertEqual(lines[1].strip(), "NONE", "co nap thu vien nang khi chi doc co")

    def test_lazy_helper_actually_imports_on_demand(self):
        code = (
            "import sys\n"
            "sys.path.insert(0, '.')\n"
            "from eduplay.core import import_service as s\n"
            "f = s._lazy_load_workbook\n"
            "assert callable(f())\n"
            "print('openpyxl' in sys.modules)\n"
        )
        res = _run(code)
        self.assertEqual(res.returncode, 0, res.stderr[-800:])
        self.assertEqual(res.stdout.strip().splitlines()[-1], "True")

    def test_startup_is_not_slower_than_baseline(self):
        """Canh bao som neu sau nay nap lai thu vien nang o cap module."""
        code = (
            "import sys, time\n"
            "sys.path.insert(0, '.')\n"
            "t = time.perf_counter()\n"
            "import eduplay.ui.main_window\n"
            "print(int((time.perf_counter() - t) * 1000))\n"
        )
        res = _run(code)
        self.assertEqual(res.returncode, 0, res.stderr[-800:])
        ms = int(res.stdout.strip().splitlines()[-1])
        self.assertLess(ms, 3000, f"import main_window cham ({ms}ms)")


class TestMotionPreference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def _patch(self, enabled: bool):
        from unittest import mock

        from eduplay.core.settings_manager import SettingsManager

        return mock.patch.object(
            SettingsManager,
            "get_accessibility_settings",
            return_value={"reduce_motion": bool(enabled)},
        )

    def test_ms_shortens_when_motion_allowed(self):
        from eduplay.ui import motion

        motion.invalidate_cache()
        with self._patch(False):
            self.assertFalse(motion.motion_enabled())
            self.assertLess(motion.ms(400), 400)
            self.assertGreaterEqual(motion.ms(400), 1)
        motion.invalidate_cache()

    def test_ms_zero_when_reduce_motion_on(self):
        from eduplay.ui import motion

        motion.invalidate_cache()
        with self._patch(True):
            self.assertTrue(motion.motion_enabled())
            self.assertEqual(motion.ms(400), 0)
        motion.invalidate_cache()

    def test_fade_widget_skips_animation_when_disabled(self):
        from PySide6.QtWidgets import QLabel

        from eduplay.ui import motion

        motion.invalidate_cache()
        label = QLabel("x")
        label.show()
        done = []
        with self._patch(True):
            anim = motion.fade_widget(label, 0.0, 1.0, 200, on_finished=lambda: done.append(1))
        self.assertIsNone(anim, "khong duoc tao animation khi tat hieu ung")
        self.assertEqual(done, [1], "phai goi on_finished ngay")
        motion.invalidate_cache()

    def test_fade_widget_animates_when_enabled(self):
        from PySide6.QtWidgets import QLabel

        from eduplay.ui import motion

        motion.invalidate_cache()
        label = QLabel("y")
        with self._patch(False):
            anim = motion.fade_widget(label, 0.0, 1.0, 200)
        self.assertIsNotNone(anim, "phai co animation khi bat hieu ung")
        motion.invalidate_cache()

    def test_ms_never_raises_on_bad_input(self):
        from eduplay.ui import motion

        motion.invalidate_cache()
        self.assertIsInstance(motion.ms(None), int)

    def test_ui_uses_motion_helper(self):
        """Cac animation lon phai di qua _motion_ms de rut ngan/tat duoc."""
        for rel in (
            "eduplay/ui/main_window.py",
            "eduplay/ui/screens/editor_screen.py",
        ):
            text = (STUDIO / rel).read_text(encoding="utf-8", errors="replace")
            self.assertIn("_motion_ms", text, f"{rel} chua dung motion helper")
            self.assertIn(
                "from eduplay.ui.motion import", text, f"{rel} thieu import motion"
            )


if __name__ == "__main__":
    unittest.main()