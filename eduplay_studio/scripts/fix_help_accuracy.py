"""Sua cac tuyen bo SAI trong noi dung Tro giup (da doi chieu voi code thuc te).

Ngay 14/09/2026, kiem chieu tung dong voi code:
  - Ctrl+S / Esc: app KHONG gan phim nay -> xoa khoi huong dan.
  - Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z: co that (editor_screen) -> bo sung.
  - F5 / Shift+F5 la phim cua PowerPoint, khong phai cua app -> ghi ro.
  - Xuat EXE/Native: khong co nut nao mo ra (chi ton tai trong panel _simple
    khong duoc dung) -> xoa khoi huong dan.
  - Nhap .txt: hop thoai chon file hua .txt nhung import_service bo qua
    -> da them route trong code, tai lieu ghi lai dung.
  - Nhap .pdf: co that nhung chua duoc ghi -> bo sung.
  - Ten nut phai dung y noi dung app hien thi.
Chay lai duoc nhieu lan (idempotent).

LUU Y QUAN TRONG: trong `re.sub`, PHAN THAY THE la chuoi LITERAL - khong
hieu "character class". Neu viet `[âa]` o phan thay the thi no se ghi
thang "[âa]" vao noi dung (da lam loi o mot lan: "[ó] 3 cách"). Phan thay
the phai dung KY TU THAT, chi dung `[...]` o phan MAU.
"""
import json
import pathlib
import re
import sys

BASE = pathlib.Path(r"E:\eduplay\v1.0\EDUPLAY-OFFLINE\eduplay_studio\eduplay\resources\i18n")

# --- 1. Xoa dong gan sai (Esc / Ctrl+S) -------------------------------------
# Luu y: noi dung sau phim tat co the chua <b>...</b> nen phai dung
# "tempered dot" (khong duoc gap <br>/</div>) thay vi [^<]*.
DROP_LINE_PATTERNS = [
    r"<b>Esc</b>(?:(?!<br>|</div>).)*?(?:<br>|</div>)",
    r"<b>(?:Ctrl\+S|Strg\+S|May[úu]s\+Ctrl\+S)</b>(?:(?!<br>|</div>).)*?(?:<br>|</div>)",
]

# --- 2. Bo khoi "Xuat EXE/Native" ------------------------------------------
EXE_PATTERNS = [
    r"<b>(?:Cách|Way|Méthode|Methode|Weg|Vía|Via|Modo)\s*4\s*[—–-][^<]*</b>[^<]*(?:<br>)?",
    r"<b>(?:EXE/Native|EXE/Natif|EXE/Nativo|EXE/Nativ|EXE|Native)[^<]*</b>[^<]*(?:<br>)?",
    r"<b>[^<]{0,60}EXE[^<]{0,60}</b>[^<]*(?:<br>)?",
]

# --- 2b. Dong "• <b>Ctrl+S</b> luu •" (danh sach goc) -> bo ca goc do -------
BULLET_CTRL_S = [
    r"\s*[•·\-–]\s*<b>(?:Ctrl\+S|Strg\+S|May[úu]s\+Ctrl\+S)</b>[^•<]{0,60}(?=[•·]|\.|\s*</)",
]

# --- 3. Ghi ro phim cua PowerPoint, them nhom undo/redo -----------------------
F5_NOTE = {
    "vi": "<b>F5 / Shift+F5</b> — của <b>PowerPoint</b> (không phải của app): F5 trình chiếu từ đầu, Shift+F5 từ slide hiện tại.<br>",
    "en": "<b>F5 / Shift+F5</b> — <b>PowerPoint</b> keys (not app keys): F5 plays from the start, Shift+F5 from the current slide.<br>",
    "fr": "<b>F5 / Maj+F5</b> — raccourcis de <b>PowerPoint</b> (pas de l'app) : F5 lance le diaporama, Maj+F5 depuis la diapositive courante.<br>",
    "es": "<b>F5 / Mayús+F5</b> — teclas de <b>PowerPoint</b> (no de la app): F5 inicia la presentación, Mayús+F5 desde la diapositiva actual.<br>",
    "de": "<b>F5 / Umschalt+F5</b> — Tasten von <b>PowerPoint</b> (nicht von der App): F5 startet die Präsentation, Umschalt+F5 ab der aktuellen Folie.<br>",
}

