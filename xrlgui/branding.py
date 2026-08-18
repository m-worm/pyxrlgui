"""The application mark, shared by the running window and the packaged icons.

Kept free of any dependency on the rest of the package so the build scripts can
import it without pulling in xraylib.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

APP_NAME = "X-ray Explorer"

#: Ring colors, outermost first. Matches the plot color cycle.
RING_COLORS = ["#4c9aff", "#2dd4bf", "#ff7a59"]
BACKDROP = "#13151a"


def draw_mark(painter: QPainter, size: int, backdrop: bool = False) -> None:
    """Paint the mark into a ``size``x``size`` square starting at (0, 0)."""
    painter.setRenderHint(QPainter.Antialiasing, True)
    unit = size / 64.0

    if backdrop:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(BACKDROP))
        radius = 12 * unit
        painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    painter.setBrush(Qt.NoBrush)
    pen = QPen()
    pen.setCapStyle(Qt.RoundCap)
    center = size / 2.0
    for index, radius_units in enumerate((27, 18.5, 10)):
        pen.setColor(QColor(RING_COLORS[index % len(RING_COLORS)]))
        pen.setWidthF(max(1.0, 3.6 * unit))
        painter.setPen(pen)
        r = radius_units * unit
        painter.drawEllipse(QRectF(center - r, center - r, r * 2, r * 2))

    # Nucleus.
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(RING_COLORS[0]))
    r = 3.4 * unit
    painter.drawEllipse(QRectF(center - r, center - r, r * 2, r * 2))


def render_pixmap(size: int, backdrop: bool = False) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    draw_mark(painter, size, backdrop=backdrop)
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    """Multi-resolution icon for the running application."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(render_pixmap(size))
    return icon
