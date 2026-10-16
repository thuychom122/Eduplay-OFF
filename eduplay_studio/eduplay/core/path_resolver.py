r"""
PathResolver — Single source of truth for all EduPlay file-system paths.

Consolidates Documents, Settings, Projects, Cache, PublishCache, LocalAppData,
TrustedSlides and VSTO add-in paths so every module resolves them the same way,
including machines with OneDrive redirection or non-standard profiles.

OneDrive-aware: handles SHGetKnownFolderPath GUIDs, OneDrive env vars,
User Shell Folders registry, home OneDrive scan, localized folder names
(Tài liệu, Màn hình nền, Tải xuống, Hình ảnh, Âm nhạc), file:// URI,
percent-encoding, long path prefix \\?\ and short 8.3 names via
GetLongPathNameW, reparse points/junctions, and Files-On-Demand hydration.

Global patch: install_global_patches() monkey-patches open/Path.exists etc
with recursion guard _RESOLVING to make the entire process OneDrive-aware.

Encoding: utf-8 (supports Vietnamese diacritics).
"""
import os
import re
import sys
import stat
import builtins
import functools
import tempfile
import threading
import urllib.parse
from pathlib import Path
from typing import Optional, List

# --- Eager imports for patch-safety (see below) ---
# install_global_patches() replaces builtins.open / os.path.exists / isfile
# process-wide. Resolver helpers reachable from those patched functions
# (normalize_user_path, _to_long_path, resolve_documents, ...) must NEVER
# trigger a *fresh* module import: a lazy `import ctypes` executed from
# inside a patched call fires PEP-302 import hooks (notably shiboken's
# signature loader) -> inspect.getsource -> os.path.exists (patched!) ->
# normalize_user_path -> _to_long_path -> `import ctypes` again, i.e.
# unbounded mutual recursion ending in stack overflow / native crash.
# (Frozen builds always trip it: Nuitka layouts contain 8.3 short path
# components like NUITKA~1, so _to_long_path is always engaged there.)
# Importing these modules once here - before any patch is installed -
# turns every later `import X` into a harmless sys.modules lookup.
try:
    import ctypes as _ctypes_preload  # noqa: F401
    from ctypes import wintypes as _wintypes_preload  # noqa: F401
except Exception:  # pragma: no cover - non-Windows / stripped envs
    _ctypes_preload = None  # type: ignore
    _wintypes_preload = None  # type: ignore
try:
    import winreg as _winreg_preload  # noqa: F401
except Exception:  # pragma: no cover - non-Windows
    _winreg_preload = None  # type: ignore
try:
    import uuid as _uuid_preload  # noqa: F401
except Exception:  # pragma: no cover - should never happen
    _uuid_preload = None  # type: ignore

_KNOWN_FOLDER_GUIDS = {
    "Documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "Desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "Pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "Music": "{4BD8D571-6D19-48D3-BE97-422220080E43}",
    "Videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
}
_FOLDER_ALIASES = {
    "Documents": ["Documents", "T\xe0i li\u1ec7u", "My Documents", "Tai lieu"],
    "Desktop": ["Desktop", "M\xe0n h\xecnh n\u1ec1n", "Man hinh nen", "B\xe0n l\xe0m vi\u1ec7c"],
    "Downloads": ["Downloads", "T\u1ea3i xu\u1ed1ng", "Tai xuong", "T\u1ea3i v\u1ec1", "Download"],
    "Pictures": ["Pictures", "H\xecnh \u1ea3nh", "Hinh anh", "\u1ea2nh", "My Pictures"],
    "Music": ["Music", "\xc2m nh\u1ea1c", "Am nhac", "Nh\u1ea1c", "My Music"],
    "Videos": ["Videos", "Video", "Phim", "My Videos"],
}
_ALIAS_TO_CANONICAL = {}
for _canon, _aliases in _FOLDER_ALIASES.items():
    for _a in _aliases:
        _ALIAS_TO_CANONICAL[_a.lower()] = _canon

_RESOLVING = threading.local()

def _is_resolving() -> bool:
    return bool(getattr(_RESOLVING, "value", False))

def _set_resolving(v: bool):
    _RESOLVING.value = bool(v)

# --- Recursion depth cap for patched open()/exists() entries ---
# The patched helpers legitimately call back into resolver probing
# (normalize/resolve/hydration), which may itself touch patched calls
# (Path.exists, os.path.exists, inspect.getsource during imports, ...).
# Normally this nests 1-3 levels and terminates. But a non-terminating
# cycle is possible (e.g. frozen layouts where probed .py files do not
# exist on disk, so every level regenerates the same candidates), and
# the _is_resolving bool alone cannot catch it because inner helpers
# toggle it around raw _ORIG calls. The depth cap below makes ANY such
# cycle terminate: past the cap, entries answer straight from _ORIG.
_PATCH_DEPTH = threading.local()
_PATCH_MAX_DEPTH = 32

def _patch_depth() -> int:
    try:
        return int(getattr(_PATCH_DEPTH, "value", 0) or 0)
    except Exception:
        return 0

def _patch_enter() -> bool:
    try:
        if _patch_depth() >= _PATCH_MAX_DEPTH:
            return False
        _PATCH_DEPTH.value = _patch_depth() + 1
        return True
    except Exception:
        return False

def _patch_exit() -> None:
    try:
        _PATCH_DEPTH.value = max(0, _patch_depth() - 1)
    except Exception:
        pass

