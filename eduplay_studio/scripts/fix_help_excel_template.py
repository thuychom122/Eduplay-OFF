"""Sua thong tin SAI ve mau nhap Excel trong noi dung Tro giup.

SAI: "Excel co them cot Loai cau hoi".
THAT:
  - Mau Excel sinh ra co cot: STT | Cau hoi | Dap an 1..4 | Giai thich
    (xem import_service._create_sample_xlsx: headers = STT, Cau hoi,
     Dap an 1-4, Giai thich - KHONG co cot loai cau hoi).
  - App TU DOAN loai cau hoi tu noi dung ban dien (dau "==" cho dap an dung,
    cap "trai = phai" cho ghep noi, dau ___ cho dien cho trong...).
"""
import json
import pathlib

BASE = pathlib.Path(r"E:\eduplay\v1.0\EDUPLAY-OFFLINE\eduplay_studio\eduplay\resources\i18n")

# (cum sai, cum dung) cho tung ngon ngu
FIXES = {
    "vi": [
        (
            "Excel có thêm cột <b>Loại câu hỏi</b>",
            "Excel có <b>STT, Câu hỏi, Đáp án 1–4, Giải thích</b> (loại câu hỏi được <b>tự nhận</b> từ nội dung)",
        ),
        (
            "loại câu hỏi</b> (trắc nghiệm/đúng-sai/điền chỗ trống...)",
            "loại câu hỏi được <b>tự nhận</b> từ nội dung (đáp án đúng bắt đầu bằng <b>==</b>, ghép cặp viết <b>trái = phải</b>, chỗ trống viết <b>___</b>)",
        ),
    ],
    "en": [
        (
            "Excel adds <b>Question type</b>",
            "Excel has <b>STT, Question, Answer 1–4, Explanation</b> (the type is detected from your content)",
        ),
        (
            "same plus <b>Question type</b> column",
            "same columns (STT, Question, Answer 1–4); the type is detected from your content",
        ),
    ],
    "fr": [
        (
            "Excel ajoute <b>Type de question</b>",
            "Excel a <b>N°, Question, Réponse 1–4, Explication</b> (le type est détecté d’après le contenu)",
        ),
        (
            "pareil plus <b>Type de question</b>",
            "mêmes colonnes ; le type est détecté d’après le contenu",
        ),
    ],
    "es": [
        (
            "Excel añade <b>Tipo de pregunta</b>",
            "Excel tiene <b>N.º, Pregunta, Respuesta 1–4, Explicación</b> (el tipo se detecta por el contenido)",
        ),
        (
            "igual más <b>Tipo de pregunta</b>",
            "las mismas columnas; el tipo se detecta por el contenido",
        ),
    ],
    "de": [
        (
            "Excel plus <b>Fragetyp</b>",
            "Excel hat <b>Nr., Frage, Antwort 1–4, Erklärung</b> (der Typ wird aus dem Inhalt erkannt)",
        ),
        (
            "gleich plus <b>Fragetyp</b>",
            "gleiche Spalten; der Typ wird aus dem Inhalt erkannt",
        ),
    ],
}


def main() -> int:
    for lang, pairs in FIXES.items():
        path = BASE / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        applied, missed = [], []
        for key in list(data.keys()):
            if not key.startswith("help.sections."):
                continue
            text = data[key]
            new = text
            for old, rep in pairs:
                if old in new:
                    new = new.replace(old, rep)
            if new != text:
                data[key] = new
                applied.append(key.split(".")[2])
        joined = "\n".join(
            str(v) for k, v in data.items() if k.startswith("help.sections.")
        )
        for old, _ in pairs:
            if old in joined:
                missed.append(old[:52])
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{lang}: sua o {sorted(set(applied))}")
        if missed:
            print(f"    chua khop cau nao: {missed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())