UNDO_ADD = {
    "vi": "<b>Ctrl+Z</b> — Hoàn tác vừa sửa câu; <b>Ctrl+Y</b> hoặc <b>Ctrl+Shift+Z</b> — Làm lại.<br>",
    "en": "<b>Ctrl+Z</b> — Undo the last edit; <b>Ctrl+Y</b> or <b>Ctrl+Shift+Z</b> — Redo.<br>",
    "fr": "<b>Ctrl+Z</b> — Annuler la dernière modification ; <b>Ctrl+Y</b> ou <b>Ctrl+Maj+Z</b> — Rétablir.<br>",
    "es": "<b>Ctrl+Z</b> — Deshacer el último cambio; <b>Ctrl+Y</b> o <b>Mayús+Ctrl+Z</b> — Rehacer.<br>",
    "de": "<b>Strg+Z</b> — Letzte Änderung rückgängig; <b>Strg+Y</b> oder <b>Umschalt+Strg+Z</b> — Wiederholen.<br>",
}

# --- 4. Bo sung dinh dang nhap thieu (.pdf) ---------------------------------
PDF_ADD = {
    lang: (".docx / .doc / .xlsx / .txt", ".docx / .doc / .pdf / .xlsx / .txt")
    for lang in ("vi", "en", "fr", "es", "de")
}

# --- 5. Dung ten nut that (chi tieng Viet) ----------------------------------
# PHAN THAY THE dung KY TU THAT (khong phai [a-z]).
LABEL_FIXES = [
    (r"(?:nút cam\s*<b>|nút\s*<b>)\s*Xuất HTML\s*</b>",
     "nút cam <b>Xuất nội bộ (HTML)</b>"),
    (r"<b>Xuất HTML</b>\s*\(nút cam\)", "<b>Xuất nội bộ (HTML)</b>"),
    (r"<b>\+ Thêm</b>", "<b>Thêm câu hỏi</b>"),
    (r"<b>Xem nhanh</b>\s*\(con mắt\)", "<b>Xem câu chọn</b>"),
    (r"khác <b>Xem nhanh</b>", "khác <b>Xem câu chọn</b>"),
    (r"bấm <b>Lưu</b>\s*\.", "bấm <b>Lưu câu hỏi</b>."),
]

# --- 6. Sua ky tu "character class" bi ghi nham vao noi dung ----------------
# Do lan chay truoc: phan thay the co "[âa]" nen con day "[âa]" trong text.
# Chỉ đụng các mẫu KHÔNG phải nội dung thật (giữ nguyên "[...]", "[x+1]").
ARTIFACT_FIX = {
    "Th[êe]m": "Thêm",
    "c[âa]u": "câu",
    "h[ỏi]": "hỏi",
    # ban dau con "h[ỏi</b>" (khong co dau ] nen khong khop mau co dau ngoac)
    "h[ỏi": "hỏi",
    "b[ấa]m": "bấm",
    "C[óo] 3 c[áa]ch": "Có 3 cách",
    "el [úu]ltimo": "el último",
    "May[úu]s": "Mayús",
    "presentaci[óo]n": "presentación",
    "w[âa]hrend": "während",
    "f[üu]r": "für",
    "[ÄA]nderung": "Änderung",
    "[ée]dition": "édition",
    "aujourd[êe]hui": "aujourd'hui",
    "derni[èe]re": "dernière",
    "R[ée]tablir": "Rétablir",
    "r[üu]ckg[äa]ngig": "rückgängig",
    "Pr[äa]sentation": "Präsentation",
}