def _patch_guard(orig_name: str):
    """Decorator for the patched open()/exists()/isfile() entries.

    Guarantees termination: each nested patched call consumes one depth
    level; past _PATCH_MAX_DEPTH the call is answered from the pristine
    _ORIG function (looked up late-bound from module globals, which are
    populated when install_global_patches() runs). Normal flows never
    nest anywhere near the cap, so their behavior is unchanged.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                orig = globals().get(orig_name)
            except Exception:
                orig = None
            if orig is None:
                return fn(*args, **kwargs)
            if _is_resolving() or not _patch_enter():
                return orig(*args, **kwargs)
            try:
                return fn(*args, **kwargs)
            finally:
                _patch_exit()
        return wrapper
    return deco

_ORIG_OPEN = None
_ORIG_PATH_OPEN = None
_ORIG_EXISTS = None
_ORIG_ISFILE = None
_ORIG_PATH_EXISTS = None
_ORIG_PATH_ISFILE = None
_PATCH_INSTALLED = False

# --- Performance caches (avoid scanning registry / filesystem on every file open) ---
_CACHED_ONEDRIVE_ROOTS: list[Path] | None = None
_CACHED_ONEDRIVE_TS: float = 0.0
_CACHED_KNOWN_FOLDERS: dict[str, Optional[Path]] = {}
_CANDIDATE_CACHE: dict[str, List[str]] = {}
_CANDIDATE_CACHE_MAX = 512

class PathResolver:
    """Resolves EduPlay paths consistently across the application."""

    APP_NAME = "EduPlay"
    SETTINGS_SUBDIR = "Settings"
    PROJECTS_SUBDIR = "Projects"
    PUBLISH_CACHE_SUBDIR = "PublishCache"
    ADDIN_DIRNAME = "EduPlayPowerPointAddin"
    RUNTIME_CACHE_DIRNAME = "runtime_cache"
    PREVIEW_SUBDIR = "eduplay_preview_files"
    TRUSTED_SLIDES_SUBDIR = "TrustedSlides"
    ASSET_CACHE_DIRNAME = "EduPlayStudio"

    @staticmethod
    def resolve_documents() -> Path:
        r"""Return the real Windows Documents folder, respecting OneDrive redirection.

        Strategy (priority):
        1) SHGetKnownFolderPath GUID FDD39AD0-238F-46AF-ADB4-6C85480369C7
        2) SHGetFolderPathW CSIDL_PERSONAL (5)
        3) Registry User Shell Folders Personal
        4) OneDrive Documents candidate
        5) Path.home()/Documents fallback
        Handles Vietnamese paths and long prefix \\?\ transparently.
        """
        try:
            p = PathResolver._resolve_known_folder(_KNOWN_FOLDER_GUIDS["Documents"])
            if p is not None and str(p).strip():
                return Path(str(p).strip())
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                import ctypes
                buf = ctypes.create_unicode_buffer(32768)
                if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
                    resolved = str(buf.value or "").strip()
                    if resolved:
                        try:
                            resolved = PathResolver._to_long_path(resolved)
                        except Exception:
                            pass
                        return Path(resolved)
            except Exception:
                pass
        if sys.platform == "win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                    try:
                        val, _ = winreg.QueryValueEx(k, "Personal")
                        if val:
                            val = os.path.expandvars(str(val))
                            val = PathResolver.normalize_user_path(val)
                            if val:
                                return Path(val)
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            roots = PathResolver._get_onedrive_roots()
            for r in roots:
                cand = Path(r) / "Documents"
                if cand.exists():
                    return cand
                for alias in _FOLDER_ALIASES["Documents"]:
                    cand2 = Path(r) / alias
                    if cand2.exists():
                        return cand2
        except Exception:
            pass
        try:
            return Path.home() / "Documents"
        except Exception:
            user_profile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
            if user_profile:
                return Path(user_profile) / "Documents"
            return Path(os.getcwd()) / "Documents"

    @staticmethod
    def resolve_eduplay_root() -> Path:
        """Return Documents/EduPlay."""
        return PathResolver.resolve_documents() / PathResolver.APP_NAME

    @staticmethod
    def resolve_settings_dir() -> Path:
        """Return Documents/EduPlay/Settings."""
        settings_dir = PathResolver.resolve_eduplay_root() / PathResolver.SETTINGS_SUBDIR
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir

    @staticmethod
    def resolve_projects_dir() -> Path:
        """Return Documents/EduPlay/Projects."""
        projects_dir = PathResolver.resolve_eduplay_root() / PathResolver.PROJECTS_SUBDIR
        projects_dir.mkdir(parents=True, exist_ok=True)
        return projects_dir

    @staticmethod
    def resolve_publish_cache_dir() -> Path:
        """Return Documents/EduPlay/PublishCache."""
        cache_dir = PathResolver.resolve_eduplay_root() / PathResolver.PUBLISH_CACHE_SUBDIR
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @staticmethod
    def resolve_local_app_data() -> Path:
        """Return the LOCALAPPDATA path, falling back to temp dir."""
        base = os.environ.get("LOCALAPPDATA")
        if base:
            try:
                norm = PathResolver.normalize_user_path(base)
                if norm:
                    return Path(norm)
            except Exception:
                pass
            return Path(base)
        user_profile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
        if user_profile:
            return Path(user_profile) / "AppData" / "Local"
        return Path(tempfile.gettempdir())

    @staticmethod
    def resolve_runtime_cache_dir() -> Path:
        """Return LOCALAPPDATA/EduPlayStudio/runtime_cache."""
        cache_dir = PathResolver.resolve_local_app_data() / PathResolver.ASSET_CACHE_DIRNAME / PathResolver.RUNTIME_CACHE_DIRNAME
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @staticmethod
    def resolve_preview_dir(project_id: str) -> Path:
        """Return a per-project preview directory under the system temp folder."""
        safe_id = "".join(c for c in str(project_id) if c.isalnum() or c in ("-", "_"))
        if not safe_id:
            safe_id = "unknown"
        preview_dir = Path(tempfile.gettempdir()) / PathResolver.PREVIEW_SUBDIR / safe_id
        preview_dir.mkdir(parents=True, exist_ok=True)
        return preview_dir

    @staticmethod
    def resolve_addin_dir() -> Path:
        """Return LOCALAPPDATA/EduPlayPowerPointAddin."""
        addin_dir = PathResolver.resolve_local_app_data() / PathResolver.ADDIN_DIRNAME
        addin_dir.mkdir(parents=True, exist_ok=True)
        return addin_dir

    @staticmethod
    def resolve_trusted_slides_dir() -> Path:
        """Return LOCALAPPDATA/EduPlayPowerPointAddin/TrustedSlides."""
        trusted_dir = PathResolver.resolve_addin_dir() / PathResolver.TRUSTED_SLIDES_SUBDIR
        trusted_dir.mkdir(parents=True, exist_ok=True)
        return trusted_dir

    @staticmethod
    def resolve_asset_db_path() -> Path:
        """Return LOCALAPPDATA/EduPlayStudio/eduplay.db."""
        db_path = PathResolver.resolve_local_app_data() / PathResolver.ASSET_CACHE_DIRNAME / "eduplay.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    @staticmethod
    def resolve_ai_token_cache_path() -> Path:
        """Return Documents/EduPlay/Settings/ai_proxy_token.txt."""
        return PathResolver.resolve_settings_dir() / "ai_proxy_token.txt"

    @staticmethod
    def _get_onedrive_roots_uncached() -> List[Path]:
        r"""Uncached version of OneDrive roots detection (do not call directly, use _get_onedrive_roots)."""


        roots: List[Path] = []
        seen = set()
        def _add(p_str):
            if not p_str:
                return
            try:
                s = str(p_str).strip().strip('"').strip("'")
                if not s:
                    return
                s = os.path.expandvars(s)
                if s.startswith("\\\\?\\"):
                    s = s[4:]
                s = s.rstrip("/\\")
                if not s:
                    return
                key = s.lower() if sys.platform == "win32" else s
                if key in seen:
                    return
                seen.add(key)
                roots.append(Path(s))
            except Exception:
                pass
        for k in ["OneDrive","OneDriveCommercial","OneDriveConsumer","OneDriveBusiness","OneDriveEnterprise"]:
            try:
                v = os.environ.get(k)
                if v:
                    _add(v)
            except Exception:
                continue
        try:
            for ek, ev in os.environ.items():
                if "onedrive" in ek.lower() and ev:
                    # Trích xuất OneDrive root từ các đường dẫn như OneDrive\Documents\...
                    try:
                        # Nếu ev chứa OneDrive, chỉ lấy phần đến OneDrive (bao gồm OneDrive, OneDriveCommercial, etc.)
                        m = re.search(r"(.*?[\\/]OneDrive[^\\/]*)(?:[\\/]|$)", str(ev), re.IGNORECASE)
                        if m:
                            _add(m.group(1))
                        else:
                            _add(ev)
                    except Exception:
                        _add(ev)
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                import winreg
                for hive, subkey in [(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"), (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")]:
                    try:
                        with winreg.OpenKey(hive, subkey) as key:
                            i=0
                            while True:
                                try:
                                    name,val,typ = winreg.EnumValue(key,i)
                                    i+=1
                                    if not val or not isinstance(val,str):
                                        continue
                                    if "onedrive" in val.lower():
                                        expanded = os.path.expandvars(val)
                                        # Chỉ thêm OneDrive root, không thêm full Documents/Pictures/Desktop để tránh duplicate
                                        try:
                                            m = re.search(r"(.*?[\\/]OneDrive[^\\/]*)(?:[\\/]|$)", expanded, re.IGNORECASE)
                                            if m:
                                                _add(m.group(1))
                                            else:
                                                _add(expanded)
                                        except Exception:
                                            _add(expanded)
                                except OSError:
                                    break
                                except Exception:
                                    i+=1
                                    continue
                    except Exception:
                        continue
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\OneDrive\Accounts") as acc_key:
                        num = winreg.QueryInfoKey(acc_key)[0]
                        for idx in range(num):
                            try:
                                sub = winreg.EnumKey(acc_key, idx)
                                with winreg.OpenKey(acc_key, sub) as sk:
                                    try:
                                        val,_ = winreg.QueryValueEx(sk, "UserFolder")
                                        if val:
                                            _add(val)
                                    except Exception:
                                        pass
                            except Exception:
                                continue
                except Exception:
                    pass
            except Exception:
                pass
        try:
            home = Path.home()
            if home.exists() and home.is_dir():
                for child in home.iterdir():
                    try:
                        if child.is_dir() and child.name.lower().startswith("onedrive"):
                            _add(str(child))
                    except Exception:
                        continue
            up = os.environ.get("USERPROFILE")
            if up:
                up_path = Path(up)
                if str(up_path).lower() != str(home).lower() and up_path.exists() and up_path.is_dir():
                    for child in up_path.iterdir():
                        try:
                            if child.is_dir() and child.name.lower().startswith("onedrive"):
                                _add(str(child))
                        except Exception:
                            continue
        except Exception:
            pass
        try:
            known_paths = PathResolver._get_all_known_folder_paths()
            for kp in known_paths:
                try:
                    s = str(kp)
                    if "onedrive" not in s.lower():
                        continue
                    # Trích xuất OneDrive root, không phải full Documents/Pictures path
                    m = re.search(r"(.*?[\\/]OneDrive[^\\/]*)(?:[\\/]|$)", s, re.IGNORECASE)
                    if m:
                        _add(m.group(1))
                    else:
                        parts = re.split(r"[\\/]+", s)
                        for idx, part in enumerate(parts):
                            if part.lower().startswith("onedrive"):
                                root_str = "\\".join(parts[:idx+1]) if s[1:2]==":" else "/".join(parts[:idx+1])
                                _add(root_str)
                                break
                except Exception:
                    continue
        except Exception:
            pass
        try:
            def _sort_key(p: Path):
                try:
                    exists = 1 if p.exists() else 0
                except Exception:
                    exists = 0
                return (-exists, -len(str(p)))
            roots_sorted = sorted(roots, key=_sort_key)
            return roots_sorted
        except Exception:
            return roots

    @staticmethod
    def _get_onedrive_roots() -> List[Path]:
        """Cached wrapper - returns cached OneDrive roots for 10 minutes to avoid registry spam."""
        global _CACHED_ONEDRIVE_ROOTS, _CACHED_ONEDRIVE_TS
        try:
            import time as _time
            now = _time.monotonic()
            if _CACHED_ONEDRIVE_ROOTS is not None and (now - _CACHED_ONEDRIVE_TS) < 600:
                return list(_CACHED_ONEDRIVE_ROOTS)
        except Exception:
            pass
        try:
            roots = PathResolver._get_onedrive_roots_uncached()
        except Exception:
            roots = []
        try:
            _CACHED_ONEDRIVE_ROOTS = list(roots)
            import time as _time2
            _CACHED_ONEDRIVE_TS = _time2.monotonic()
        except Exception:
            pass
        return roots

    @staticmethod
    def _resolve_known_folder(guid_str: str) -> Optional[Path]:
        r"""Resolve Windows Known Folder via SHGetKnownFolderPath.

        GUID like {FDD39AD0-238F-46AF-ADB4-6C85480369C7}. Handles \\?\ prefix.
        """
        try:
            key = str(guid_str).strip().lower()
            if key in _CACHED_KNOWN_FOLDERS:
                return _CACHED_KNOWN_FOLDERS[key]
        except Exception:
            pass
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            from ctypes import wintypes
            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE*8)]
            clean = str(guid_str).strip().strip("{}")
            guid = GUID()
            try:
                ole32 = ctypes.windll.ole32
                hr_cls = ole32.CLSIDFromString(ctypes.c_wchar_p("{" + clean + "}"), ctypes.byref(guid))
                if hr_cls != 0:
                    raise Exception("CLSIDFromString failed")
            except Exception:
                import uuid
                u = uuid.UUID(clean)
                guid.Data1 = u.time_low
                guid.Data2 = u.time_mid
                guid.Data3 = u.time_hi_version
                b = u.bytes[8:]
                for i in range(8):
                    guid.Data4[i] = b[i]
            shell32 = ctypes.windll.shell32
            SHGetKnownFolderPath = shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
            SHGetKnownFolderPath.restype = wintypes.HRESULT
            psz_path = ctypes.c_wchar_p()
            hr = SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(psz_path))
            if hr != 0 or not psz_path.value:
                return None
            raw_path = psz_path.value
            try:
                ctypes.windll.ole32.CoTaskMemFree(psz_path)
            except Exception:
                pass
            raw_path = str(raw_path).strip()
            if not raw_path:
                return None
            if raw_path.startswith("\\\\?\\"):
                raw_path = raw_path[4:]
            try:
                raw_path = PathResolver._to_long_path(raw_path)
            except Exception:
                pass
            result = Path(raw_path)
            try:
                _CACHED_KNOWN_FOLDERS[key] = result
            except Exception:
                pass
            return result
        except Exception:
            try:
                _CACHED_KNOWN_FOLDERS[str(guid_str).strip().lower()] = None
            except Exception:
                pass
            return None

    @staticmethod
    def _get_all_known_folder_paths() -> List[Path]:
        """Return list of all known folder paths that could be resolved."""
        out: List[Path] = []
        for name, guid in _KNOWN_FOLDER_GUIDS.items():
            try:
                p = PathResolver._resolve_known_folder(guid)
                if p is not None and str(p).strip():
                    out.append(p)
            except Exception:
                continue
        try:
            home = Path.home()
            for canon in _FOLDER_ALIASES:
                if canon in ["Documents","Desktop","Downloads","Pictures","Music","Videos"]:
                    out.append(home / canon)
        except Exception:
            pass
        return out

    @staticmethod
    def _get_documents_candidates() -> List[Path]:
        """Return ordered candidates for Documents folder location."""
        cands: List[Path] = []
        seen=set()
        def _add(p):
            try:
                if p is None:
                    return
                s=str(p).strip()
                if not s:
                    return
                key=s.lower() if sys.platform=="win32" else s
                if key in seen:
                    return
                seen.add(key)
                cands.append(Path(s))
            except Exception:
                pass
        try:
            kf = PathResolver._resolve_known_folder(_KNOWN_FOLDER_GUIDS["Documents"])
            if kf is not None:
                _add(kf)
        except Exception:
            pass
        if sys.platform=="win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                    try:
                        val,_ = winreg.QueryValueEx(k,"Personal")
                        if val:
                            val=os.path.expandvars(str(val))
                            _add(val)
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            for root in PathResolver._get_onedrive_roots():
                for alias in _FOLDER_ALIASES["Documents"]:
                    _add(Path(root)/alias)
        except Exception:
            pass
        try:
            home=Path.home()
            for alias in _FOLDER_ALIASES["Documents"]:
                _add(home/alias)
            up=os.environ.get("USERPROFILE")
            if up and str(Path(up)).lower()!=str(home).lower():
                for alias in _FOLDER_ALIASES["Documents"]:
                    _add(Path(up)/alias)
        except Exception:
            pass
        try:
            _add(Path.cwd()/"Documents")
        except Exception:
            pass
        return cands

    @staticmethod
    def _strip_file_uri(raw: str) -> str:
        r"""Strip file:// URI prefix including file:/// and percent-decode."""
        s=str(raw or "").strip()
        if not s:
            return ""
        low=s.lower()
        if low.startswith("file:"):
            try:
                parsed=urllib.parse.urlparse(s)
                path_part=urllib.parse.unquote(parsed.path or "")
                if re.match(r"^/[A-Za-z]:", path_part):
                    path_part=path_part[1:]
                if parsed.netloc and parsed.netloc.lower() not in ("","localhost"):
                    path_part=f"//{parsed.netloc}{path_part}"
                s=path_part
            except Exception:
                s=re.sub(r"(?i)^file:/+", "", s)
                try:
                    s=urllib.parse.unquote(s)
                except Exception:
                    pass
        else:
            if "%" in s and not s.lower().startswith("data:"):
                try:
                    if re.search(r"%[0-9A-Fa-f]{2}", s):
                        s=urllib.parse.unquote(s)
                except Exception:
                    pass
        return s

    @staticmethod
    def normalize_user_path(raw: str) -> str:
        r"""Normalize any user-supplied Windows file path.

        Handles file://, %20, quotes, long prefix \\?\, 8.3 via GetLongPathNameW,
        env vars, slash normalization, Vietnamese paths.
        """
        if raw is None:
            return ""
        s=str(raw).strip()
        if not s:
            return ""
        if s.lower().startswith("data:"):
            return s
        s=PathResolver._strip_file_uri(s)
        for _ in range(3):
            ns=s.strip().strip('"').strip("'").strip()
            if ns==s:
                break
            s=ns
        if not s:
            return ""
        try:
            expanded=os.path.expandvars(s)
            if "%" in expanded and sys.platform!="win32":
                def _repl(m):
                    var=m.group(1)
                    return os.environ.get(var, m.group(0))
                expanded=re.sub(r"%([^%]+)%", _repl, expanded)
            s=expanded
        except Exception:
            pass
        for prefix in ("\\\\?\\", "\\\\.\\"):
            if s.startswith(prefix):
                s=s[len(prefix):]
                break
        if s.startswith("//?/"):
            s=s[4:]
        s=s.strip()
        if not s:
            return ""
        if "~" in s and sys.platform=="win32":
            try:
                s_long=PathResolver._to_long_path(s)
                if s_long and s_long!=s:
                    s=s_long
            except Exception:
                pass
        is_unc=s.startswith("\\\\") or s.startswith("//")
        s=s.replace("\\", "/")
        if is_unc:
            s="/"+s.lstrip("/")
            s="/"+s
            rest=re.sub(r"/+", "/", s[2:])
            s="//"+rest.lstrip("/")
        else:
            s=re.sub(r"/+", "/", s)
        m=re.match(r"^([a-zA-Z]):/(.*)", s)
        if m:
            drive=m.group(1).upper()
            rest=m.group(2)
            s=f"{drive}:/{rest}" if rest else f"{drive}:/"
            if len(s)>3 and s.endswith("/"):
                s=s.rstrip("/")
        else:
            if len(s)>1 and s.endswith("/") and not s.startswith("//"):
                s=s.rstrip("/")
            if s.startswith("//") and len(s)>2 and s.endswith("/"):
                s=s.rstrip("/")
        return s.strip()

    @staticmethod
    def _to_long_path(p_str: str) -> str:
        r"""Convert 8.3 short path to long via GetLongPathNameW. Handles \\?\."""
        if not p_str:
            return p_str
        s=str(p_str).strip()
        if not s:
            return s
        if s.startswith("\\\\?\\"):
            s=s[4:]
        if sys.platform!="win32":
            return s
        if "~" not in s:
            return s
        try:
            import ctypes
            from ctypes import wintypes
            GetLongPathNameW=ctypes.windll.kernel32.GetLongPathNameW
            GetLongPathNameW.argtypes=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD]
            GetLongPathNameW.restype=wintypes.DWORD
            buf=ctypes.create_unicode_buffer(32768)
            length=GetLongPathNameW(s,buf,32768)
            if length>0 and length<32768:
                val=buf.value
                if val:
                    if val.startswith("\\\\?\\"):
                        val=val[4:]
                    return val
        except Exception:
            pass
        return p_str

    @staticmethod
    def _is_reparse_point(p_str: str) -> bool:
        r"""Check if path is reparse point / junction. Handles \\?\."""
        if not p_str:
            return False
        s=str(p_str).strip()
        if not s:
            return False
        if s.startswith("\\\\?\\"):
            s=s[4:]
        if sys.platform=="win32":
            try:
                import ctypes
                from ctypes import wintypes
                GetFileAttributesW=ctypes.windll.kernel32.GetFileAttributesW
                GetFileAttributesW.argtypes=[wintypes.LPCWSTR]
                GetFileAttributesW.restype=wintypes.DWORD
                attrs=GetFileAttributesW(s)
                if attrs!=0xFFFFFFFF:
                    return bool(attrs & 0x400)
            except Exception:
                pass
            try:
                st=os.lstat(s)
                return stat.S_ISLNK(st.st_mode)
            except Exception:
                return False
        else:
            try:
                st=os.lstat(s)
                return stat.S_ISLNK(st.st_mode)
            except Exception:
                return False

    @staticmethod
    def _resolve_via_junction(p_str: str) -> Optional[Path]:
        r"""Resolve reparse point to target via GetFinalPathNameByHandleW. Handles \\?\."""
        if not p_str:
            return None
        s=str(p_str).strip()
        if not s:
            return None
        if not PathResolver._is_reparse_point(s):
            try:
                p=Path(s)
                if p.exists():
                    try:
                        return p.resolve()
                    except Exception:
                        return p
            except Exception:
                pass
            return None
        if sys.platform=="win32":
            try:
                import ctypes
                from ctypes import wintypes
                GENERIC_READ=0x80000000
                FILE_SHARE_READ=1
                FILE_SHARE_WRITE=2
                FILE_SHARE_DELETE=4
                OPEN_EXISTING=3
                FILE_FLAG_BACKUP_SEMANTICS=0x02000000
                CreateFileW=ctypes.windll.kernel32.CreateFileW
                CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
                CreateFileW.restype=wintypes.HANDLE
                INVALID_HANDLE_VALUE=ctypes.c_void_p(-1).value
                handle=CreateFileW(s,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,None,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS,None)
                if handle!=INVALID_HANDLE_VALUE and handle is not None:
                    try:
                        GetFinalPathNameByHandleW=ctypes.windll.kernel32.GetFinalPathNameByHandleW
                        GetFinalPathNameByHandleW.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD]
                        GetFinalPathNameByHandleW.restype=wintypes.DWORD
                        buf=ctypes.create_unicode_buffer(32768)
                        length=GetFinalPathNameByHandleW(handle,buf,32768,0)
                        if length>0 and length<32768 and buf.value:
                            target=buf.value
                            if target.startswith("\\\\?\\"):
                                target=target[4:]
                            return Path(target)
                    finally:
                        try:
                            ctypes.windll.kernel32.CloseHandle(handle)
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                return Path(s).resolve()
            except Exception:
                try:
                    target=os.readlink(s)
                    if not os.path.isabs(target):
                        target=str(Path(s).parent/target)
                    return Path(target)
                except Exception:
                    pass
        else:
            try:
                target=os.readlink(s)
                if not os.path.isabs(target):
                    target=str(Path(s).parent/target)
                return Path(target)
            except Exception:
                try:
                    return Path(s).resolve()
                except Exception:
                    pass
        return None

    @staticmethod
    def _candidate_paths(normalized: str, project_dir: Optional[Path] = None) -> List[str]:
        r"""Generate ordered candidate paths to probe.

        Handles OneDrive swap, localized names like Tài liệu, long prefix \\?\ etc.
        """
        # Cache to avoid regenerating same candidate list for repeated file opens
        try:
            cache_key = f"{normalized}|{project_dir}"
            if cache_key in _CANDIDATE_CACHE:
                return list(_CANDIDATE_CACHE[cache_key])
        except Exception:
            cache_key = None
        cands: List[str]=[]
        seen=set()
        def _add(p:str):
            if not p:
                return
            key=p.lower() if sys.platform=="win32" else p
            if key not in seen:
                seen.add(key)
                cands.append(p)
        raw=str(normalized or "").strip()
        if not raw or raw.lower().startswith("data:"):
            return []
        _add(raw)
        try:
            _add(str(Path(raw)))
        except Exception:
            pass
        try:
            long_v=PathResolver._to_long_path(raw)
            if long_v!=raw:
                _add(long_v)
        except Exception:
            pass
        try:
            if os.path.isabs(raw):
                res=PathResolver._resolve_via_junction(raw)
                if res is not None:
                    _add(str(res))
                    _add(str(res).replace("\\","/"))
        except Exception:
            pass
        if sys.platform=="win32":
            try:
                bs=raw.replace("/","\\")
                if bs!=raw:
                    _add(bs)
            except Exception:
                pass
        if project_dir is not None and not os.path.isabs(raw):
            try:
                pd=Path(project_dir)
                _add(str(pd/raw))
                _add(str(pd/raw).replace("\\","/"))
                if raw.startswith("media/") or raw.startswith("media\\"):
                    _add(str(pd/raw))
                else:
                    _add(str(pd/"media"/Path(raw).name))
                    _add(str(pd/"media"/Path(raw).name).replace("\\","/"))
            except Exception:
                pass
        try:
            real_map={}
            for canon,guid in _KNOWN_FOLDER_GUIDS.items():
                try:
                    p=PathResolver._resolve_known_folder(guid)
                    if p is not None and str(p).strip():
                        real_map[canon]=str(p).replace("\\","/")
                except Exception:
                    continue
            try:
                home_str=str(Path.home()).replace("\\","/")
            except Exception:
                home_str=""
            for canon in _FOLDER_ALIASES:
                if canon not in real_map:
                    if home_str:
                        real_map[canon]=f"{home_str.rstrip("/")}/{canon}"
                    else:
                        real_map[canon]=canon
            od_roots=[]
            try:
                for r in PathResolver._get_onedrive_roots():
                    od_roots.append(str(r).replace("\\","/").rstrip("/"))
            except Exception:
                pass
            raw_slash=raw.replace("\\","/")
            raw_lower=raw_slash.lower()
            for canon,aliases in _FOLDER_ALIASES.items():
                found=None
                fidx=-1
                flen=0
                for alias in aliases:
                    pat=re.compile(r"(^|/)"+re.escape(alias)+r"($|/)", re.IGNORECASE)
                    m=pat.search(raw_slash)
                    if m:
                        idx=raw_lower.find(alias.lower())
                        if idx>=0 and (fidx==-1 or idx<fidx):
                            fidx=idx
                            found=alias
                            flen=len(alias)
                if fidx>=0 and found is not None:
                    suffix=raw_slash[fidx+flen:].lstrip("/")
                    real_base=real_map.get(canon,"").rstrip("/")
                    if real_base:
                        if suffix:
                            _add(f"{real_base}/{suffix}")
                        else:
                            _add(real_base)
                        if "onedrive" in real_base.lower():
                            alt_base=re.sub(r"/OneDrive[^/]*","",real_base,flags=re.IGNORECASE)
                            alt_base=re.sub(r"/+","/",alt_base)
                            if alt_base!=real_base:
                                if suffix:
                                    _add(f"{alt_base.rstrip("/")}/{suffix}")
                                else:
                                    _add(alt_base)
                        else:
                            for od in od_roots:
                                cand=f"{od.rstrip("/")}/{found}/{suffix}" if suffix else f"{od.rstrip("/")}/{found}"
                                _add(cand)
                                cand2=f"{od.rstrip("/")}/{canon}/{suffix}" if suffix else f"{od.rstrip("/")}/{canon}"
                                if cand2!=cand:
                                    _add(cand2)
                    try:
                        if home_str:
                            for a2 in aliases:
                                hc=f"{home_str.rstrip("/")}/{a2}/{suffix}" if suffix else f"{home_str.rstrip("/")}/{a2}"
                                _add(hc)
                    except Exception:
                        pass
                    for od in od_roots:
                        for a2 in aliases:
                            if suffix:
                                _add(f"{od.rstrip("/")}/{a2}/{suffix}")
                            else:
                                _add(f"{od.rstrip("/")}/{a2}")
                    for other in aliases:
                        if other.lower()==found.lower():
                            continue
                        prefix=raw_slash[:fidx]
                        rebuilt=f"{prefix.rstrip("/")}/{other}/{suffix}" if suffix else f"{prefix.rstrip("/")}/{other}"
                        rebuilt=re.sub(r"/+","/",rebuilt)
                        _add(rebuilt)
        except Exception:
            pass
        try:
            raw_slash=raw.replace("\\","/")
            if "onedrive" in raw_slash.lower():
                alt=re.sub(r"/OneDrive[^/]*","",raw_slash,1,flags=re.IGNORECASE)
                alt=re.sub(r"/+","/",alt)
                _add(alt)
                _add(alt.replace("/","\\") if sys.platform=="win32" else alt)
                try:
                    home_str=str(Path.home()).replace("\\","/")
                    for od in PathResolver._get_onedrive_roots():
                        od_s=str(od).replace("\\","/").rstrip("/")
                        if raw_slash.lower().startswith(od_s.lower()):
                            suffix2=raw_slash[len(od_s):].lstrip("/")
                            if home_str:
                                cand_home=f"{home_str.rstrip("/")}/{suffix2}" if suffix2 else home_str
                                _add(cand_home)
                except Exception:
                    pass
            else:
                try:
                    home_str=str(Path.home()).replace("\\","/")
                    rl=raw_slash.lower()
                    hl=home_str.lower() if home_str else ""
                    if home_str and rl.startswith(hl):
                        suffix_home=raw_slash[len(home_str):].lstrip("/")
                        for od in PathResolver._get_onedrive_roots():
                            od_s=str(od).replace("\\","/").rstrip("/")
                            cand=f"{od_s.rstrip("/")}/{suffix_home}" if suffix_home else od_s
                            _add(cand)
                    m=re.match(r"^([A-Za-z]:/Users/[^/]+)/(.*)", raw_slash, re.IGNORECASE)
                    if m:
                        pre=m.group(1)
                        rest=m.group(2)
                        _add(f"{pre}/OneDrive/{rest}")
                except Exception:
                    pass
                try:
                    for od in PathResolver._get_onedrive_roots():
                        od_s=str(od).replace("\\","/").rstrip("/")
                        for aliases in _FOLDER_ALIASES.values():
                            for alias in aliases:
                                if f"/{alias}/".lower() in raw_slash.lower() or raw_slash.lower().endswith(f"/{alias.lower()}"):
                                    idx=raw_slash.lower().find(alias.lower())
                                    if idx>=0:
                                        prefix_before=raw_slash[:idx].rstrip("/")
                                        suffix_after=raw_slash[idx+len(alias):].lstrip("/")
                                        cand_tmp=f"{od_s.rstrip("/")}/{alias}/{suffix_after}" if suffix_after else f"{od_s.rstrip("/")}/{alias}"
                                        _add(cand_tmp)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            up=os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
            if up:
                up_slash=up.replace("\\","/").rstrip("/")
                raw_slash2=raw.replace("\\","/")
                if os.path.isabs(raw):
                    m=re.match(r"^[A-Za-z]:/Users/[^/]+/(.*)", raw_slash2, re.IGNORECASE)
                    if m:
                        suffix2=m.group(1)
                        _add(f"{up_slash.rstrip("/")}/{suffix2}")
                    m2=re.match(r"^/home/[^/]+/(.*)", raw_slash2)
                    if m2:
                        suffix2=m2.group(1)
                        _add(f"{up_slash.rstrip("/")}/{suffix2}")
        except Exception:
            pass
        try:
            extra=[]
            for c in list(cands):
                try:
                    if "\\" in c:
                        extra.append(c.replace("\\","/"))
                    if "/" in c:
                        extra.append(c.replace("/","\\") if sys.platform=="win32" else c)
                except Exception:
                    continue
            for e in extra:
                _add(e)
        except Exception:
            pass
        # Cache result
        try:
            if cache_key is not None:
                if len(_CANDIDATE_CACHE) >= _CANDIDATE_CACHE_MAX:
                    # Simple LRU: drop oldest
                    try:
                        _CANDIDATE_CACHE.pop(next(iter(_CANDIDATE_CACHE)))
                    except Exception:
                        pass
                _CANDIDATE_CACHE[cache_key] = list(cands)
        except Exception:
            pass
        return cands

    @staticmethod
    def resolve_user_file(raw_path: str, project_dir: Optional[Path] = None) -> Optional[Path]:
        r"""Resolve user-supplied path to existing file. Probes OneDrive variants, hydration."""
        if raw_path is None:
            return None
        s=str(raw_path).strip()
        if not s or s.lower().startswith("data:"):
            return None
        normalized=PathResolver.normalize_user_path(s)
        if not normalized:
            return None
        # Fast path: if original file exists, return immediately without expensive candidate generation
        try:
            prev=_is_resolving()
            _set_resolving(True)
            try:
                st=os.stat(normalized)
                if not stat.S_ISDIR(st.st_mode):
                    # Also ensure readable (hydration)
                    try:
                        orig=_ORIG_OPEN if _ORIG_OPEN is not None else builtins.open
                        with orig(normalized,"rb") as fh:
                            fh.read(1)
                    except Exception:
                        pass
                    return Path(normalized)
            except FileNotFoundError:
                pass
            except OSError:
                pass
            finally:
                _set_resolving(prev)
        except Exception:
            pass
        cands=PathResolver._candidate_paths(normalized, project_dir=project_dir)
        if normalized not in cands:
            cands.insert(0, normalized)
        for cand in cands:
            try:
                cand_str=str(cand).strip().strip('"').strip("'")
                if not cand_str or cand_str.lower().startswith("data:"):
                    continue
                check=cand_str
                if check.startswith("\\\\?\\"):
                    check=check[4:]
                exists=False
                is_file=False
                try:
                    prev=_is_resolving()
                    _set_resolving(True)
                    try:
                        st=os.stat(check)
                        exists=True
                        is_file=not stat.S_ISDIR(st.st_mode)
                    except FileNotFoundError:
                        exists=False
                    except OSError:
                        try:
                            exists=os.path.exists(check) or os.path.lexists(check)
                            if exists:
                                if _ORIG_ISFILE is not None:
                                    try:
                                        _set_resolving(True)
                                        is_file=_ORIG_ISFILE(check)
                                    finally:
                                        _set_resolving(prev)
                                else:
                                    is_file=os.path.isfile(check)
                        except Exception:
                            exists=False
                    finally:
                        _set_resolving(prev)
                except Exception:
                    exists=False
                if exists and is_file:
                    try:
                        orig=_ORIG_OPEN if _ORIG_OPEN is not None else builtins.open
                        prev2=_is_resolving()
                        _set_resolving(True)
                        try:
                            with orig(check,"rb") as fh:
                                fh.read(1)
                        finally:
                            _set_resolving(prev2)
                    except Exception:
                        pass
                    try:
                        if PathResolver._is_reparse_point(check):
                            resolved=PathResolver._resolve_via_junction(check)
                            if resolved is not None and resolved.exists():
                                try:
                                    with orig(str(resolved),"rb") as fh2:
                                        fh2.read(1)
                                except Exception:
                                    pass
                                return resolved
                    except Exception:
                        pass
                    return Path(check)
                if sys.platform=="win32":
                    alt=check.replace("/","\\")
                    if alt!=check:
                        try:
                            st2=os.stat(alt)
                            if not stat.S_ISDIR(st2.st_mode):
                                return Path(alt)
                        except Exception:
                            pass
            except Exception:
                continue
        return None

    @staticmethod
    def resolve_user_file_any(raw_path: str, project_dir: Optional[Path] = None) -> Optional[Path]:
        r"""Like resolve_user_file but also matches directories. Handles OneDrive."""
        if raw_path is None:
            return None
        s=str(raw_path).strip()
        if not s or s.lower().startswith("data:"):
            return None
        normalized=PathResolver.normalize_user_path(s)
        if not normalized:
            return None
        # Fast path: original path exists -> return immediately
        try:
            prev=_is_resolving()
            _set_resolving(True)
            try:
                os.stat(normalized)
                return Path(normalized)
            except FileNotFoundError:
                pass
            except OSError:
                pass
            finally:
                _set_resolving(prev)
        except Exception:
            pass
        cands=PathResolver._candidate_paths(normalized, project_dir=project_dir)
        if normalized not in cands:
            cands.insert(0, normalized)
        for cand in cands:
            try:
                cand_str=str(cand).strip().strip('"').strip("'")
                if not cand_str or cand_str.lower().startswith("data:"):
                    continue
                check=cand_str
                if check.startswith("\\\\?\\"):
                    check=check[4:]
                exists=False
                try:
                    prev=_is_resolving()
                    _set_resolving(True)
                    try:
                        os.stat(check)
                        exists=True
                    except FileNotFoundError:
                        exists=False
                    except OSError:
                        try:
                            exists=os.path.exists(check) or os.path.lexists(check)
                        except Exception:
                            exists=False
                    finally:
                        _set_resolving(prev)
                except Exception:
                    exists=False
                if exists:
                    return Path(check)
                if sys.platform=="win32":
                    alt=check.replace("/","\\")
                    if alt!=check:
                        try:
                            os.stat(alt)
                            return Path(alt)
                        except Exception:
                            pass
            except Exception:
                continue
        return None

    @staticmethod
    def ensure_readable(raw_path: str, project_dir: Optional[Path] = None) -> Optional[Path]:
        r"""Ensure user path readable via OneDrive hydration. Handles file:// etc."""
        if raw_path is None:
            return None
        s=str(raw_path).strip()
        if not s or s.lower().startswith("data:"):
            return None
        p=PathResolver.resolve_user_file(s, project_dir=project_dir)
        if p is not None:
            try:
                orig=_ORIG_OPEN if _ORIG_OPEN is not None else builtins.open
                prev=_is_resolving()
                _set_resolving(True)
                try:
                    with orig(str(p),"rb") as fh:
                        fh.read(1)
                finally:
                    _set_resolving(prev)
            except Exception:
                pass
            return p
        p_any=PathResolver.resolve_user_file_any(s, project_dir=project_dir)
        if p_any is not None:
            try:
                orig=_ORIG_OPEN if _ORIG_OPEN is not None else builtins.open
                prev=_is_resolving()
                _set_resolving(True)
                try:
                    with orig(str(p_any),"rb") as fh:
                        fh.read(1)
                    return p_any
                except IsADirectoryError:
                    return p_any
                except Exception:
                    try:
                        if p_any.is_dir():
                            return p_any
                    except Exception:
                        pass
                    return p_any if p_any.exists() else None
                finally:
                    _set_resolving(prev)
            except Exception:
                pass
            return p_any
        return None

    @staticmethod
    def open_readable(raw_path: str, mode: str = "rb", project_dir: Optional[Path] = None, **kwargs):
        r"""Open user file with OneDrive hydration and swapping. Handles \\?\."""
        if raw_path is None:
            raise FileNotFoundError("open_readable: raw_path is None")
        s=str(raw_path).strip()
        if not s:
            raise FileNotFoundError("open_readable: empty path")
        if s.lower().startswith("data:"):
            raise FileNotFoundError("open_readable: data URI not file")
        is_read=any(c in mode for c in ("r","+")) or "b" in mode or "t" in mode
        if is_read:
            p=PathResolver.ensure_readable(s, project_dir=project_dir)
            if p is not None:
                target=str(p)
                orig=_ORIG_OPEN if _ORIG_OPEN is not None else builtins.open
                prev=_is_resolving()
                _set_resolving(True)
                try:
                    return orig(target, mode, **kwargs)
                finally:
                    _set_resolving(prev)
            norm=PathResolver.normalize_user_path(s)
            if norm:
                orig=_ORIG_OPEN if _ORIG_OPEN is not None else builtins.open
                prev=_is_resolving()
                _set_resolving(True)
                try:
                    return orig(norm, mode, **kwargs)
                finally:
                    _set_resolving(prev)
            raise FileNotFoundError(f"open_readable: not found {raw_path!r} (normalized {norm!r})")
        else:
            norm=PathResolver.normalize_user_path(s)
            if not norm:
                norm=s
            try:
                Path(norm).parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            orig=_ORIG_OPEN if _ORIG_OPEN is not None else builtins.open
            prev=_is_resolving()
            _set_resolving(True)
            try:
                return orig(norm, mode, **kwargs)
            finally:
                _set_resolving(prev)

