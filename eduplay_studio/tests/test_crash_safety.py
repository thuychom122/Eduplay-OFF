"""Luoi chong crash: notify catch-all + breadcrumb log + AI fail tiep tuc chay."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class _BoomWidget:
    """Gia widget ma event() luon nem (khong can QApplication that)."""


class TestNotifyCatchAll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        with mock.patch.dict(os.environ, {"EDUPLAY_NO_SPLASH": "1"}):
            import app as app_mod

        cls._app_mod = app_mod
        inst = QApplication.instance()
        if inst is None:
            inst = app_mod.EduPlayApp([])
        cls._app = inst

    def test_notify_catches_slot_exception(self):
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication, QWidget

        app_mod = self._app_mod

        class Boom(QWidget):
            def event(self, e):
                raise RuntimeError("boom-trong-slot")

        # chuyen crash log sang tmp de khong ban vao may that
        with tempfile.TemporaryDirectory() as tmp:
            app_mod._CRASH_LOG_DIR = Path(tmp)
            try:
                w = Boom()
                target = self._app
                if not isinstance(target, app_mod.EduPlayApp):
                    target = app_mod.EduPlayApp.instance() or target
                res = app_mod.EduPlayApp.notify(target, w, QEvent(QEvent.Type.User))
                self.assertFalse(res)
                logs = list(Path(tmp).glob("crash*.log"))
                self.assertTrue(logs, "phai ghi crash log")
                body = logs[0].read_text(encoding="utf-8", errors="replace")
                self.assertIn("boom-trong-slot", body)
            finally:
                app_mod._CRASH_LOG_DIR = None
                try:
                    w.deleteLater()
                except Exception:
                    pass

    def test_ai_failure_does_not_exit(self):
        # exec() khong duoc sys.exit khi AI loi: kiem tra source khong con exit cung
        import pathlib

        src = pathlib.Path(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))
        ).read_text(encoding="utf-8")
        exec_block = src.split("def exec(self):", 1)[1].split("def _get_icon_path", 1)[0]
        self.assertNotIn("sys.exit(1)", exec_block)
        self.assertIn("graceful", exec_block)


class TestRunLog(unittest.TestCase):
    def test_run_log_writes_and_rotates(self):
        from eduplay.ui.main_window import _run_log

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": tmp}):
                _run_log("selftest noises")
                log = Path(tmp) / "EduPlayStudio" / "logs" / "run.log"
                self.assertTrue(log.is_file())
                self.assertIn("selftest noises", log.read_text(encoding="utf-8", errors="replace"))
                # file > 512KB thi xoay
                with open(log, "wb") as f:
                    f.write(b"x" * (512 * 1024 + 10))
                _run_log("after-rotate")
                self.assertTrue((Path(tmp) / "EduPlayStudio" / "logs" / "run.old.log").is_file())


class TestSplashTkThreadSafety(unittest.TestCase):
    """Splash Tk chay tren thread rieng: loi nay chi xuat hien LUC PROCESS THOAT
    (Tcl in 'Tcl_AsyncDelete' roi abort 0x80000003) nen phai kiem tra bang subprocess."""

    def _run(self, mode: str):
        import subprocess

        studio = Path(__file__).resolve().parent.parent
        script = (
            "import os, sys, time\n"
            "sys.path.insert(0, r'%s')\n"
            "os.environ.pop('EDUPLAY_NO_SPLASH', None)\n"
            "import eduplay.core.instant_splash as spl\n"
            "spl.show()\n"
            "time.sleep(0.4)\n"
            "%s\n"
            "time.sleep(0.3)\n"
            "print('END')\n"
        ) % (studio, mode)
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        return subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=120, env=env, cwd=str(studio),
        )

    def _assert_clean(self, proc):
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, f"crash khi thoat:\n{blob}")
        self.assertNotIn("Tcl_AsyncDelete", blob)
        self.assertIn("END", blob)

    def test_finish_path_exits_clean(self):
        self._assert_clean(self._run("spl.finish()"))

    def test_hide_then_finish_path_exits_clean(self):
        self._assert_clean(self._run("spl.hide()\ntime.sleep(0.2)\nspl.reshow()\nspl.finish()"))

    def test_no_finish_atexit_path_exits_clean(self):
        self._assert_clean(self._run("pass"))


if __name__ == "__main__":
    unittest.main()
