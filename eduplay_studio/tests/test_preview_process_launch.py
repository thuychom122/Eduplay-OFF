import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestPreviewProcessLaunch(unittest.TestCase):
    def test_build_preview_process_command_uses_same_exe_when_frozen(self):
        from eduplay.core.preview_runner import build_preview_process_command

        program, args = build_preview_process_command(
            executable=r"C:\Apps\EduPlayStudio\EduPlayStudio.exe",
            uri="file:///C:/temp/sample_preview.html",
            title="Preview",
            frozen=True,
        )

        self.assertEqual(program, r"C:\Apps\EduPlayStudio\EduPlayStudio.exe")
        self.assertEqual(args, ["--preview-runner", "file:///C:/temp/sample_preview.html", "Preview"])

    def test_build_preview_process_command_uses_python_module_when_python_exists(self):
        from eduplay.core.preview_runner import build_preview_process_command

        program, args = build_preview_process_command(
            executable=r"C:\Python312\python.exe",
            uri="file:///C:/temp/sample_preview.html",
            title="Preview",
            frozen=False,
        )

        self.assertEqual(program, r"C:\Python312\python.exe")
        self.assertEqual(args, ["-u", "-m", "eduplay.core.preview_runner", "file:///C:/temp/sample_preview.html", "Preview"])

    def test_resolve_frozen_preview_executable_prefers_existing_file(self):
        from eduplay.core.preview_runner import resolve_frozen_preview_executable

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_exe = root / "EduPlayStudio.exe"
            real_exe.write_bytes(b"")
            missing = root / "missing.exe"
            chosen = resolve_frozen_preview_executable(
                executable=str(missing),
                argv0=str(real_exe),
                cwd=str(root),
            )
            self.assertEqual(chosen, str(real_exe))

    def test_resolve_frozen_preview_executable_strips_extended_path_prefix(self):
        from eduplay.core.preview_runner import resolve_frozen_preview_executable

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_exe = root / "EduPlayStudio.exe"
            real_exe.write_bytes(b"")
            prefixed = "\\\\?\\" + str(real_exe)
            chosen = resolve_frozen_preview_executable(
                executable=prefixed,
                argv0="",
                cwd="",
            )
            self.assertEqual(chosen, str(real_exe))

    def test_resolve_frozen_preview_executable_returns_empty_when_missing(self):
        from eduplay.core.preview_runner import resolve_frozen_preview_executable

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chosen = resolve_frozen_preview_executable(
                executable=str(root / "missing.exe"),
                argv0=str(root / "also-missing.exe"),
                cwd=str(root / "empty"),
            )
            self.assertEqual(chosen, "")

    def test_normalize_windows_path_strips_extended_prefixes(self):
        from eduplay.core.preview_runner import normalize_windows_path

        self.assertEqual(normalize_windows_path(r"\\?\C:\App\EduPlayStudio.exe"), r"C:\App\EduPlayStudio.exe")
        self.assertEqual(normalize_windows_path(r"\\.\D:\Tools\EduPlayStudio.exe"), r"D:\Tools\EduPlayStudio.exe")

    def test_resolve_frozen_preview_working_directory_uses_executable_parent(self):
        from eduplay.core.preview_runner import resolve_frozen_preview_working_directory

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_exe = root / "EduPlayStudio.exe"
            real_exe.write_bytes(b"")
            chosen = resolve_frozen_preview_working_directory(
                executable=str(real_exe),
                argv0="",
                cwd=str(root / "missing"),
            )
            self.assertEqual(chosen, str(root))

    def test_resolve_frozen_preview_working_directory_strips_prefix(self):
        from eduplay.core.preview_runner import resolve_frozen_preview_working_directory

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_exe = root / "EduPlayStudio.exe"
            real_exe.write_bytes(b"")
            chosen = resolve_frozen_preview_working_directory(
                executable="\\\\?\\" + str(real_exe),
                argv0="",
                cwd="",
            )
            self.assertEqual(chosen, str(root))

    def test_get_current_process_executable_returns_running_interpreter(self):
        from eduplay.core.preview_runner import get_current_process_executable

        value = get_current_process_executable()
        self.assertTrue(value)
        self.assertTrue(Path(value).is_file())

    def test_is_compiled_app_is_false_under_plain_python(self):
        from eduplay.core.preview_runner import is_compiled_app

        self.assertFalse(is_compiled_app())

    def test_resolve_frozen_preview_executable_prefers_process_image(self):
        from eduplay.core.preview_runner import resolve_frozen_preview_executable

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_exe = root / "EduPlayStudio.exe"
            real_exe.write_bytes(b"")
            missing = root / "missing.exe"
            chosen = resolve_frozen_preview_executable(
                executable=str(missing),
                argv0=str(missing),
                cwd=str(root / "empty"),
                process_exe=str(real_exe),
            )
            self.assertEqual(chosen, str(real_exe))


if __name__ == "__main__":
    unittest.main()
