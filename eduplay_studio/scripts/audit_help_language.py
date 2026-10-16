"""Quet xem noi dung Tieng Viet con sot trong cac ngon ngu khac (key help.*)."""
import json
import pathlib
import re

BASE = pathlib.Path("eduplay/resources/i18n")
LANGS = ("en", "fr", "es", "de")

# Tu/dau hieu tieng Viet (co dau)
VI_HINTS = re.compile(
    r"\b(?:câu|bấm|nhấn|chọn|xuất|nhập|thêm|xóa|giữa|trái|phải|dự án|"
    r"câu hỏi|học sinh|giáo viên|trợ giúp|đóng|xem|chơi|thử|cài đặt|"
    r"bài|tài liệu|hình ảnh|âm thanh|hướng dẫn|sử dụng|được|với|như)\b",
    re.IGNORECASE,
)
# Ky tu CHI co trong tieng Viet (khong dung o fr/es/de).
# Luu y: bo "ê" va "ô" vi tieng Phap co (être, rôle...).
VI_CHARS = re.compile(
    r"[đơưĂÂĐƠƯạảấầẩẫậắằẳẵặẹẻẽếềểễệịỉĩọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]"
)


def strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip()


def vi_score(text: str) -> int:
    t = strip_html(text)
    return len(VI_CHARS.findall(t)) + 2 * len(VI_HINTS.findall(t))


def main() -> int:
    vi = json.loads((BASE / "vi.json").read_text(encoding="utf-8"))
    keys = [k for k in vi if k.startswith("help.")]
    rows = []
    for lang in LANGS:
        data = json.loads((BASE / f"{lang}.json").read_text(encoding="utf-8"))
        for key in sorted(keys):
            other = data.get(key)
            if not isinstance(other, str) or not other.strip():
                continue
            sv = vi_score(other)
            same = strip_html(other)[:90] == strip_html(vi[key])[:90]
            if sv >= 3 or same:
                rows.append((lang, key, sv, "TRUNG" if same else "GIONG-VIET"))
    if not rows:
        print("Khong con noi dung tieng Viet nao trong help.*")
        return 0
    for lang, key, sv, why in rows:
        print(f"{lang:3} {sv:4}  {why:11} {key}")
    print(f"\nTong so muc con sot: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())