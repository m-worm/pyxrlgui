"""An interactive periodic table used both as a browser and as an element picker."""

from __future__ import annotations

import math

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import elements as elem
from .. import theme


def _mix(hex_color: str, other: str, t: float) -> str:
    """Blend two ``#rrggbb`` colors; ``t=0`` returns the first."""
    def parts(c: str) -> tuple[int, int, int]:
        c = c.lstrip("#")
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

    r1, g1, b1 = parts(hex_color)
    r2, g2, b2 = parts(other)
    return "#{:02x}{:02x}{:02x}".format(
        round(r1 + (r2 - r1) * t), round(g1 + (g2 - g1) * t), round(b1 + (b2 - b1) * t))


class ElementCell(QFrame):
    """One tile in the table."""

    clicked = Signal(int)

    def __init__(self, element: elem.Element, size: int, parent=None):
        super().__init__(parent)
        self.element = element
        self.selected = False
        self._base_color = theme.CATEGORY_COLORS.get(element.category, "#888888")
        self._palette = theme.DARK
        self._enabled_look = True

        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)

        self.lbl_z = QLabel(str(element.Z))
        self.lbl_z.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_symbol = QLabel(element.symbol)
        self.lbl_symbol.setAlignment(Qt.AlignCenter)
        self.lbl_extra = QLabel("")
        self.lbl_extra.setAlignment(Qt.AlignCenter)

        big = max(11, int(size * 0.36))
        small = max(7, int(size * 0.19))
        self.lbl_z.setStyleSheet(f"font-size: {small}px; background: transparent; border: none;")
        self.lbl_symbol.setStyleSheet(
            f"font-size: {big}px; font-weight: 700; background: transparent; border: none;")
        self.lbl_extra.setStyleSheet(f"font-size: {small}px; background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 1, 3, 2)
        layout.setSpacing(0)
        layout.addWidget(self.lbl_z)
        layout.addWidget(self.lbl_symbol, 1)
        layout.addWidget(self.lbl_extra)

        self.setToolTip(f"{element.name} — {elem.CATEGORY_LABELS[element.category]}")
        self.restyle(theme.DARK)

    def set_extra(self, text: str) -> None:
        self.lbl_extra.setText(text)

    def set_selected(self, selected: bool) -> None:
        if self.selected != selected:
            self.selected = selected
            self.restyle(self._palette)

    def set_highlight_color(self, color: str | None) -> None:
        """Override the category color, e.g. to render a heat map."""
        self._base_color = color or theme.CATEGORY_COLORS.get(self.element.category, "#888888")
        self.restyle(self._palette)

    def restyle(self, palette: theme.Palette) -> None:
        self._palette = palette
        dark = palette.name == "dark"
        fill = _mix(self._base_color, palette.surface, 0.72 if dark else 0.62)
        text = _mix(self._base_color, palette.text, 0.35 if dark else 0.55)
        if self.selected:
            border = f"2px solid {palette.accent}"
            fill = _mix(self._base_color, palette.surface, 0.42 if dark else 0.35)
        else:
            border = f"1px solid {_mix(self._base_color, palette.border, 0.55)}"
        self.setStyleSheet(
            f"ElementCell {{ background-color: {fill}; border: {border}; border-radius: 5px; }}"
            f"ElementCell:hover {{ border: 2px solid {palette.accent_hi}; }}")
        self.lbl_symbol.setStyleSheet(
            self.lbl_symbol.styleSheet().split("color:")[0] + f"color: {palette.text};")
        self.lbl_z.setStyleSheet(
            self.lbl_z.styleSheet().split("color:")[0] + f"color: {text};")
        self.lbl_extra.setStyleSheet(
            self.lbl_extra.styleSheet().split("color:")[0] + f"color: {palette.muted};")

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.element.Z)
        super().mousePressEvent(event)


