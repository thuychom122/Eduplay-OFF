"""Stage the Firebase Hosting directory for deployment.

Copies the viewer web app into a clean staging folder, excluding sensitive
Firebase credentials (service-account files, fernet keys, admin SDK JSON).

Supported sources:
    - "modern":  <repo_root>/eduplay_studio/eduplay/resources/firebase_hosting
    - "legacy":  <repo_root>/firebase_hosting
"""

import shutil
import sys
from pathlib import Path


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parent


def resolve_hosting_source(source: str = "modern", repo_root=None) -> Path:
    root = Path(repo_root) if repo_root else _default_repo_root()
    source_key = str(source or "modern").strip().lower()
    if source_key == "legacy":
        return root / "firebase_hosting"
    return root / "eduplay_studio" / "eduplay" / "resources" / "firebase_hosting"


def _is_sensitive(name: str) -> bool:
    lowered = str(name or "").lower()
    if "service_account" in lowered or "serviceaccount" in lowered:
        return True
    if "adminsdk" in lowered and lowered.endswith(".json"):
        return True
    if lowered.endswith(".fernet"):
        return True
    if lowered.endswith(".b64") and "firebase" in lowered:
        return True
    return False


def stage_hosting_directory(source: str = "modern", repo_root=None) -> Path:
    """Copy the hosting source into a clean staging dir, minus secrets."""
    root = Path(repo_root) if repo_root else _default_repo_root()
    src = resolve_hosting_source(source, root)
    if not src.is_dir():
        raise FileNotFoundError(f"Hosting source not found: {src}")

    source_key = str(source or "modern").strip().lower() or "modern"
    stage = root / f".firebase_hosting_stage_{source_key}"
    if stage.exists():
        shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        if _is_sensitive(item.name):
            continue
        target = stage / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    return stage


if __name__ == "__main__":
    chosen = sys.argv[1] if len(sys.argv) > 1 else "modern"
    print(stage_hosting_directory(chosen))