def _quick_needs_patch(raw: str) -> bool:
    """Fast check: does this path potentially need OneDrive/Documents handling?
    Returns True only for paths that look like user data (Documents/OneDrive/file:///% etc).
    This avoids heavy registry scans for every Python/Qt internal file open."""
    if not raw:
        return False
    try:
        low = str(raw).lower()
    except Exception:
        return False
    # Strong signals always need handling
    if low.startswith("file:"):
        return True
    if "%20" in low or "%2f" in low or "%3a" in low:
        return True
    if "onedrive" in low:
        return True
    if raw.startswith("\\\\?\\") or raw.startswith("\\\\.\\"):
        return True
    if "~" in raw:
        return True
    # User shell folder aliases (Documents etc) -> need handling
    # Only check for Documents/EduPlay relevant aliases to keep fast path for bundle assets
    for alias in ("documents", "tài liệu", "tai lieu", "my documents",
                  "desktop", "màn hình nền", "man hinh nen",
                  "downloads", "tải xuống", "tai xuong",
                  "pictures", "hình ảnh", "hinh anh",
                  "music", "âm nhạc", "am nhac"):
        if alias in low:
            return True
    # EduPlay projects/settings are always under Documents, so Documents check already covers them.
    # But also check for "eduplay" ONLY if combined with OneDrive/Documents path; standalone bundle
    # path like E:\eduplay\... should NOT trigger heavy logic.
    if "eduplay" in low and ("documents" in low or "onedrive" in low):
        return True
    return False

