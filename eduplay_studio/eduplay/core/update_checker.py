from __future__ import annotations

import os
import tempfile
import threading
import requests
import re
import logging
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


def _normalize_version(v: str) -> tuple[list[int], str | None]:
    if not v:
        return [0], None
    match = re.match(r"^v?([0-9]+(?:\.[0-9]+)*)(?:[-_\.]+(.+))?$", v.strip(), re.IGNORECASE)
    if not match:
        parts = re.findall(r"\d+", v)
        return ([int(p) for p in parts] if parts else [0]), None
    numbers = [int(p) for p in match.group(1).split('.') if p.isdigit()]
    suffix = match.group(2)
    return numbers or [0], suffix


def _compare_prerelease(a: str | None, b: str | None) -> int:
    if a is None and b is None:
        return 0
    if a is None:
        return 1
    if b is None:
        return -1
    # compare by segments: digits numerically, text lexically
    def segments(value: str) -> list[str]:
        return re.findall(r"[0-9]+|[A-Za-z]+", value)
    segs_a = segments(a.lower())
    segs_b = segments(b.lower())
    for seg_a, seg_b in zip(segs_a, segs_b):
        if seg_a == seg_b:
            continue
        if seg_a.isdigit() and seg_b.isdigit():
            return int(seg_a) - int(seg_b)
        if seg_a.isdigit():
            return -1
        if seg_b.isdigit():
            return 1
        return -1 if seg_a < seg_b else 1
    return len(segs_a) - len(segs_b)


def version_is_newer(current: str, candidate: str) -> bool:
    cur_nums, cur_suffix = _normalize_version(current)
    cand_nums, cand_suffix = _normalize_version(candidate)
    n = max(len(cur_nums), len(cand_nums))
    cur_nums += [0] * (n - len(cur_nums))
    cand_nums += [0] * (n - len(cand_nums))
    if cand_nums != cur_nums:
        return cand_nums > cur_nums
    # equal numeric version
    # stable release is newer than pre-release with same numbers
    result = _compare_prerelease(cur_suffix, cand_suffix)
    return result < 0


class UpdateChecker(QObject):
    """Background updater helper.

    Emits signals when an update is detected and while downloading.
    """

    update_available = Signal(dict)
    download_progress = Signal(int)
    download_completed = Signal(str)
    error = Signal(str)
    # Emitted when a check has finished (regardless of found update)
    check_finished = Signal()

    def __init__(self, settings_manager, current_version: str = "0.0.0"):
        super().__init__()
        self.settings = settings_manager
        self.current_version = str(current_version or "0.0.0")
        self._api_url = "https://api.github.com/repos/Tan0807-creat3/EduPlay-Studio/releases/latest"
        self._cancel_event = threading.Event()

    def check_for_update(self) -> None:
        """Run the check in a background thread."""
        t = threading.Thread(target=self._do_check, daemon=True)
        t.start()

    def _do_check(self) -> None:
        try:
            # Inform console that a check is starting
            try:
                print("Đang kiểm tra cập nhật...")
            except Exception:
                pass
            logger.debug("Checking for updates: current=%s", self.current_version)
            if not bool(self.settings.get("auto_update.enable", True)):
                logger.debug("Auto-update disabled in settings")
                return
            resp = requests.get(self._api_url, timeout=10)
            # The /releases/latest endpoint returns 404 when there are only
            # pre-releases. In that case, fall back to listing releases and
            # pick the newest entry.
            if resp.status_code == 404:
                logger.debug("/releases/latest returned 404, falling back to /releases list")
                try:
                    list_url = self._api_url.replace("/releases/latest", "/releases")
                    list_resp = requests.get(list_url, timeout=10)
                    if list_resp.status_code != 200:
                        logger.debug("Fallback releases list returned HTTP %s", list_resp.status_code)
                        return
                    releases = list_resp.json()
                    if not releases:
                        logger.debug("No releases found in list response")
                        return
                    data = releases[0]
                except Exception:
                    logger.exception("Error fetching releases list fallback")
                    return
            else:
                if resp.status_code != 200:
                    logger.debug("Update check returned HTTP %s", resp.status_code)
                    return
                data = resp.json()
            tag = str(data.get("tag_name") or data.get("name") or "")
            if not tag:
                logger.debug("No tag found in release payload")
                return
            logger.debug("Latest release tag: %s", tag)
            if version_is_newer(self.current_version, tag):
                payload = {
                    "tag_name": tag,
                    "name": data.get("name", ""),
                    "body": data.get("body", ""),
                    "assets": data.get("assets", []),
                    "html_url": data.get("html_url", ""),
                }
                logger.info("Update available: %s", tag)
                self.update_available.emit(payload)
        except Exception as e:
            logger.exception("Error while checking for update")
            try:
                self.error.emit(str(e))
            except Exception:
                pass
        finally:
            try:
                self.check_finished.emit()
            except Exception:
                pass

    def download_asset(self, url: str, filename: Optional[str] = None) -> None:
        """Download the given URL in background and emit progress/complete."""
        # Clear previous cancel flag
        self._cancel_event.clear()
        t = threading.Thread(target=self._do_download, args=(url, filename), daemon=True)
        t.start()

    def cancel_download(self) -> None:
        """Signal that an in-progress download should be cancelled."""
        logger.info("Download cancellation requested")
        self._cancel_event.set()

    def _do_download(self, url: str, filename: Optional[str]) -> None:
        tmp_path = None
        try:
            logger.info("Starting download: %s", url)
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code != 200:
                msg = f"Download failed: HTTP {r.status_code}"
                logger.error(msg)
                self.error.emit(msg)
                return
            total = int(r.headers.get("content-length") or 0)
            if not filename:
                filename = os.path.join(tempfile.gettempdir(), os.path.basename(url) or "setup.exe")
            tmp_path = filename
            written = 0
            chunk_size = 8192
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if self._cancel_event.is_set():
                        logger.info("Download cancelled by user")
                        try:
                            f.close()
                        except Exception:
                            pass
                        try:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
                        except Exception:
                            pass
                        try:
                            self.error.emit("cancelled")
                        except Exception:
                            pass
                        return
                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)
                    if total:
                        pct = int(written * 100 / total)
                        try:
                            self.download_progress.emit(pct)
                        except Exception:
                            pass
            logger.info("Download completed: %s", tmp_path)
            try:
                self.download_completed.emit(tmp_path)
            except Exception:
                pass
        except Exception as e:
            logger.exception("Error during download")
            try:
                # cleanup partial file
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            try:
                self.error.emit(str(e))
            except Exception:
                pass
