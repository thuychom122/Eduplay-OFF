"""Lam moi noi dung help: bo khoi "Phan N" rong, emoji lap, mau hardcode -> token."""
import json
import pathlib
import re
import sys

BASE = pathlib.Path(r"E:\eduplay\v1.0\EDUPLAY-OFFLINE\eduplay_studio\eduplay\resources\i18n")

# Mau -> token de runtime doi theo theme (sang/troi)
TOKENS = {
    "#0F172A": "{{fg}}",
    "#334155": "{{fg_soft}}",
    "#475569": "{{fg_soft}}",
    "#64748B": "{{muted}}",
    "#FFFFFF": "{{bg_card}}",
    "#F8FAFC": "{{bg_card}}",
    "#E2E8F0": "{{border}}",
    "#86EFAC": "{{border}}",
    "#F0FDF4": "{{surface_ok}}",
    "#EFF6FF": "{{surface_info}}",
    "#FFF7ED": "{{surface_warn}}",
    "#FAF5FF": "{{surface_accent}}",
    "#22C55E": "{{ok}}",
    "#12B76A": "{{ok}}",
    "#065F46": "{{ok_text}}",
    "#3B82F6": "{{info}}",
    "#1E40AF": "{{info_text}}",
    "#F97316": "{{warn}}",
    "#F79009": "{{warn}}",
    "#7F56D9": "{{accent}}",
    "#A855F7": "{{accent}}",
}

# Tieu de rong lap di o moi muc -> bo, noi dung dung nghia ben duoi
BOILER = (
    "Giới thiệu",
    "Hướng dẫn chi tiết",
    "Tính năng nâng cao",
    "Tính năng mới",
    "Danh sách phím",
    "Hỏi & đáp",
    "Giao diện chính ở đâu?",
    "Introduction",
    "Detailed guide",
)

EMOJI = r"\U0001F300-\U0001FAFF☀-➿⬀-⯿️"


def strip_boilerplate(html: str) -> str:
    out = html
    for name in BOILER:
        pat = re.compile(
            r"<div[^>]*>\s*(?:[\U0001F300-\U0001FAFF☀-➿⬀-⯿️✦-✯\s])*"
            r"(?:Phần\s*\d+\s*[—–-]\s*|Part\s*\d+\s*[—–-]\s*)"
            + re.escape(name)
            + r"\s*</div>",
            re.IGNORECASE,
        )
        out = pat.sub("", out)
    # Con "Phan 3 — Tri nho cua Edubot": bo dam "Phan N — ", giu lai ten that
    out = re.sub(
        r"((?:[\U0001F300-\U0001FAFF☀-➿⬀-⯿]\s*))(?:Phần|Part)\s*\d+\s*[—–-]\s*",
        r"\1",
        out,
    )
    return out


def dedupe_emoji(html: str) -> str:
    # "💡 📌 Phần 1" hoac "📂 📌 Phần 1" -> giu 1 emoji
    out = re.sub(r"((?:[\U0001F300-\U0001FAFF☀-➿⬀-⯿️])\s*)\1+", r"\1", html)
    out = re.sub(
        r"((?:[\U0001F300-\U0001FAFF☀-➿⬀-⯿️])\s+)([\U0001F300-\U0001FAFF☀-➿⬀-⯿️]\s*)", r"\1", out
    )
    return out


def fix_glyphs(html: str) -> str:
    # U+1F6DF (Ring buoy) Segoe UI Emoji Windows thieu glyph -> hien o vuong
    out = html.replace("\U0001F6DF", "⚠").replace("⚠️", "⚠")
    # Emoji bi bo header con lai: "🛠️ ️ " -> "🛠️ "
    out = re.sub("([\U0001F300-\U0001FAFF☀-➿⬀-⯿])\uFE0F\uFE0F", r"\1", out)
    out = re.sub(r"([\U0001F300-\U0001FAFF☀-➿⬀-⯿])\uFE0F(?=\s*<)", r"\1", out)
    return out


def tokenize_colors(html: str) -> str:
    out = html
    for hexval, token in TOKENS.items():
        out = re.sub(hexval, token, out, flags=re.IGNORECASE)
    return out


def main() -> int:
    total = 0
    for lang in ("vi", "en", "fr", "es", "de"):
        path = BASE / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for key in list(data.keys()):
            if not (key.startswith("help.sections.") and key.endswith(".content")):
                continue
            old = data[key]
            new = old
            new = strip_boilerplate(new)
            new = dedupe_emoji(new)
            new = fix_glyphs(new)
            new = tokenize_colors(new)
            if new != old:
                data[key] = new
                changed += 1
        if changed:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        total += changed
        print(f"{lang}: {changed} section(s) updated")
    print(f"total {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())