def _simple_onedrive_alt(raw: str) -> str | None:
    """Return a single OneDrive alternative path (swap OneDrive segment) for fast exists check.
    Avoids full candidate generation for Projects preview files."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        if "\\OneDrive\\" in raw or "/OneDrive/" in raw:
            # Remove OneDrive segment: C:\Users\X\OneDrive\Documents -> C:\Users\X\Documents
            alt = re.sub(r"[/\\]OneDrive[^/\\]*", "", raw, flags=re.IGNORECASE, count=1)
            # Clean double slashes
            if "\\" in raw:
                alt = re.sub(r"\\\\+", "\\\\", alt)
            else:
                alt = re.sub(r"/+", "/", alt)
            if alt and alt != raw:
                return alt
        elif "\\Documents\\" in raw or "/Documents/" in raw or "Tài liệu" in raw:
            # Insert OneDrive before Documents (quick heuristic)
            # Use the first OneDrive root if known, else generic
            try:
                roots = _CACHED_ONEDRIVE_ROOTS or []
                if roots:
                    # Try using first root's prefix
                    first_root = str(roots[0])
                    # Find Documents segment and prepend OneDrive root
                    # Simplified: replace \Documents\ with \OneDrive\Documents\
                    if "\\Documents\\" in raw:
                        return raw.replace("\\Documents\\", "\\OneDrive\\Documents\\", 1)
                    if "/Documents/" in raw:
                        return raw.replace("/Documents/", "/OneDrive/Documents/", 1)
                else:
                    if "\\Documents\\" in raw:
                        return raw.replace("\\Documents\\", "\\OneDrive\\Documents\\", 1)
                    if "/Documents/" in raw:
                        return raw.replace("/Documents/", "/OneDrive/Documents/", 1)
            except Exception:
                pass
    except Exception:
        pass
    return None


def install_global_patches():
    r"""Monkey-patch open/Path.exists etc to be OneDrive-aware. Handles file://, %20, \\?\, hydration."""
    global _ORIG_OPEN,_ORIG_PATH_OPEN,_ORIG_EXISTS,_ORIG_ISFILE,_ORIG_PATH_EXISTS,_ORIG_PATH_ISFILE,_PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return False
    if getattr(install_global_patches,"_installed",False):
        _PATCH_INSTALLED=True
        return False
    import builtins as _builtins
    import pathlib as _pathlib
    import os.path as _osp
    _ORIG_OPEN=_builtins.open
    try:
        _ORIG_PATH_OPEN=_pathlib.Path.open
    except Exception:
        _ORIG_PATH_OPEN=None
    _ORIG_EXISTS=_osp.exists
    _ORIG_ISFILE=_osp.isfile
    try:
        _ORIG_PATH_EXISTS=_pathlib.Path.exists
    except Exception:
        _ORIG_PATH_EXISTS=None
    try:
        _ORIG_PATH_ISFILE=_pathlib.Path.is_file
    except Exception:
        _ORIG_PATH_ISFILE=None
    def _is_read_mode(mode):
        try:
            m=str(mode or "r")
            return "r" in m or "+" in m
        except Exception:
            return False
    @_patch_guard("_ORIG_OPEN")
    def _patched_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if _is_resolving():
            return _ORIG_OPEN(file, mode, buffering, encoding, errors, newline, closefd, opener)
        is_pathlike=isinstance(file,(str,bytes,os.PathLike))
        if isinstance(file, bytes):
            try:
                decoded=file.decode("utf-8",errors="surrogateescape")
                if decoded.lower().startswith("file:") or "%" in decoded or decoded.startswith("\\\\?\\"):
                    norm=PathResolver.normalize_user_path(decoded)
                    if norm and norm!=decoded:
                        resolved=PathResolver.resolve_user_file(norm)
                        if resolved is not None:
                            file=str(resolved).encode("utf-8")
                        else:
                            file=norm.encode("utf-8")
            except Exception:
                pass
            _set_resolving(True)
            try:
                return _ORIG_OPEN(file, mode, buffering, encoding, errors, newline, closefd, opener)
            finally:
                _set_resolving(False)
        if not is_pathlike:
            _set_resolving(True)
            try:
                return _ORIG_OPEN(file, mode, buffering, encoding, errors, newline, closefd, opener)
            finally:
                _set_resolving(False)
        try:
            raw_str=os.fspath(file) if isinstance(file, os.PathLike) else str(file)
            # Fast path: only OneDrive/Documents-like paths need heavy resolution.
            # Previous code set needs=True for EVERY read, causing 30s+ startup.
            needs = _quick_needs_patch(raw_str)
            if needs:
                norm=PathResolver.normalize_user_path(raw_str)
                if _is_read_mode(mode):
                    resolved=PathResolver.resolve_user_file(norm if norm else raw_str)
                    if resolved is not None:
                        _set_resolving(True)
                        try:
                            return _ORIG_OPEN(str(resolved), mode, buffering, encoding, errors, newline, closefd, opener)
                        finally:
                            _set_resolving(False)
                    maybe=PathResolver.ensure_readable(norm if norm else raw_str)
                    if maybe is not None:
                        _set_resolving(True)
                        try:
                            return _ORIG_OPEN(str(maybe), mode, buffering, encoding, errors, newline, closefd, opener)
                        finally:
                            _set_resolving(False)
                    if norm and norm!=raw_str:
                        _set_resolving(True)
                        try:
                            return _ORIG_OPEN(norm, mode, buffering, encoding, errors, newline, closefd, opener)
                        finally:
                            _set_resolving(False)
                else:
                    if norm and norm!=raw_str:
                        try:
                            Path(norm).parent.mkdir(parents=True, exist_ok=True)
                        except Exception:
                            pass
                        _set_resolving(True)
                        try:
                            return _ORIG_OPEN(norm, mode, buffering, encoding, errors, newline, closefd, opener)
                        finally:
                            _set_resolving(False)
        except Exception:
            pass
        _set_resolving(True)
        try:
            return _ORIG_OPEN(file, mode, buffering, encoding, errors, newline, closefd, opener)
        finally:
            _set_resolving(False)
    @_patch_guard("_ORIG_PATH_OPEN")
    def _patched_path_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if _is_resolving():
            return _ORIG_PATH_OPEN(self, mode, buffering, encoding, errors, newline)
        try:
            raw=os.fspath(self)
            if not _quick_needs_patch(raw):
                _set_resolving(True)
                try:
                    return _ORIG_PATH_OPEN(self, mode, buffering, encoding, errors, newline)
                finally:
                    _set_resolving(False)
            norm=PathResolver.normalize_user_path(raw)
            if _is_read_mode(mode):
                resolved=PathResolver.resolve_user_file(norm if norm else raw)
                if resolved is not None:
                    _set_resolving(True)
                    try:
                        return _ORIG_PATH_OPEN(resolved, mode, buffering, encoding, errors, newline)
                    finally:
                        _set_resolving(False)
                maybe=PathResolver.ensure_readable(norm if norm else raw)
                if maybe is not None:
                    _set_resolving(True)
                    try:
                        return _ORIG_PATH_OPEN(maybe, mode, buffering, encoding, errors, newline)
                    finally:
                        _set_resolving(False)
            else:
                if norm and norm!=raw:
                    try:
                        Path(norm).parent.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass
                    _set_resolving(True)
                    try:
                        return _ORIG_PATH_OPEN(Path(norm), mode, buffering, encoding, errors, newline)
                    finally:
                        _set_resolving(False)
        except Exception:
            pass
        _set_resolving(True)
        try:
            return _ORIG_PATH_OPEN(self, mode, buffering, encoding, errors, newline)
        finally:
            _set_resolving(False)
    @_patch_guard("_ORIG_EXISTS")
    def _patched_exists(path):
        if _is_resolving():
            return _ORIG_EXISTS(path)
        try:
            if isinstance(path, bytes):
                try:
                    decoded=path.decode("utf-8",errors="surrogateescape")
                    norm=PathResolver.normalize_user_path(decoded)
                    if norm!=decoded:
                        cand=PathResolver.resolve_user_file_any(norm)
                        if cand is not None:
                            return True
                        _set_resolving(True)
                        try:
                            if _ORIG_EXISTS(norm):
                                return True
                            if _ORIG_EXISTS(norm.encode("utf-8")):
                                return True
                        finally:
                            _set_resolving(False)
                except Exception:
                    pass
            else:
                raw=os.fspath(path) if isinstance(path, os.PathLike) else str(path)
                if raw.lower().startswith("data:"):
                    _set_resolving(True)
                    try:
                        return _ORIG_EXISTS(path)
                    finally:
                        _set_resolving(False)
                _set_resolving(True)
                try:
                    orig_result=_ORIG_EXISTS(path)
                finally:
                    _set_resolving(False)
                if orig_result:
                    return True
                # Fast path: skip heavy OneDrive probing for irrelevant paths
                if not _quick_needs_patch(raw):
                    return False
                norm=PathResolver.normalize_user_path(raw)
                if norm and norm!=raw:
                    _set_resolving(True)
                    try:
                        if _ORIG_EXISTS(norm):
                            return True
                    finally:
                        _set_resolving(False)
                # Fast path for EduPlay Projects preview/missing files: don't probe 30 candidates (0.5s each)
                # Projects are already under resolved Documents path, alternative unlikely.
                try:
                    _low = raw.lower() if isinstance(raw, str) else ""
                    if "eduplay" in _low and "projects" in _low:
                        try:
                            alt = _simple_onedrive_alt(raw)
                            if alt and alt != raw:
                                _set_resolving(True)
                                try:
                                    if _ORIG_EXISTS(alt):
                                        return True
                                finally:
                                    _set_resolving(False)
                        except Exception:
                            pass
                        return False
                except Exception:
                    pass
                resolved_any=PathResolver.resolve_user_file_any(norm if norm else raw)
                if resolved_any is not None:
                    return True
                try:
                    long_v=PathResolver._to_long_path(raw)
                    if long_v!=raw:
                        _set_resolving(True)
                        try:
                            if _ORIG_EXISTS(long_v):
                                return True
                        finally:
                            _set_resolving(False)
                except Exception:
                    pass
        except Exception:
            pass
        _set_resolving(True)
        try:
            return _ORIG_EXISTS(path)
        finally:
            _set_resolving(False)
    @_patch_guard("_ORIG_ISFILE")
    def _patched_isfile(path):
        if _is_resolving():
            return _ORIG_ISFILE(path)
        try:
            if isinstance(path, bytes):
                try:
                    decoded=path.decode("utf-8",errors="surrogateescape")
                    norm=PathResolver.normalize_user_path(decoded)
                    cand=PathResolver.resolve_user_file(norm if norm else decoded)
                    if cand is not None:
                        return True
                    _set_resolving(True)
                    try:
                        if _ORIG_ISFILE(norm):
                            return True
                        if _ORIG_ISFILE(norm.encode("utf-8")):
                            return True
                    finally:
                        _set_resolving(False)
                except Exception:
                    pass
            else:
                raw=os.fspath(path) if isinstance(path, os.PathLike) else str(path)
                if raw.lower().startswith("data:"):
                    _set_resolving(True)
                    try:
                        return _ORIG_ISFILE(path)
                    finally:
                        _set_resolving(False)
                _set_resolving(True)
                try:
                    orig_result=_ORIG_ISFILE(path)
                finally:
                    _set_resolving(False)
                if orig_result:
                    return True
                if not _quick_needs_patch(raw):
                    return False
                norm=PathResolver.normalize_user_path(raw)
                if norm and norm!=raw:
                    _set_resolving(True)
                    try:
                        if _ORIG_ISFILE(norm):
                            return True
                    finally:
                        _set_resolving(False)
                try:
                    _low = raw.lower() if isinstance(raw, str) else ""
                    if "eduplay" in _low and "projects" in _low:
                        try:
                            alt = _simple_onedrive_alt(raw)
                            if alt and alt != raw:
                                _set_resolving(True)
                                try:
                                    if _ORIG_ISFILE(alt):
                                        return True
                                finally:
                                    _set_resolving(False)
                        except Exception:
                            pass
                        return False
                except Exception:
                    pass
                resolved_file=PathResolver.resolve_user_file(norm if norm else raw)
                if resolved_file is not None:
                    return True
                try:
                    long_v=PathResolver._to_long_path(raw)
                    if long_v!=raw:
                        _set_resolving(True)
                        try:
                            if _ORIG_ISFILE(long_v):
                                return True
                        finally:
                            _set_resolving(False)
                except Exception:
                    pass
        except Exception:
            pass
        _set_resolving(True)
        try:
            return _ORIG_ISFILE(path)
        finally:
            _set_resolving(False)
    @_patch_guard("_ORIG_PATH_EXISTS")
    def _patched_path_exists(self):
        if _is_resolving():
            return _ORIG_PATH_EXISTS(self)
        try:
            raw=os.fspath(self)
            _set_resolving(True)
            try:
                orig=_ORIG_PATH_EXISTS(self)
            finally:
                _set_resolving(False)
            if orig:
                return True
            if not _quick_needs_patch(raw):
                return False
            try:
                _low = raw.lower() if isinstance(raw, str) else ""
                if "eduplay" in _low and "projects" in _low:
                    try:
                        alt = _simple_onedrive_alt(raw)
                        if alt and alt != raw:
                            _set_resolving(True)
                            try:
                                if _ORIG_EXISTS(alt) or _ORIG_PATH_EXISTS(Path(alt)):
                                    return True
                            finally:
                                _set_resolving(False)
                    except Exception:
                        pass
                    return False
            except Exception:
                pass
            norm=PathResolver.normalize_user_path(raw)
            resolved_any=PathResolver.resolve_user_file_any(norm if norm else raw)
            if resolved_any is not None:
                return True
            if norm and norm!=raw:
                _set_resolving(True)
                try:
                    if _ORIG_EXISTS(norm):
                        return True
                    if _ORIG_PATH_EXISTS(Path(norm)):
                        return True
                finally:
                    _set_resolving(False)
        except Exception:
            pass
        _set_resolving(True)
        try:
            return _ORIG_PATH_EXISTS(self)
        finally:
            _set_resolving(False)
    @_patch_guard("_ORIG_PATH_ISFILE")
    def _patched_path_is_file(self):
        if _is_resolving():
            return _ORIG_PATH_ISFILE(self)
        try:
            raw=os.fspath(self)
            _set_resolving(True)
            try:
                orig=_ORIG_PATH_ISFILE(self)
            finally:
                _set_resolving(False)
            if orig:
                return True
            if not _quick_needs_patch(raw):
                return False
            try:
                _low = raw.lower() if isinstance(raw, str) else ""
                if "eduplay" in _low and "projects" in _low:
                    try:
                        alt = _simple_onedrive_alt(raw)
                        if alt and alt != raw:
                            _set_resolving(True)
                            try:
                                if _ORIG_ISFILE(alt) or _ORIG_PATH_ISFILE(Path(alt)):
                                    return True
                            finally:
                                _set_resolving(False)
                    except Exception:
                        pass
                    return False
            except Exception:
                pass
            norm=PathResolver.normalize_user_path(raw)
            resolved_file=PathResolver.resolve_user_file(norm if norm else raw)
            if resolved_file is not None:
                return True
            if norm and norm!=raw:
                _set_resolving(True)
                try:
                    if _ORIG_ISFILE(norm):
                        return True
                    if _ORIG_PATH_ISFILE(Path(norm)):
                        return True
                finally:
                    _set_resolving(False)
        except Exception:
            pass
        _set_resolving(True)
        try:
            return _ORIG_PATH_ISFILE(self)
        finally:
            _set_resolving(False)
    _builtins.open=_patched_open
    if _ORIG_PATH_OPEN is not None:
        _pathlib.Path.open=_patched_path_open
    _osp.exists=_patched_exists
    _osp.isfile=_patched_isfile
    if _ORIG_PATH_EXISTS is not None:
        _pathlib.Path.exists=_patched_path_exists
    if _ORIG_PATH_ISFILE is not None:
        _pathlib.Path.is_file=_patched_path_is_file
    _PATCH_INSTALLED=True
    install_global_patches._installed=True
    return True

__all__=["PathResolver","install_global_patches","_RESOLVING"]
