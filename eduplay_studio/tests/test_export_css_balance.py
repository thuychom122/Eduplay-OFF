"""Hoi quy: CSS trong HTML xuat ra phai can bang brace (tung co loi
.intro-card{ lap 2 lan lam chet CSS phia sau -> game mat style)."""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _style_blocks(html: str):
    return re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)


def _assert_balanced(testcase, css: str):
    tmp = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)
    tmp2 = re.sub(r"\"(?:[^\"\\\\\n]|\\\\.)*\"|'(?:[^'\\\\\n]|\\\\.)*'", "", tmp)
    stack = []
    extra_close = 0
    for i, ch in enumerate(tmp2):
        if ch == "{":
            lineno = tmp2.count("\n", 0, i) + 1
            start = tmp2.rfind("\n", 0, i) + 1
            stack.append((lineno, tmp2[start:i].strip()[-80:]))
        elif ch == "}":
            if stack:
                stack.pop()
            else:
                extra_close += 1
    testcase.assertEqual(extra_close, 0, "thua dau dong ngoac trong CSS")
    testcase.assertEqual(stack, [], "thieu dau dong ngoac trong CSS: %r" % (stack[:3],))


class TestExportCssBalance(unittest.TestCase):
    def _export_classic(self, tmpdir):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        proj = {
            "id": "css1",
            "name": "CSS Check",
            "game_type": "quiz_classic",
            "language": "vi",
            "questions": [
                {
                    "id": "q1",
                    "type": "multiple_choice",
                    "question": "Nguyen nhan chinh?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0,
                },
                {
                    "id": "q2",
                    "type": "true_false",
                    "question": "Dung hay sai?",
                    "correct_answer": True,
                },
            ],
            "game_config": {},
        }
        ok = svc.export_to_html(
            proj, tmpdir, bundle_resources=True, single_file=True, output_filename="CssCheck"
        )
        self.assertTrue(ok)
        return Path(tmpdir) / "CssCheck.html"

    def test_classic_export_css_is_balanced(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = self._export_classic(tmp)
            html = fp.read_text(encoding="utf-8")
            blocks = _style_blocks(html)
            self.assertTrue(blocks, "khong tim thay <style> nao")
            for css in blocks:
                _assert_balanced(self, css)

    def test_classic_export_has_key_selectors_and_no_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = self._export_classic(tmp)
            html = fp.read_text(encoding="utf-8")
            for sel in (
                ".game-stats",
                ".btn-classic",
                ".option-prefix",
                ".game-over",
                "#eduImageLightbox",
                ".control-button",
            ):
                self.assertIn(sel, html, f"thieu selector {sel}")
            self.assertEqual(html.count("{{"), 0, "con sot placeholder jinja")
            self.assertEqual(html.count("<style>"), html.count("</style>"))


if __name__ == "__main__":
    unittest.main()
