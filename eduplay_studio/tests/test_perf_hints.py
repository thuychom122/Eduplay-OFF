"""Canh bao nhe (soft limit) cho anh cua cau hoi va do lon bai.

Khong chan nguoi dung - chi thong bao de app chay mat hon.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from eduplay.core import perf_hints  # noqa: E402


class TestFormatSize(unittest.TestCase):
    def test_formats_readable_in_all_languages(self):
        self.assertEqual(perf_hints.format_size(900 * 1024), "900 KB")
        self.assertEqual(perf_hints.format_size(2 * 1024 * 1024), "2.0 MB")
        self.assertEqual(perf_hints.format_size(512), "512 B")

    def test_bad_input_does_not_raise(self):
        self.assertTrue(perf_hints.format_size(None))


class TestImageLimit(unittest.TestCase):
    def test_small_image_no_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.png"
            p.write_bytes(b"0" * 1024)
            self.assertIsNone(perf_hints.image_size_warning(p, "vi"))

    def test_large_image_warns_in_5_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "big.png"
            p.write_bytes(b"0" * (2 * 1024 * 1024))
            for lang in ("vi", "en", "fr", "es", "de"):
                msg = perf_hints.image_size_warning(p, lang)
                self.assertIsInstance(msg, str)
                self.assertTrue(msg.strip())
                self.assertIn("2.0 MB", msg)

    def test_missing_file_no_warning(self):
        self.assertIsNone(perf_hints.image_size_warning("/no/such/file.png", "vi"))


class TestQuestionLimit(unittest.TestCase):
    def test_at_limit_no_warning(self):
        self.assertIsNone(perf_hints.many_questions_warning(50, "vi"))

    def test_over_limit_warns_with_count(self):
        msg = perf_hints.many_questions_warning(120, "vi")
        self.assertIn("120", msg)
        for lang in ("en", "fr", "es", "de"):
            self.assertTrue(perf_hints.many_questions_warning(51, lang))

    def test_bad_input_no_warning(self):
        self.assertIsNone(perf_hints.many_questions_warning("abc", "vi"))


class TestPanelEmitsNotice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_panel_has_notice_signal(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        self.assertTrue(hasattr(panel, "notice"))

    def test_browse_image_emits_notice_for_big_file(self):
        from unittest import mock

        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        with tempfile.TemporaryDirectory() as tmp:
            big = Path(tmp) / "big.png"
            big.write_bytes(b"0" * (2 * 1024 * 1024))
            panel = EditorCenterPanel()
            seen = []
            panel.notice.connect(lambda m: seen.append(str(m)))
            with mock.patch(
                "PySide6.QtWidgets.QFileDialog.getOpenFileName",
                return_value=(str(big), ""),
            ):
                panel.browse_image()
            self.assertEqual(len(seen), 1)
            self.assertIn("2.0 MB", seen[0])

    def test_browse_image_silent_for_small_file(self):
        from unittest import mock

        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        with tempfile.TemporaryDirectory() as tmp:
            small = Path(tmp) / "s.png"
            small.write_bytes(b"0" * 2048)
            panel = EditorCenterPanel()
            seen = []
            panel.notice.connect(lambda m: seen.append(str(m)))
            with mock.patch(
                "PySide6.QtWidgets.QFileDialog.getOpenFileName",
                return_value=(str(small), ""),
            ):
                panel.browse_image()
            self.assertEqual(seen, [])


class TestHelpMatchesLimits(unittest.TestCase):
    """Tro giup phai noi dung dung moc ma app canh bao."""

    def test_help_documents_both_limits(self):
        import json
        import re

        base = Path(__file__).resolve().parent.parent / "eduplay" / "resources" / "i18n"
        for lang in ("vi", "en", "fr", "es", "de"):
            data = json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))
            text = str(data.get("help.sections.troubleshooting.content") or "")
            self.assertTrue(
                re.search(r"1\s*(?:MB|Mo|Mo\b)", text),
                f"{lang}: tro giup khong nhac moc 1 MB cho anh",
            )
            self.assertTrue(
                re.search(r"50", text), f"{lang}: tro giup khong nhac moc 50 cau"
            )


if __name__ == "__main__":
    unittest.main()