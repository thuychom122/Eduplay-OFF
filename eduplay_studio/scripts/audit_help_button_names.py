"""Bao cao: cac chuoi in dam (<b>..</b>) trong noi dung Tro giup co khop
voi ten nut that cua app hay khong.

Khong phai moi cum in dam deu la ten nut (nhieu cum chi de nhan manh), nen
day la BAO CAO de nguoi doc tu kiem, khong phai test.
"""
import json
import pathlib
import re

BASE = pathlib.Path(r"E:\eduplay\v1.0\EDUPLAY-OFFLINE\eduplay_studio\eduplay\resources\i18n")
SHOWN = [
    "quickstart", "editor", "import", "media", "browse", "preview", "export",
    "powerpoint_addin", "edubot", "settings", "keyboard_shortcuts", "troubleshooting",
]
# Cac cum co the la ten nut (co dau cham hoac chu hoa, it chu)
LIKELY_BUTTON = re.compile(r"^[^.!?]{3,40}$")


def main() -> int:
    lang = "vi"
    data = json.loads((BASE / f"{lang}.json").read_text(encoding="utf-8"))
    # tap tat ca nhan hien thi cua app
    labels = set()
    for key, value in data.items():
        if isinstance(value, str) and len(value) <= 60:
            labels.add(value.strip())
    # them mot so nhan ngai thuong Viet (tieng Anh/ky tu)
    for extra in (
        "Ctrl+K", "Ctrl+T", "Ctrl+Z", "Ctrl+Y", "Esc", "F5", "Shift+F5",
        "PowerPoint", "Insert", "HTML Frame", "EduPlay", "crash.log", "Media",
    ):
        labels.add(extra)

    suspects = {}
    for section in SHOWN:
        text = str(data.get(f"help.sections.{section}.content") or "")
        for m in re.finditer(r"<b>(.*?)</b>", text, re.S):
            frag = re.sub(r"\s+", " ", m.group(1)).strip()
            if not frag or not LIKELY_BUTTON.match(frag):
                continue
            if frag in labels:
                continue
            suspects.setdefault(frag, set()).add(section)

    if not suspects:
        print("Moi cum in deu khop voi nhan hien thi cua app.")
        return 0
    print("Can xac nhan (cum in dam khong khop ten nut nao trong app):\n")
    for frag, sections in sorted(suspects.items()):
        print(f"  - {frag!r:52} ({', '.join(sorted(sections))})")
    print(f"\nTong: {len(suspects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())