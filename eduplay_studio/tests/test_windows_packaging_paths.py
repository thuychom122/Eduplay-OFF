import os
import sys
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestWindowsPackagingPaths(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.build_release = (self.root / "build_release.bat").read_text(encoding="utf-8")
        self.build_installer = (self.root / "build_installer.bat").read_text(encoding="utf-8")
        self.setup_iss = (self.root / "setup.iss").read_text(encoding="utf-8")

    def test_build_release_publishes_standalone_folder(self):
        self.assertIn(r'set "RELEASE_ROOT=%ROOT%\dist"', self.build_release)
        self.assertIn(r'set "RELEASE_DIR=%RELEASE_ROOT%\EduPlayStudio"', self.build_release)
        self.assertIn('echo [STEP 6] Publishing standalone directory...', self.build_release)
        self.assertIn('xcopy "%DIST_DIR%\\*" "%RELEASE_DIR%\\" /E /I /H /Y >nul', self.build_release)
        self.assertIn(r'set "EXE=%RELEASE_DIR%\EduPlayStudio.exe"', self.build_release)

    def test_build_installer_uses_published_folder(self):
        self.assertIn(r'set "DIST_DIR=%ROOT%\dist\EduPlayStudio"', self.build_installer)
        self.assertIn(r'set "DIST_EXE=%DIST_DIR%\EduPlayStudio.exe"', self.build_installer)
        self.assertIn('call "%BUILD_SCRIPT%"', self.build_installer)
        self.assertIn('"%ISCC%" "%SETUP_FILE%"', self.build_installer)

    def test_setup_iss_reads_same_folder(self):
        self.assertIn('#define BuildDir RepoRoot + "dist\\EduPlayStudio"', self.setup_iss)
        self.assertIn('#define BuildExe BuildDir + "\\EduPlayStudio.exe"', self.setup_iss)
        self.assertIn('#ifexist BuildExe', self.setup_iss)
        self.assertIn('Source: "{#BuildDir}\\*"; DestDir: "{app}";', self.setup_iss)


if __name__ == "__main__":
    unittest.main()
