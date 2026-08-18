#!/usr/bin/env python3
"""Render the application mark into the icon formats each platform needs.

Produces ``icon.png`` (Linux), ``icon.ico`` (Windows) and ``icon.icns`` (macOS)
next to this script. The ICO and ICNS containers are written by hand from PNG
payloads so the only dependency is PySide6, which the project already needs.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QBuffer, QByteArray  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xrlgui.branding import render_pixmap  # noqa: E402

#: Sizes embedded in the Windows .ico.
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

#: macOS .icns chunk types, keyed by pixel size. All take PNG payloads.
ICNS_TYPES = {
    32: b"ic11",
    64: b"ic12",
    128: b"ic07",
    256: b"ic08",
    512: b"ic09",
    1024: b"ic10",
}


def png_bytes(size: int, backdrop: bool) -> bytes:
    """Render the mark at ``size`` and return it as PNG data."""
    # The QByteArray must outlive the QBuffer that wraps it; passing a
    # temporary leaves the buffer pointing at freed memory and segfaults.
    storage = QByteArray()
    buffer = QBuffer(storage)
    buffer.open(QBuffer.WriteOnly)
    render_pixmap(size, backdrop=backdrop).save(buffer, "PNG")
    buffer.close()
    return bytes(storage)


def write_ico(path: Path, backdrop: bool) -> None:
    images = [(size, png_bytes(size, backdrop)) for size in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))     # reserved, type=icon, count
    offset = len(header) + 16 * len(images)

    entries, payloads = b"", b""
    for size, data in images:
        entries += struct.pack(
            "<BBBBHHII",
            0 if size >= 256 else size,   # 0 means 256
            0 if size >= 256 else size,
            0,                            # palette size
            0,                            # reserved
            1,                            # color planes
            32,                           # bits per pixel
            len(data),
            offset,
        )
        payloads += data
        offset += len(data)
    path.write_bytes(header + entries + payloads)


def write_icns(path: Path, backdrop: bool) -> None:
    chunks = b""
    for size, code in sorted(ICNS_TYPES.items()):
        data = png_bytes(size, backdrop)
        chunks += code + struct.pack(">I", len(data) + 8) + data
    path.write_bytes(b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)


def main() -> int:
    # A backdrop keeps the mark visible on light desktops and in taskbars.
    backdrop = True
    # QPixmap rendering needs a live QApplication; it must outlive every save.
    app = QApplication.instance() or QApplication(sys.argv)

    png = HERE / "icon.png"
    render_pixmap(1024, backdrop=backdrop).save(str(png), "PNG")
    write_ico(HERE / "icon.ico", backdrop)
    write_icns(HERE / "icon.icns", backdrop)

    for name in ("icon.png", "icon.ico", "icon.icns"):
        target = HERE / name
        print(f"  {name:12s} {target.stat().st_size:>8,} bytes")

    app.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
