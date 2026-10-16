"""Ngang suyen an toan (soft limit) cho anh/media cua bai hoc.

KHONG chan nguoi dung - chi canh bao de app chay mat hon va file xuat ra
nho hon. Cac moc nay cung chinh la noi dung dang nhac trong Tro giup
("App cham/giat"), nen hai noi phai khop nhau.

  IMAGE_SOFT_LIMIT_BYTES : moi anh cau hoi nen nho hon muc nay (1 MB).
  QUESTIONS_SOFT_LIMIT   : mot bai nen it cau hon muc nay (50 cau).
"""
from __future__ import annotations

IMAGE_SOFT_LIMIT_BYTES = 1 * 1024 * 1024  # 1 MB
QUESTIONS_SOFT_LIMIT = 50

_MESSAGES = {
    "image_too_large": {
        "vi": "Ảnh nặng {size} — nên dùng ảnh dưới 1 MB để app chạy mượt và file xuất ra nhỏ hơn.",
        "en": "This image is {size} — keep images under 1 MB so the app stays smooth and exports stay small.",
        "fr": "Cette image fait {size} — restez sous 1 Mo pour une application fluide et des exports légers.",
        "es": "Esta imagen ocupa {size} — usa imágenes de menos de 1 MB para que la app vaya fluida y la exportación sea ligera.",
        "de": "Dieses Bild ist {size} — Bilder unter 1 MB halten die App flüssig und die Exporte klein.",
    },
    "many_questions": {
        "vi": "Bài đang có {n} câu — trên 50 câu nên tách nhỏ để game chạy mượt hơn.",
        "en": "This project has {n} questions — above 50, consider splitting it for smoother play.",
        "fr": "Ce projet compte {n} questions — au-delà de 50, pensez à le diviser pour une lecture plus fluide.",
        "es": "Este proyecto tiene {n} preguntas — por encima de 50, conviene dividirlo para jugar mejor.",
        "de": "Dieses Projekt hat {n} Fragen — über 50 lohnt sich ein Teilen für flüssigeres Spiel.",
    },
}


def _normalize_lang(lang) -> str:
    try:
        code = str(lang or "").strip().lower().replace("_", "-").split("-")[0]
    except Exception:
        code = ""
    return code if code in ("vi", "en", "fr", "es", "de") else "en"


def format_size(num_bytes: int) -> str:
    """1.4 MB / 850 KB (chu thuong de doc, dung cho ca 5 ngon ngu)."""
    try:
        value = float(num_bytes)
    except Exception:
        return "?"
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.0f} KB"
    return f"{int(value)} B"


def file_size(path) -> int:
    """Kich thuoc file (byte), 0 neu khong doc duoc."""
    try:
        import os

        return int(os.path.getsize(str(path)))
    except Exception:
        return 0


def image_size_warning(path, lang="vi"):
    """Canh bao neu anh lon hon moc - tra ve chuoi thong bao hoac None."""
    try:
        size = file_size(path)
        if not size or size <= IMAGE_SOFT_LIMIT_BYTES:
            return None
        template = _MESSAGES["image_too_large"][_normalize_lang(lang)]
        return template.format(size=format_size(size))
    except Exception:
        return None


def many_questions_warning(count, lang="vi"):
    """Canh bao neu bai qua nhieu cau - tra ve chuoi thong bao hoac None."""
    try:
        n = int(count)
        if n <= QUESTIONS_SOFT_LIMIT:
            return None
        template = _MESSAGES["many_questions"][_normalize_lang(lang)]
        return template.format(n=n)
    except Exception:
        return None