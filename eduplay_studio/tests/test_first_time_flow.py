import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestFirstTimeFlow(unittest.TestCase):
    def test_existing_settings_file_with_incomplete_first_run_still_prompts(self):
        """A settings file may exist while first_run is still true (previous
        launch crashed or was closed before onboarding finished). Those
        users must still be prompted instead of silently booting defaults.
        """
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            (settings_dir / "settings.json").write_text(
                '{\n  "first_run": true,\n  "app_language": "en"\n}',
                encoding="utf-8",
            )

            sm = SettingsManager(settings_dir=settings_dir)

            self.assertTrue(sm.settings_file_existed)
            self.assertTrue(sm.should_run_first_time_flow())

    def test_existing_settings_file_with_completed_first_run_skips_flow(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            (settings_dir / "settings.json").write_text(
                '{\n  "first_run": false,\n  "app_language": "vi"\n}',
                encoding="utf-8",
            )

            sm = SettingsManager(settings_dir=settings_dir)

            self.assertTrue(sm.settings_file_existed)
            self.assertFalse(sm.should_run_first_time_flow())

    def test_missing_settings_file_runs_first_time_flow(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"

            sm = SettingsManager(settings_dir=settings_dir)

            self.assertFalse(sm.settings_file_existed)
            self.assertTrue(sm.should_run_first_time_flow())

    def test_second_instance_agrees_while_first_run_incomplete(self):
        """While onboarding is incomplete (first_run true), every
        SettingsManager instance reports first-time flow - a second
        instance can no longer mask it. Once onboarding completes
        (first_run false), all instances skip the flow.
        """
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)

            sm1 = SettingsManager(settings_dir=settings_dir)
            self.assertFalse(sm1.settings_file_existed)
            self.assertTrue(sm1.should_run_first_time_flow())

            # A later instance sees the file as existing, but onboarding
            # is still incomplete, so it must also report first-time.
            sm2 = SettingsManager(settings_dir=settings_dir)
            self.assertTrue(sm2.settings_file_existed)
            self.assertTrue(sm2.should_run_first_time_flow())

            # After onboarding completes, everyone skips the flow.
            sm2.set("first_run", False)
            sm3 = SettingsManager(settings_dir=settings_dir)
            self.assertFalse(sm3.should_run_first_time_flow())

    def test_aiservice_reuses_passed_settings_manager_and_preserves_first_time(self):
        """AIService must reuse the SettingsManager passed to its constructor
        instead of creating its own. Otherwise the internal instance writes
        settings.json before the main flow runs, masking the first-time state.
        """
        from eduplay.core.settings_manager import SettingsManager
        from eduplay.core.ai_service import AIService

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)

            sm = SettingsManager(settings_dir=settings_dir)
            self.assertTrue(sm.should_run_first_time_flow())

            ai = AIService(settings_manager=sm)
            # Must not have spun up a separate SettingsManager.
            self.assertIs(ai.settings_manager, sm)
            # First-time detection must still hold (no second instance created).
            self.assertTrue(sm.should_run_first_time_flow())


if __name__ == "__main__":
    unittest.main()
