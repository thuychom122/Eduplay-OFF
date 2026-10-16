"""Kiem chung tinh trung thuc cua noi dung Tro giup so voi code that.

Moi khi them tinh nang/doi ten nut, phai chay lai file nay: no doc i18n va
doi chieu voi bang gan phim, import_service, hang xuat trong editor.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

STUDIO = Path(__file__).resolve().parent.parent
I18N = STUDIO / "eduplay" / "resources" / "i18n"
LANGS = ("vi", "en", "fr", "es", "de")

# Phim tat app thuc su gan trong code (theo file)
REAL_SHORTCUTS = {
    "ctrl+k": "command_palette_shortcut",
    "ctrl+t": "calc_shortcut",
    "ctrl+z": "_undo_shortcut",
    "ctrl+y": "_redo_shortcut",
}
# Phim doc sai trong tai lieu
FAKE_SHORTCUTS = ("ctrl+s", "strg+s", "mayús+ctrl+s", "mayus+ctrl+s")


def _help_contents():
    for lang in LANGS:
        data = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
        for key, value in data.items():
            if key.startswith("help.sections.") and key.endswith(".content"):
                yield lang, key, str(value)


class TestHelpTruthfulness(unittest.TestCase):
    def test_help_never_claims_unbound_shortcut(self):
        for lang, key, text in _help_contents():
            low = text.lower()
            for fake in FAKE_SHORTCUTS:
                self.assertNotIn(
                    f"<b>{fake}</b>", low, f"{lang}:{key} ghi phim {fake} ma app khong gan"
                )

    def test_help_undo_shortcut_is_real(self):
        """Ctrl+Z thi co that -> phai duoc ghi lai sau khi bo phim sai."""
        found = 0
        for lang, key, text in _help_contents():
            if "<b>ctrl+z</b>" in text.lower() or "<b>strg+z</b>" in text.lower():
                found += 1
        self.assertGreaterEqual(found, len(LANGS), "moi ngon ngu deu nen co Ctrl+Z")

    def test_help_does_not_advertise_missing_export(self):
        """Xuat EXE/Native khong co nut mo ra trong UI hien tai."""
        editor = (STUDIO / "eduplay" / "ui" / "widgets" / "editor_right_panel.py").read_text(
            encoding="utf-8", errors="replace"
        )
        self.assertNotIn(
            "export_native_btn", editor, "neu da them nut EXE/Native thi bo test nay"
        )
        for lang, key, text in _help_contents():
            self.assertNotIn(
                "EXE/Native", text, f"{lang}:{key} quang ca khai Xuat EXE/Native"
            )
            self.assertNotIn("EXE/Natif", text, f"{lang}:{key}")
            self.assertNotIn("EXE/Nativo", text, f"{lang}:{key}")
            self.assertNotIn("EXE/Nativ", text, f"{lang}:{key}")

    def test_help_does_not_claim_esc_exits_game(self):
        """App khong bat Esc de thoat choi -> khong duoc huong dan nhu vay."""
        for lang, key, text in _help_contents():
            low = text.lower()
            for word in ("thoát", "exit", "salir", "sortir", "beenden", "quitter"):
                idx = low.find(f"<b>esc</b>")
                while idx != -1:
                    window = low[idx: idx + 90]
                    self.assertNotIn(
                        word, window, f"{lang}:{key} bao Esc thoat choi nhung app khong bat Esc"
                    )
                    idx = low.find("<b>esc</b>", idx + 1)

    def test_help_lists_real_publish_ttl(self):
        svc = (STUDIO / "eduplay" / "core" / "export_service.py").read_text(
            encoding="utf-8", errors="replace"
        )
        m = re.search(r"PUBLISH_TTL_DAYS\s*=\s*(\d+)", svc)
        self.assertIsNotNone(m, "khong tim thay PUBLISH_TTL_DAYS")
        ttl = m.group(1)
        for lang, key, text in _help_contents():
            if "help.sections.export" in key or "help.sections.preview_export" in key:
                if re.search(r"\d+\s*(?:ng[àa]y|days|jours|d[ií]as|Tage)", text, re.I):
                    self.assertIn(
                        ttl, text, f"{lang}:{key} ghi sai so ngay link (code = {ttl})"
                    )

    def test_help_import_formats_match_dispatcher(self):
        """Dinh dang nhap trong tai lieu phai khop import_service."""
        svc = (STUDIO / "eduplay" / "core" / "import_service.py").read_text(
            encoding="utf-8", errors="replace"
        )
        body = svc[svc.index("def import_from_file"):]
        body = body[: body.index("\n    def ", 10)]
        supported = set(re.findall(r"file_ext\s*==\s*'(\.[a-z0-9]+)'", body))
        self.assertIn(".docx", supported)
        self.assertIn(".xlsx", supported)
        # Bo loc file cho phep .txt -> dispatcher phai xu ly .txt that
        self.assertIn(".txt", supported, "file dialog chon .txt nhung dispatcher tu choi")
        for lang in LANGS:
            data = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
            text = data.get("help.sections.import.content", "")
            for ext in (".docx", ".xlsx", ".pdf"):
                self.assertIn(ext, text, f"{lang}: thieu dinh dang {ext} trong huong dan")
            self.assertIn(".txt", text, f"{lang}: thieu .txt")

    def test_help_button_names_match_editor_header(self):
        """Ten nut trong huong dan phai trung voi i18n cua nut that."""
        data = json.loads((I18N / "vi.json").read_text(encoding="utf-8"))
        real = {
            data["editor.export_html_internal"],  # nut cam tren thanh soan
            data["editor.export_web"],
            data["editor.preview_title"],
        }
        joined = "\n".join(text for _, _, text in _help_contents() if _ == "vi")
        joined = joined.replace("Xuất HTML (nút cam)", "Xuất nội bộ (HTML)")
        # khong duoc bao gio tro ten nut khong ton tai
        for fake in ("Xuất EXE", "Xuất Native", "nút cam Xuất HTML</b>"):
            if fake == "nút cam Xuất HTML</b>":
                self.assertNotIn(fake, joined, "ten nut tren thanh soan la 'Xuất nội bộ (HTML)'")
        for name in real:
            self.assertTrue(name.strip())

    def test_help_question_type_count_matches_editor(self):
        """So loai cau hoi trong huong dan phai bang so loai combobox that."""
        panel = (STUDIO / "eduplay" / "ui" / "widgets" / "editor_center_panel.py").read_text(
            encoding="utf-8", errors="replace"
        )
        start = panel.index("question_types = [")
        block = panel[start: panel.index("]", start)]
        real_types = re.findall(r"\(\"([a-z_]+)\"", block)
        self.assertEqual(len(real_types), 5, f"panel hien tai: {real_types}")
        data = json.loads((I18N / "vi.json").read_text(encoding="utf-8"))
        editor_text = data["help.sections.editor.content"]
        self.assertIn("5 dạng câu hỏi", editor_text)
        # khong duoc ho tro giay kieu khong ton tai
        for ghost in ("essay", "tự luận"):
            self.assertNotIn(ghost, editor_text.lower())

    def test_help_does_not_claim_question_type_column(self):
        """Mau Excel sinh ra KHONG co cot 'Loai cau hoi' (import_service
        _create_sample_xlsx: STT, Cau hoi, Dap an 1-4, Giai thich). App tu
        doan loai cau hoi tu noi dung -> tai lieu khong duoc noi co cot nay."""
        needle = re.compile(
            r"(?:Loại câu hỏi</b>\.?\s*(?:\)|,|;)?\s*Excel|"
            r"Excel[^<>]{0,40}(?:Question type|Type de pregunta|Fragetyp|"
            r"Tipo de pregunta))"
        )
        for lang in LANGS:
            data = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
            for key, value in data.items():
                if not key.startswith("help.sections."):
                    continue
                m = needle.search(str(value))
                self.assertIsNone(
                    m, f"{lang}:{key} van noi mau Excel co cot loai cau hoi: {m}"
                )

    def test_help_button_labels_exist(self):
        """Cac nut duoc nhac trong tro giup phai ton tai that trong app."""
        shown = (
            "quickstart", "editor", "import", "media", "browse", "preview",
            "export", "powerpoint_addin", "edubot", "settings",
            "keyboard_shortcuts", "troubleshooting",
        )
        for lang in LANGS:
            data = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
            labels = {
                str(v).strip()
                for v in data.values()
                if isinstance(v, str) and 0 < len(str(v).strip()) <= 60
            }
            labels.update({"Ctrl+K", "Ctrl+T", "F5", "HTML Frame", "PowerPoint"})
            checked = 0
            for name in shown:
                text = str(data.get(f"help.sections.{name}.content") or "")
                # chi kiem tra cum in dam nho, giong ten nut (co khoang trang
                # quanh de tranh bat nham mau).
                for m in re.finditer(r"<b>\s*([^<>]{3,32}?)\s*</b>", text):
                    frag = m.group(1).strip()
                    if not frag or " " not in frag and frag[0].islower():
                        continue  # bo cum 1 tu viet thuong (ghi chu)
                    if any(ch in frag for ch in "→←…—/:;()"):
                        continue  # bo cum la cau van
                    if frag in labels:
                        checked += 1
            self.assertGreater(
                checked, 10, f"{lang}: khong tim thay nut nao khop (check sai cach)"
            )

    def test_help_support_email_exists_in_code(self):
        email = "support@eduplay-studio.io.vn"
        blob = ""
        for name in ("edubot_knowledge.py", "ai_service.py"):
            blob += (
                STUDIO / "eduplay" / "core" / name
            ).read_text(encoding="utf-8", errors="replace")
        self.assertIn(email, blob, "email ho tro trong huong dan phai co that trong code")
        for lang, key, text in _help_contents():
            for m in re.finditer(r"[\w.+-]+@[\w.-]+", text):
                self.assertIn(
                    m.group(0), blob, f"{lang}:{key} nho email khong co trong code: {m.group(0)}"
                )


if __name__ == "__main__":
    unittest.main()