"""
Auto update helpers for EduPlay Studio.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from eduplay.core.path_resolver import PathResolver


GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/Tan0807-creat3/EduPlay-Studio/releases/latest"
DEFAULT_USER_AGENT = "EduPlay-Studio-Updater"


def normalize_version(version: str) -> tuple[int, ...]:
    text = str(version or "").strip()
    if text.lower().startswith("v"):
        text = text[1:]
    numbers = [int(part) for part in re.findall(r"\d+", text)]
    return tuple(numbers)


def is_newer_version(current_version: str, release_version: str) -> bool:
    current = normalize_version(current_version)
    release = normalize_version(release_version)
    width = max(len(current), len(release), 1)
    current = current + (0,) * (width - len(current))
    release = release + (0,) * (width - len(release))
    return release > current


def extract_release_version(release_data: Dict[str, Any]) -> str:
    for key in ("tag_name", "name"):
        value = str((release_data or {}).get(key) or "").strip()
        if value:
            return value
    return ""


def pick_windows_installer_asset(release_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    assets = (release_data or {}).get("assets") or []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip().lower()
        url = str(asset.get("browser_download_url") or "").strip()
        if not name or not url:
            continue
        if name.endswith(".exe") and "setup" in name:
            return asset
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip().lower()
        url = str(asset.get("browser_download_url") or "").strip()
        if name.endswith(".exe") and url:
            return asset
    return None


def fetch_latest_release(
    requests_module=None,
    url: str = GITHUB_LATEST_RELEASE_URL,
    timeout: int = 12,
) -> Dict[str, Any]:
    req = requests_module or requests
    response = req.get(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": DEFAULT_USER_AGENT,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Invalid GitHub release payload.")
    return payload


def check_for_update(
    current_version: str,
    requests_module=None,
    url: str = GITHUB_LATEST_RELEASE_URL,
) -> Dict[str, Any]:
    release_data = fetch_latest_release(requests_module=requests_module, url=url)
    release_version = extract_release_version(release_data)
    installer_asset = pick_windows_installer_asset(release_data)
    installer_url = ""
    installer_name = ""
    if installer_asset:
        installer_url = str(installer_asset.get("browser_download_url") or "").strip()
        installer_name = str(installer_asset.get("name") or "").strip()
    has_update = bool(release_version) and is_newer_version(current_version, release_version)
    return {
        "has_update": has_update,
        "current_version": str(current_version or "").strip(),
        "release_version": release_version,
        "release_name": str(release_data.get("name") or release_version or "").strip(),
        "release_notes": str(release_data.get("body") or "").strip(),
        "published_at": str(release_data.get("published_at") or "").strip(),
        "html_url": str(release_data.get("html_url") or "").strip(),
        "installer_name": installer_name,
        "installer_url": installer_url,
        "release_data": release_data,
    }


def ensure_update_download_dir() -> Path:
    try:
        base_dir = PathResolver.resolve_settings_dir()
    except Exception:
        base_dir = Path(tempfile.gettempdir()) / "EduPlay" / "Settings"
    download_dir = Path(base_dir) / "updates"
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def _safe_installer_name(name: str, version: str) -> str:
    raw_name = str(name or "").strip()
    if raw_name:
        candidate = os.path.basename(raw_name)
    else:
        version_text = re.sub(r"[^0-9A-Za-z._-]+", "-", str(version or "").strip() or "latest")
        candidate = f"EduPlay-Studio-{version_text}-Setup.exe"
    lower = candidate.lower()
    if not lower.endswith(".exe"):
        candidate += ".exe"
    return candidate


def download_installer(
    installer_url: str,
    version: str = "",
    installer_name: str = "",
    requests_module=None,
    chunk_size: int = 1024 * 256,
) -> str:
    url = str(installer_url or "").strip()
    if not url:
        raise ValueError("Missing installer URL.")
    req = requests_module or requests
    download_dir = ensure_update_download_dir()
    filename = _safe_installer_name(installer_name, version)
    target_path = download_dir / filename

    response = req.get(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=60,
        stream=True,
    )
    response.raise_for_status()

    with open(target_path, "wb") as fh:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                fh.write(chunk)
    return str(target_path)
