"""Re-upload EduPlay built-in templates and seed the shared library asset packs (with audio).

Usage (from the eduplay_studio folder):
    python scripts/publish_templates.py

Requires:
    - EduPlay Studio configured with a Firebase service account (Cai dat / Settings).
    - A correct system clock (Windows: Settings -> Time & Language -> Sync now).
      A wrong clock causes "invalid_grant" JWT errors.
"""
import os
import sys
import tempfile

# Console-safe output (Windows cp1252 consoles crash on Vietnamese text)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from eduplay.core.export_service import ExportService  # noqa: E402

DATABASE_URL = "https://eduplay-game-default-rtdb.firebaseio.com"

# built-in template HTML files (relative to assets_bundle)
TEMPLATES = [
    ("fishing", os.path.join("templates_fish", "fishing_game.html")),
]


def _sample_classic_project():
    return {
        "id": "template_classic",
        "name": "Quiz Classic (Mau)",
        "game_type": "quiz_classic",
        "language": "vi",
        "questions": [
            {
                "type": "multiple_choice",
                "question": "Thu do cua Viet Nam la gi?",
                "options": ["Ha Noi", "Ho Chi Minh", "Da Nang", "Can Tho"],
                "correct_answer": 0,
            },
            {
                "type": "true_false",
                "question": "Mat troi moc o huong Dong.",
                "correct_answer": True,
            },
        ],
    }


def _safe(text):
    try:
        return str(text or "")
    except Exception:
        return ""


def main():
    es = ExportService()

    print("== 1) Seeding library asset packs (images + audio) ==")
    for profile in ("classic", "fishing", "millionaire"):
        r = es.publish_library_asset_pack(profile, DATABASE_URL)
        if r.get("skipped"):
            status = "SKIP"
        else:
            status = "OK" if r.get("ok") else "FAIL"
        err = _safe(r.get("error", "")).encode("ascii", "replace").decode("ascii")
        print(f"  [{status}] {profile} key={r.get('key')} error={err}")

    print("\n== 2) Publishing built-in templates ==")
    for profile, rel in TEMPLATES:
        path = os.path.join(str(es.assets_dir), rel)
        if not os.path.exists(path):
            print(f"  [SKIP] template not found: {path}")
            continue
        project_data = {
            "name": profile,
            "game_type": profile,
            "asset_pack_profile": profile,
        }
        r = es.publish_to_firebase(
            path,
            profile,
            DATABASE_URL,
            project_id=profile,
            project_data=project_data,
            allow_overwrite=True,
        )
        ok = isinstance(r, dict) and r.get("ok")
        print(f"  [{'OK' if ok else 'FAIL'}] {profile}")
        print(f"      play_link: {r.get('play_link', '')}")
        if not ok:
            err = _safe(r.get("error", "")).encode("ascii", "replace").decode("ascii")
            print(f"      error: {err}")

    print("\n== 3) Building & publishing Classic example game ==")
    try:
        project = _sample_classic_project()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "classic_export")
            ok_export = es.export_to_html(
                project,
                out_dir,
                bundle_resources=True,
                single_file=True,
                output_filename="Quiz_Classic_Mau",
            )
            html_file = os.path.join(out_dir, "Quiz_Classic_Mau.html")
            if not (ok_export and os.path.exists(html_file)):
                print(f"  [FAIL] export_to_html did not produce {html_file}")
            else:
                r = es.publish_to_firebase(
                    html_file,
                    "Quiz Classic (Mau)",
                    DATABASE_URL,
                    project_id="template_classic",
                    project_data=project,
                    allow_overwrite=True,
                )
                ok = isinstance(r, dict) and r.get("ok")
                print(f"  [{'OK' if ok else 'FAIL'}] classic example")
                print(f"      play_link: {r.get('play_link', '')}")
                if not ok:
                    err = _safe(r.get("error", "")).encode("ascii", "replace").decode("ascii")
                    print(f"      error: {err}")
    except Exception as e:
        err = _safe(e).encode("ascii", "replace").decode("ascii")
        print(f"  [FAIL] classic example publish threw: {err}")


if __name__ == "__main__":
    main()