def strip_false_lines(html: str) -> str:
    out = html
    for pat in BULLET_CTRL_S:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    for pat in DROP_LINE_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    for pat in EXE_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    # EN/FR/ES/DE: bo tieu de "PowerPoint & EXE" -> "PowerPoint"
    out = re.sub(r"PowerPoint\s*&\s*EXE", "PowerPoint", out)
    out = re.sub(r"PowerPoint\s*(?:et|and|y|e)\s*EXE", "PowerPoint", out)
    # bo <br> thua do cat dong
    out = re.sub(r"(?:<br>\s*){2,}", "<br>", out)
    out = re.sub(r"\s*<br>\s*</div>", "</div>", out)
    return out


def fix_artifacts(out: str) -> str:
    for bad, good in ARTIFACT_FIX.items():
        out = out.replace(bad, good)
    return out


def inject_keys(html: str, lang: str) -> str:
    out = html
    # them phim undo/redo ngay truoc dong F5 (neu co)
    marker = re.search(r"<b>(?:F5|Umschalt\+F5|Mayús\+F5|Maj\+F5)</b>", out)
    if marker and "Ctrl+Z" not in out and "Strg+Z" not in out:
        out = out[: marker.start()] + UNDO_ADD[lang] + out[marker.start():]
    # ghi ro F5 la phim cua PowerPoint
    if "<b>F5" in out and "PowerPoint" not in out:
        m = re.search(r"<b>(?:F5|Umschalt\+F5|Mayús\+F5|Maj\+F5)[^<]*</b>", out)
        if m:
            out = out[: m.start()] + F5_NOTE[lang] + out[m.end():]
    return out


def fix_pdf(out: str, lang: str) -> str:
    old, new = PDF_ADD[lang]
    if ".pdf" not in out and old in out:
        out = out.replace(old, new)
    return out


def main() -> int:
    total = 0
    for lang in ("vi", "en", "fr", "es", "de"):
        path = BASE / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = []

        key = "help.sections.keyboard_shortcuts.content"
        if key in data:
            old = data[key]
            new = strip_false_lines(old)
            new = inject_keys(new, lang)
            if new != old:
                data[key] = new
                changed.append("keyboard_shortcuts")

        # Ap dung cho MOI muc (ke ca muc an) de khong con noi dung noi doi
        # o bat ky cho nao duoc mo sau nay.
        for k in list(data.keys()):
            if not (k.startswith("help.sections.") and k.endswith(".content")):
                continue
            if k == "help.sections.keyboard_shortcuts.content":
                continue
            old = data[k]
            new = strip_false_lines(old)
            new = re.sub(
                r"<b>Esc</b>[^<]{0,60}(?:thoát|exit|salir|sortir|beenden|raus)[^<]{0,20}\.?",
                "",
                new,
                flags=re.IGNORECASE,
            )
            if new != old:
                data[k] = new
                changed.append(k.split(".")[2])

        key = "help.sections.preview.content"
        if key in data:
            old = data[key]
            new = strip_false_lines(old)
            if new != old:
                data[key] = new
                changed.append("preview")

        key = "help.sections.export.content"
        if key in data:
            old = data[key]
            new = strip_false_lines(old)
            if new != old:
                data[key] = new
                changed.append("export")

        for name in ("import", "quickstart", "editor", "powerpoint_addin", "troubleshooting"):
            key = f"help.sections.{name}.content"
            if key not in data:
                continue
            old = data[key]
            new = old
            if name == "import":
                new = fix_pdf(new, lang)
            for pat, repl in LABEL_FIXES:
                new = re.sub(pat, repl, new)
            if new != old:
                data[key] = new
                changed.append(name)

        # Sua ky tu "character class" bi ghi nham (lan chay truoc)
        for k in list(data.keys()):
            if not k.startswith("help.sections."):
                continue
            old = data[k]
            new = fix_artifacts(old)
            if new != old:
                data[k] = new
                changed.append(k.split(".")[2] + "(artifact)")

        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        total += len(changed)
        print(f"{lang}: {sorted(set(changed))}")
    print(f"tong so muc sua: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())