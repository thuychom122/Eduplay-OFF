"""Sua ten NUT trong noi dung Tro giup cho khop 100% voi nhan hien thi cua app.

Bao cao audit_help_button_names.py chi ra cac cum in dam khong khop ten
nut nao trong app. Day la danh sach sua cho cac cai do (bo qua nhung cum
chi de nhan manh chu).
"""
import json
import pathlib

BASE = pathlib.Path(r"E:\eduplay\v1.0\EDUPLAY-OFFLINE\eduplay_studio\eduplay\resources\i18n")

# moi ngon ngu: (cum sai -> cum dung)
FIXES = {
    "vi": [
        ("<b>Xem nhanh</b> (con mắt)", "<b>Xem câu chọn</b> (con mắt)"),
        ("bấm <b>Chơi</b> → chọn bài", "bấm <b>CHƠI</b> → chọn bài"),
        ("<b>Chỉnh thẻ</b>", "<b>Chỉnh sửa thẻ</b>"),
        ("<b>Cho phép truy cập Internet</b>", "<b>Cho phép AI tra cứu internet</b>"),
        ("<b>Cho phép tải ảnh</b>", "<b>Cho phép tải ảnh về và gán vào câu hỏi</b>"),
        ("<b>Đúng / Sai</b>", "<b>Đúng/Sai</b>"),
        ("<b>Điền chỗ trống</b>", "<b>Điền vào chỗ trống</b>"),
        ("thẻ <b>Thư viện</b>", "thẻ <b>Thư viện Media</b>"),
        ("<b>Cài/Sửa</b>", "<b>Cài đặt</b>"),
    ],
    "en": [
        ("<b>Quick view</b>", "<b>Preview Selected</b>"),
        ("<b>PLAY</b>", "<b>PLAY</b>"),
        ("<b>Edit tag</b>", "<b>Edit tags</b>"),
        ("<b>True / False</b>", "<b>True/False</b>"),
        ("<b>Fill in the blank</b>", "<b>Fill in the Blank</b>"),
        ("<b>Media</b> tab", "<b>Media Library</b> tab"),
    ],
    "fr": [
        ("<b>Xem nhanh</b>", "<b>Aperçu ciblé</b>"),
        ("<b>Chơi</b>", "<b>JOUER</b>"),
        ("<b>Chỉnh thẻ</b>", "<b>Modifier les étiquettes</b>"),
        ("<b>Cho phép truy cập Internet</b>", "<b>Autoriser la recherche sur internet</b>"),
        ("<b>Cho phép tải ảnh</b>", "<b>Autoriser le téléchargement d’images</b>"),
        ("<b>Đúng / Sai</b>", "<b>Vrai/Faux</b>"),
        ("<b>Điền chỗ trống</b>", "<b>Texte à trous</b>"),
        ("<b>Thư viện</b>", "<b>Médias</b>"),
        ("<b>Cài/Sửa</b>", "<b>Installer</b>"),
    ],
    "es": [
        ("<b>Xem nhanh</b>", "<b>Vista previa</b>"),
        ("<b>Chơi</b>", "<b>JUGAR</b>"),
        ("<b>Chỉnh thẻ</b>", "<b>Editar etiquetas</b>"),
        ("<b>Cho phép truy cập Internet</b>", "<b>Permitir búsqueda en internet</b>"),
        ("<b>Cho phép tải ảnh</b>", "<b>Permitir descargar imágenes para preguntas</b>"),
        ("<b>Đúng / Sai</b>", "<b>Verdadero/Falso</b>"),
        ("<b>Điền chỗ trống</b>", "<b>Rellenar espacios</b>"),
        ("<b>Thư viện</b>", "<b>Medios</b>"),
        ("<b>Cài/Sửa</b>", "<b>Instalar</b>"),
    ],
    "de": [
        ("<b>Xem nhanh</b>", "<b>Auswahl ansehen</b>"),
        ("<b>Chơi</b>", "<b>SPIELEN</b>"),
        ("<b>Chỉnh thẻ</b>", "<b>Tags bearbeiten</b>"),
        ("<b>Cho phép truy cập Internet</b>", "<b>Internet-Suche erlauben</b>"),
        ("<b>Cho phép tải ảnh</b>", "<b>Bilder für Fragen herunterladen erlauben</b>"),
        ("<b>Đúng / Sai</b>", "<b>Richtig/Falsch</b>"),
        ("<b>Điền chỗ trống</b>", "<b>Lückentext</b>"),
        ("<b>Thư viện</b>", "<b>Medien</b>"),
        ("<b>Cài/Sửa</b>", "<b>Installieren</b>"),
    ],
}


def main() -> int:
    for lang, pairs in FIXES.items():
        path = BASE / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        applied, missed = [], []
        for key in list(data.keys()):
            if not key.startswith("help."):
                continue
            text = data[key]
            new = text
            for old, rep in pairs:
                if old in new:
                    new = new.replace(old, rep)
            if new != text:
                data[key] = new
                applied.append(key.split(".")[-1] or key)
        # ghi nhan cum khong tim thay (vi da dung ngon ngu khac)
        joined = "\n".join(str(v) for k, v in data.items() if k.startswith("help."))
        for old, _rep in pairs:
            if old in joined:
                missed.append(old[:44])
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{lang}: sua o {len(applied)} muc")
        if missed:
            print(f"    chua thay (khong ton tai o ngon ngu nay): {missed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())