class PeriodicTable(QWidget):
    """Grid of every element xraylib knows about.

    In ``single`` mode clicking an element replaces the selection; in ``multi``
    mode it toggles.  ``elementActivated`` always fires with the clicked Z.
    """

    elementActivated = Signal(int)
    selectionChanged = Signal(list)

    def __init__(self, parent=None, cell_size: int = 44, mode: str = "single",
                 show_legend: bool = True):
        super().__init__(parent)
        self.mode = mode
        self._selection: list[int] = []
        self.cells: dict[int, ElementCell] = {}
        self._palette = theme.DARK

        grid = QGridLayout()
        grid.setSpacing(max(2, cell_size // 14))
        grid.setContentsMargins(0, 0, 0, 0)

        for element in elem.ELEMENTS:
            cell = ElementCell(element, cell_size)
            cell.clicked.connect(self._on_cell_clicked)
            self.cells[element.Z] = cell
            grid.addWidget(cell, element.row - 1, element.column - 1)

        # Placeholder markers pointing at the detached f-block rows.
        for row, text, target_row in ((5, "57–71", 9), (6, "89–103", 10)):
            marker = QLabel(f"*\n{text}")
            marker.setAlignment(Qt.AlignCenter)
            marker.setFixedSize(cell_size, cell_size)
            marker.setStyleSheet(
                f"font-size: {max(7, int(cell_size * 0.17))}px; color: {theme.DARK.muted};"
                " background: transparent; border: none;")
            marker.setObjectName("fblock-marker")
            grid.addWidget(marker, row, 2)

        grid.setRowMinimumHeight(7, max(6, cell_size // 4))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)
        holder = QWidget()
        holder.setLayout(grid)
        holder.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(holder)
        row.addStretch(1)
        outer.addLayout(row)

        self.legend = self._build_legend() if show_legend else None
        if self.legend:
            outer.addWidget(self.legend)

    def _build_legend(self) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addStretch(1)
        self._legend_swatches: list[tuple[QLabel, str]] = []
        for key, label in elem.CATEGORY_LABELS.items():
            color = theme.CATEGORY_COLORS[key]
            swatch = QLabel()
            swatch.setFixedSize(11, 11)
            item = QHBoxLayout()
            item.setSpacing(5)
            item.addWidget(swatch)
            caption = QLabel(label)
            caption.setProperty("role", "subtitle")
            item.addWidget(caption)
            wrapper = QWidget()
            wrapper.setLayout(item)
            layout.addWidget(wrapper)
            self._legend_swatches.append((swatch, color))
        layout.addStretch(1)
        return holder

    # -- selection -------------------------------------------------------

    def _on_cell_clicked(self, z: int) -> None:
        if self.mode == "multi":
            if z in self._selection:
                self._selection.remove(z)
            else:
                self._selection.append(z)
        else:
            self._selection = [z]
        self._sync_cells()
        self.elementActivated.emit(z)
        self.selectionChanged.emit(list(self._selection))

    def selection(self) -> list[int]:
        return list(self._selection)

    def set_selection(self, zs: list[int]) -> None:
        self._selection = [z for z in zs if z in self.cells]
        self._sync_cells()
        self.selectionChanged.emit(list(self._selection))

    def _sync_cells(self) -> None:
        chosen = set(self._selection)
        for z, cell in self.cells.items():
            cell.set_selected(z in chosen)

    # -- decoration ------------------------------------------------------

    def set_extras(self, values: dict[int, str] | None) -> None:
        for z, cell in self.cells.items():
            cell.set_extra("" if values is None else values.get(z, ""))

    def set_heatmap(self, values: dict[int, float] | None, log: bool = True) -> None:
        """Color cells by value; pass ``None`` to restore category colors."""
        if not values:
            for cell in self.cells.values():
                cell.set_highlight_color(None)
            return
        finite = [v for v in values.values() if v is not None and math.isfinite(v) and (v > 0 or not log)]
        if not finite:
            return
        lo, hi = min(finite), max(finite)
        if log:
            lo, hi = math.log10(max(lo, 1e-12)), math.log10(max(hi, 1e-12))
        span = (hi - lo) or 1.0
        ramp = ["#2c3e73", "#2f7fb8", "#33b8a5", "#8ed15a", "#f2c14e", "#ef7d3f", "#e2483d"]
        for z, cell in self.cells.items():
            value = values.get(z)
            if value is None or not math.isfinite(value) or (log and value <= 0):
                cell.set_highlight_color(self._palette.border)
                continue
            t = ((math.log10(value) if log else value) - lo) / span
            t = min(max(t, 0.0), 1.0) * (len(ramp) - 1)
            i = min(int(t), len(ramp) - 2)
            cell.set_highlight_color(_mix(ramp[i], ramp[i + 1], t - i))

    def set_palette(self, palette: theme.Palette) -> None:
        self._palette = palette
        for cell in self.cells.values():
            cell.restyle(palette)
        for marker in self.findChildren(QLabel, "fblock-marker"):
            marker.setStyleSheet(
                marker.styleSheet().split("color:")[0] + f"color: {palette.muted};"
                " background: transparent; border: none;")
        if self.legend:
            for swatch, color in self._legend_swatches:
                swatch.setStyleSheet(
                    f"background: {_mix(color, palette.surface, 0.35)};"
                    f" border: 1px solid {palette.border}; border-radius: 3px;")


class ElementDialog(QDialog):
    """Modal element chooser built on :class:`PeriodicTable`."""

    def __init__(self, parent=None, current: int | None = None,
                 mode: str = "single", selection: list[int] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Choose element" + ("s" if mode == "multi" else ""))
        self.setModal(True)

        self.table = PeriodicTable(cell_size=38, mode=mode, show_legend=True)
        if mode == "multi":
            self.table.set_selection(selection or [])
        elif current:
            self.table.set_selection([current])
            self.table.elementActivated.connect(lambda _z: self.accept())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.addWidget(self.table)
        layout.addWidget(buttons)

        if parent is not None:
            palette = getattr(parent.window(), "active_palette", None)
            if palette:
                self.setStyleSheet(theme.stylesheet(palette))
                self.table.set_palette(palette)

    def chosen(self) -> list[int]:
        return self.table.selection()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(820, 560)
