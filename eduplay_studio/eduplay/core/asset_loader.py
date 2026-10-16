"""
EduPlay Studio — Asset Loader with transparent AES decryption.
"""

import hashlib
import os
import struct
import sys
import tempfile
from pathlib import Path

from eduplay.core.path_resolver import PathResolver

_AESGCM = None


def _aesgcm():
    """Nap `cryptography` LAZY (chi khi that su giai ma asset).

    Module nay duoc import luc khoi dong app; nap AESGCM o cap module mat
    ~85ms ma phan lon so lan app KHONG co asset can giai ma.
    """
    global _AESGCM
    if _AESGCM is None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _A

        _AESGCM = _A
    return _AESGCM

MAGIC = b"EPLA"
KEY_MAGIC = b"EPLK"
EXE_KEY_MARKER = b"EPLX"
VERSION = 2
NONCE_SIZE = 12
SALT_SIZE = 16
EMBEDDED_CODE_KEY = bytes.fromhex(
    "dc4aefd74a8ff1c75c96e7820d3a8d9976196a85c47d3c7656203946b029487f"
)

_KEY_CACHE = None


def derive_asset_key(seed: bytes, salt: bytes) -> bytes:
    """Derive the runtime AES-256 key from a build seed."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        seed,
        salt + b"EduPlayStudioAssetKey",
        240000,
        dklen=32,
    )


def _is_frozen_app() -> bool:
    """True when running from a frozen/compiled bundle (exe).

    Covers PyInstaller/cx_Freeze (sys.frozen / sys._MEIPASS) and Nuitka
    standalone/onefile, which sets neither: Nuitka sets sys.__compiled__
    and the process executable is our own EduPlayStudio.exe, not python.
    """
    try:
        if bool(getattr(sys, "frozen", False)):
            return True
    except Exception:
        pass
    try:
        if bool(getattr(sys, "__compiled__", False)):
            return True
    except Exception:
        pass
    try:
        if getattr(sys, "_MEIPASS", None):
            return True
    except Exception:
        pass
    try:
        base = os.path.basename(str(sys.executable or "")).lower()
        if base and "python" not in base:
            return True
    except Exception:
        pass
    return False


def _get_runtime_root() -> Path:
    if _is_frozen_app():
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            pass
        try:
            return Path(os.path.dirname(os.path.abspath(sys.executable)))
        except Exception:
            pass
    return Path(__file__).parent.parent.parent


def _get_runtime_exe_path() -> Path | None:
    if not _is_frozen_app():
        return None
    try:
        exe = Path(sys.executable)
        if exe.exists() and exe.is_file():
            return exe
    except Exception:
        pass
    return None


def _get_runtime_cache_dir() -> Path:
    cache_dir = PathResolver.resolve_runtime_cache_dir()
    return cache_dir


def _build_binding_digest(exe_path: Path | None) -> bytes:
    """Bind the key file to the exact frozen executable."""
    if exe_path is None or not exe_path.exists():
        return hashlib.sha256(b"eduplay-dev-binding").digest()

    effective_size = exe_path.stat().st_size
    try:
        if effective_size >= 8:
            with open(exe_path, "rb") as handle:
                handle.seek(-8, 2)
                tail = handle.read(8)
                if len(tail) == 8 and tail[:4] == EXE_KEY_MARKER:
                    blob_len = struct.unpack(">I", tail[4:8])[0]
                    footer = 8 + int(blob_len)
                    if 0 < footer < effective_size:
                        effective_size -= footer
    except Exception:
        effective_size = exe_path.stat().st_size

    digest = hashlib.sha256()
    digest.update(exe_path.name.encode("utf-8", errors="ignore"))
    digest.update(str(effective_size).encode("ascii"))
    with open(exe_path, "rb") as handle:
        remaining = int(effective_size)
        while remaining > 0:
            chunk = handle.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.digest()


def _unwrap_seed(blob: bytes, salt: bytes) -> bytes:
    exe_path = _get_runtime_exe_path()
    binding_digest = _build_binding_digest(exe_path)
    wrap_key = hashlib.pbkdf2_hmac(
        "sha256",
        EMBEDDED_CODE_KEY + binding_digest,
        salt + b"EduPlayStudioKeyWrap",
        320000,
        dklen=32,
    )
    if len(blob) < NONCE_SIZE + 16:
        raise ValueError("Wrapped key blob is too short")
    nonce = blob[:NONCE_SIZE]
    ciphertext = blob[NONCE_SIZE:]
    return _aesgcm()(wrap_key).decrypt(nonce, ciphertext, None)


def _read_key_blob_from_exe(exe_path: Path) -> bytes | None:
    try:
        if not exe_path.exists():
            return None
        size = exe_path.stat().st_size
        if size < 8:
            return None
        with open(exe_path, "rb") as handle:
            handle.seek(-8, 2)
            tail = handle.read(8)
            if len(tail) != 8 or tail[:4] != EXE_KEY_MARKER:
                return None
            blob_len = struct.unpack(">I", tail[4:8])[0]
            if blob_len <= 0 or blob_len > size - 8:
                return None
            handle.seek(-(8 + blob_len), 2)
            blob = handle.read(blob_len)
            if len(blob) != blob_len:
                return None
            return blob
    except Exception:
        return None


def load_key() -> bytes:
    """Load the AES key from the bound key file."""
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE

    if not _is_frozen_app():
        _KEY_CACHE = b""
        return _KEY_CACHE

    raw = b""
    exe_path = _get_runtime_exe_path()
    if exe_path is not None:
        raw = _read_key_blob_from_exe(exe_path) or b""
    if not raw:
        key_path = _get_runtime_root().parent / "_key.dat"
        if not key_path.exists():
            _KEY_CACHE = b""
            return _KEY_CACHE
        raw = key_path.read_bytes()
    header_size = 4 + 1 + SALT_SIZE
    if len(raw) <= header_size or raw[:4] != KEY_MAGIC or raw[4] != VERSION:
        raise ValueError("Unsupported key file format")

    salt = raw[5 : 5 + SALT_SIZE]
    wrapped_seed = raw[5 + SALT_SIZE :]
    seed = _unwrap_seed(wrapped_seed, salt)
    _KEY_CACHE = derive_asset_key(seed, salt)
    return _KEY_CACHE


def decrypt_asset(data: bytes) -> bytes:
    """Decrypt asset bytes if they carry the EduPlay header."""
    if len(data) < 4 + 1 + 4 + NONCE_SIZE or data[:4] != MAGIC:
        return data

    version = data[4]
    if version != VERSION:
        raise ValueError(f"Unsupported asset encryption version {version}")

    orig_size = struct.unpack(">I", data[5:9])[0]
    nonce = data[9 : 9 + NONCE_SIZE]
    ciphertext = data[9 + NONCE_SIZE :]
    key = load_key()
    if not key:
        return ciphertext

    decrypted = _aesgcm()(key).decrypt(nonce, ciphertext, None)
    return decrypted[:orig_size]


def load_asset_bytes(rel_path: str) -> bytes:
    """Load an asset file as raw bytes, decrypting if necessary."""
    full_path = _get_runtime_root() / rel_path
    with open(full_path, "rb") as f:
        data = f.read()

    return decrypt_asset(data)


def load_asset_text(rel_path: str, encoding="utf-8") -> str:
    """Load an asset file as text, decrypting if necessary."""
    data = load_asset_bytes(rel_path)
    return data.decode(encoding)


def materialize_asset_file(rel_path: str) -> Path:
    """Materialize an asset to a cache file, decrypting if necessary."""
    data = load_asset_bytes(rel_path)
    rel = Path(rel_path.replace("\\", "/"))
    out_path = _get_runtime_cache_dir() / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not out_path.exists() or out_path.read_bytes() != data:
        out_path.write_bytes(data)
    return out_path


def materialize_asset_tree(rel_dir: str) -> Path:
    """Materialize all files from a runtime asset directory into cache."""
    rel_root = Path(rel_dir.replace("\\", "/"))
    source_root = _get_runtime_root() / rel_root
    out_root = _get_runtime_cache_dir() / rel_root
    if not source_root.exists():
        return out_root
    for path in source_root.rglob("*"):
        rel_child = path.relative_to(_get_runtime_root()).as_posix()
        if path.is_dir():
            (out_root / path.relative_to(source_root)).mkdir(parents=True, exist_ok=True)
            continue
        materialize_asset_file(rel_child)
    return out_root


def get_asset_path(rel_path: str) -> Path:
    """Get the absolute path to an asset."""
    return _get_runtime_root() / rel_path
