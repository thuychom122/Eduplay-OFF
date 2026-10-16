import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestMathBrackets(unittest.TestCase):
    def _svc(self):
        from eduplay.core.import_service import ImportService
        return ImportService()

    def test_bracket_is_math(self):
        svc = self._svc()
        self.assertFalse(svc._bracket_is_math(""))
        self.assertFalse(svc._bracket_is_math("100"))
        self.assertFalse(svc._bracket_is_math("Đại số"))
        self.assertFalse(svc._bracket_is_math("Hà Nội"))
        self.assertFalse(svc._bracket_is_math("x"))
        self.assertFalse(svc._bracket_is_math("-5"))
        self.assertFalse(svc._bracket_is_math("Hà Nội (thủ đô)"))
        self.assertTrue(svc._bracket_is_math("x+5(78y+y^2)"))
        self.assertTrue(svc._bracket_is_math("x+1"))
        self.assertTrue(svc._bracket_is_math("2+2"))

    def test_xlsx_math_bracket_kept_with_known_answer(self):
        svc = self._svc()
        q = svc._parse_xlsx_template_row(
            "Biểu thức [x+5(78y+y^2)]+5 là biểu thức [Đại số]",
            ["Đại số"],
            "",
        )
        self.assertIsNotNone(q)
        self.assertEqual(q["type"], "fill_blank")
        self.assertIn("[x+5(78y+y^2)]", q["question"])
        self.assertIn("_____", q["question"])
        self.assertEqual(q["correct_answers"], ["Đại số"])

    def test_xlsx_math_bracket_without_match_is_not_fill(self):
        svc = self._svc()
        q = svc._parse_xlsx_template_row(
            "Biểu thức [x+5(78y+y^2)]+5 bằng bao nhiêu?",
            ["5"],
            "",
        )
        self.assertIsNotNone(q)
        self.assertNotEqual(q["type"], "fill_blank")
        self.assertIn("[x+5(78y+y^2)]", q["question"])

    def test_smart_math_bracket_with_known_answer(self):
        svc = self._svc()
        block = [
            "Câu hỏi 1: Biểu thức [x+5(78y+y^2)]+5 là biểu thức [Đại số]",
            "== Đại số",
        ]
        q = svc._parse_block(block)
        self.assertIsNotNone(q)
        self.assertEqual(q["type"], "fill_blank")
        self.assertIn("[x+5(78y+y^2)]", q["question"])
        self.assertIn("_____", q["question"])

    def test_smart_math_bracket_only_is_not_fill(self):
        svc = self._svc()
        block = [
            "Câu hỏi 1: Biểu thức [x+1]+5 bằng bao nhiêu?",
        ]
        q = svc._parse_block(block)
        self.assertTrue(q is None or q.get("type") != "fill_blank")
        if q is not None:
            self.assertIn("[x+1]", q.get("question", ""))

    def test_smart_plain_bracket_still_fill(self):
        svc = self._svc()
        block = [
            "Câu hỏi 3: Nước sôi ở [100] độ Celsius.",
        ]
        q = svc._parse_block(block)
        self.assertIsNotNone(q)
        self.assertEqual(q["type"], "fill_blank")
        self.assertIn("_____", q["question"])


if __name__ == "__main__":
    unittest.main()
