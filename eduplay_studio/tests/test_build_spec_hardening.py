import os
import sys
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestNuitkaBuildPipeline(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.script = self.root / "build_release.bat"
        self.content = self.script.read_text(encoding="utf-8")
        self.app = self.root / "eduplay_studio" / "app.py"
        self.app_content = self.app.read_text(encoding="utf-8")

    def test_build_script_uses_cython_and_nuitka(self):
        self.assertIn("Cython", self.content)
        self.assertIn("Nuitka", self.content)
        self.assertIn("compile_cython_modules.py", self.content)
        self.assertIn("--standalone", self.content)
        self.assertIn("--enable-plugin=pyside6", self.content)
        self.assertIn("--include-package=eduplay", self.content)
        self.assertIn("tools\\compile_cython_modules.py", self.content)

    def test_build_script_does_not_use_hardcoded_two_module_cython(self):
        self.assertNotIn('"eduplay.core.preview_utils", ["eduplay/core/preview_utils.py"]', self.content)
        self.assertNotIn('"eduplay.core.path_resolver", ["eduplay/core/path_resolver.py"]', self.content)
        self.assertNotIn("Extension(\"eduplay.core.preview_utils\"", self.content)

    def test_build_script_includes_qt_assets_and_icon(self):
        self.assertIn("--include-data-dir", self.content)
        self.assertIn("--windows-icon-from-ico", self.content)
        self.assertIn("--windows-console-mode=disable", self.content)
        self.assertIn("tools\\ensure_app_icon.py", self.content)

    def test_build_script_hardens_large_third_party_packages(self):
        self.assertIn("--nofollow-import-to=fitz", self.content)
        self.assertIn("--nofollow-import-to=pymupdf", self.content)
        self.assertIn("--include-module=uuid", self.content)
        self.assertIn("third_party_py", self.content)
        self.assertIn("site-packages\\pymupdf", self.content)
        self.assertIn("site-packages\\fitz", self.content)

    def test_build_script_keeps_pywebview_windows_backend(self):
        self.assertIn("--disable-plugin=pywebview", self.content)
        self.assertIn("--include-package=webview", self.content)
        self.assertIn("--include-module=pythonnet", self.content)
        self.assertIn("--include-package=clr_loader", self.content)
        self.assertNotIn("--include-module=webview.platforms.", self.content)

    def test_app_bootstraps_third_party_python_path(self):
        self.assertIn("_bootstrap_third_party_py", self.app_content)
        self.assertIn('Path(sys.executable).resolve().parent / "third_party_py"', self.app_content)
        self.assertIn('Path(__file__).resolve().parent / "third_party_py"', self.app_content)
        self.assertIn("sys.path.insert(0, candidate_str)", self.app_content)

    def test_old_packaging_files_are_removed(self):
        self.assertFalse((self.root / "eduplay_studio.spec").exists())
        self.assertFalse((self.root / "eduplay_studio" / "EduPlayStudio.spec").exists())
        self.assertFalse((self.root / "eduplay_studio" / "runtime_hook_distutils.py").exists())
        self.assertNotIn("PyInstaller", self.content)
        self.assertNotIn("PyArmor", self.content)


if __name__ == "__main__":
    unittest.main()
