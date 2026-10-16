# -*- coding: utf-8 -*-
"""Create eduplay/resources/icons/icon.ico if it is missing."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _rgba_png(size: int, pixels: bytes) -> bytes:
    raw = b"".join(b"\x00" + pixels[row * size * 4 : (row + 1) * size * 4] for row in range(size))
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)),
            _png_chunk(b"IDAT", zlib.compress(raw, 9)),
            _png_chunk(b"IEND", b""),
        )
    )


def _blend(c0: tuple[int, int, int], c1: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))  # type: ignore[return-value]


def _letter_mask(size: int) -> set[tuple[int, int]]:
    """Block-letter E scaled into the icon."""
    cells = {
        (1, 1), (2, 1), (3, 1), (4, 1), (5, 1),
        (1, 2),
        (1, 3), (2, 3), (3, 3), (4, 3),
        (1, 4),
        (1, 5), (2, 5), (3, 5), (4, 5), (5, 5),
    }
    margin = size // 5
    inner = max(1, size - margin * 2)
    scale = inner / 7.0
    painted: set[tuple[int, int]] = set()
    for gy in range(size):
        for gx in range(size):
            cx = (gx - margin) / scale
            cy = (gy - margin) / scale
            if 0 <= cx < 7 and 0 <= cy < 7 and (int(cx), int(cy)) in cells:
                painted.add((gx, gy))
    return painted


def _draw(size: int) -> bytes:
    radius = size * 22 // 100
    letter = _letter_mask(size)
    out = bytearray()
    for y in range(size):
        for x in range(size):
            dx = min(x, size - 1 - x)
            dy = min(y, size - 1 - y)
            if dx < 0 or dy < 0:
                out.extend(b"\x00\x00\x00\x00")
                continue
            inside = True
            if dx < radius and dy < radius:
                inside = (radius - dx) ** 2 + (radius - dy) ** 2 <= radius * radius
            if not inside:
                out.extend(b"\x00\x00\x00\x00")
                continue
            t = (x + y) / (2 * (size - 1))
            r, g, b = _blend((124, 58, 237), (59, 130, 246), t)
            if (x, y) in letter:
                r, g, b = (11, 18, 32)
            out.extend((r, g, b, 255))
    return bytes(out)


def _ico(images: list[bytes]) -> bytes:
    count = len(images)
    offset = 6 + 16 * count
    entries = bytearray()
    payload = bytearray()
    for png in images:
        size = 32
        if png[0:8] == b"\x89PNG\r\n\x1a\n":
            size = struct.unpack(">I", png[16:20])[0]
        w = 0 if size >= 256 else size
        entries.extend(struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(png), offset))
        payload.extend(png)
        offset += len(png)
    return struct.pack("<HHH", 0, 1, count) + bytes(entries) + bytes(payload)


def ensure_app_icon(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return path
    pngs = [_rgba_png(size, _draw(size)) for size in (16, 32, 48, 256)]
    path.write_bytes(_ico(pngs))
    return path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    icon = root / "eduplay_studio" / "eduplay" / "resources" / "icons" / "icon.ico"
    written = ensure_app_icon(icon)
    print(f"ICON={written} bytes={written.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
