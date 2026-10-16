# -*- coding: utf-8 -*-
"""Xoa sach state AI do app tao tren may (de test lai tu dau).

Xoa:
  1. %APPDATA%/EduPlayStudio/ai_memory.json (bo nho roaming)
  2. Documents/EduPlay/Settings/ai_memory.json (mirror)
  3. Documents/EduPlay/Settings/ai_proxy_token.txt (token AI server)
  4. settings.json: key "ai_memory" + device_auth.{device_key,
     machine_fingerprint, last_bound_at, device_id} (giua lai ai_settings
     cau hinh server + api key nguoi dung tu nhap).

Chay:  python tools/reset_ai_state.py
"""
import json
import os
import sys
from pathlib import Path


def _remove_file(path: Path, removed: list, missing: list) -> None:
    try:
        if path and path.is_file():
            try:
                size = path.stat().st_size
            except Exception:
                size = -1
            path.unlink()
            removed.append(f"{path} ({size} bytes)")
        else:
            missing.append(str(path))
    except Exception as e:
        missing.append(f"{path} (khong xoa duoc: {e})")


def _documents_settings_dir() -> Path | None:
    try:
        here = Path(__file__).resolve()
        root = here.parent.parent
        sys.path.insert(0, str(root / "eduplay_studio"))
        from eduplay.core.path_resolver import PathResolver

        d = PathResolver.resolve_settings_dir()
        return Path(d)
    except Exception:
        pass
    try:
        home = Path.home()
        for cand in (home / "OneDrive" / "Documents", home / "Documents"):
            p = cand / "EduPlay" / "Settings"
            if p.is_dir():
                return p
    except Exception:
        pass
    return None


def main() -> int:
    removed: list = []
    missing: list = []
    settings_notes: list = []

    # 1. roaming memory
    try:
        base = (os.environ.get("APPDATA") or "").strip()
        if base:
            _remove_file(Path(base) / "EduPlayStudio" / "ai_memory.json", removed, missing)
        else:
            missing.append("%APPDATA% (khong xac dinh)")
    except Exception as e:
        missing.append(f"roaming ({e})")

    # 2+3. documents mirror + token
    docs = _documents_settings_dir()
    if docs is not None:
        _remove_file(docs / "ai_memory.json", removed, missing)
        _remove_file(docs / "ai_proxy_token.txt", removed, missing)
        # 4+5. settings.json
        settings_file = docs / "settings.json"
        try:
            if settings_file.is_file():
                raw = settings_file.read_text(encoding="utf-8")
                data = json.loads(raw) if raw.strip() else {}
                changed = False
                if isinstance(data, dict):
                    if "ai_memory" in data:
                        data.pop("ai_memory", None)
                        changed = True
                        settings_notes.append("da xoa key 'ai_memory'")
                    dev = data.get("device_auth")
                    if isinstance(dev, dict):
                        for k in ("device_key", "machine_fingerprint", "last_bound_at", "device_id"):
                            if dev.get(k):
                                dev[k] = ""
                                changed = True
                        settings_notes.append("da reset device_auth (device_key/m fingerprint/last_bound_at/device_id)")
                    if changed:
                        settings_file.write_text(
                            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
                        )
                    else:
                        settings_notes.append("settings.json khong co gi de xoa")
            else:
                missing.append(str(settings_file))
        except Exception as e:
            missing.append(f"settings.json ({e})")
    else:
        missing.append("Documents/EduPlay/Settings (khong tim thay)")

    print("== Da xoa ==")
    for r in removed:
        print("  [x] " + r)
    if settings_notes:
        print("== settings.json ==")
        for n in settings_notes:
            print("  [x] " + n)
    print("== Khong co / bo qua ==")
    for m in missing:
        print("  [ ] " + m)
    print(f"\nTong: xoa {len(removed)} file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
