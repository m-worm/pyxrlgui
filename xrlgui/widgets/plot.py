"""Matplotlib canvas wrapped in a themed panel."""

from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg")

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..core import PlotSpec


class _Toolbar(NavigationToolbar2QT):
    """Navigation toolbar trimmed to the buttons that make sense here."""

    toolitems = [t for t in NavigationToolbar2QT.toolitems
                 if t[0] in ("Home", "Pan", "Zoom", "Subplots")]


class PlotPanel(QFrame):
    """Displays a :class:`~xrlgui.core.PlotSpec` with log/linear toggles."""

    def __init__(self, parent: QWidget | None = None,
                 xlog: bool = False, ylog: bool = False,
                 show_scale_toggles: bool = True):
        super().__init__(parent)
        self.setProperty("role", "card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._spec: PlotSpec | None = None
        self._palette = theme.DARK

        self.figure = Figure(figsize=(6, 4), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.axes = self.figure.add_subplot(111)

        # coordinates=False: the panel shows its own readout in lbl_status.
        self.toolbar = _Toolbar(self.canvas, self, coordinates=False)
        self.toolbar.setIconSize(self.toolbar.iconSize() * 0.8)

        self.chk_xlog = QCheckBox("log x")
        self.chk_ylog = QCheckBox("log y")
        self.chk_xlog.setChecked(xlog)
        self.chk_ylog.setChecked(ylog)
        self.chk_grid = QCheckBox("grid")
        self.chk_grid.setChecked(True)
        for box in (self.chk_xlog, self.chk_ylog, self.chk_grid):
            box.toggled.connect(self._redraw)

        self.btn_save = QPushButton("Save image…")
        self.btn_save.setProperty("role", "ghost")
        self.btn_save.clicked.connect(self.save_image)

        self.lbl_status = QLabel("")
        self.lbl_status.setProperty("role", "subtitle")

        controls = QHBoxLayout()
        controls.setContentsMargins(10, 6, 10, 0)
        controls.setSpacing(10)
        controls.addWidget(self.toolbar)
        controls.addWidget(self.chk_xlog)
        controls.addWidget(self.chk_ylog)
        controls.addWidget(self.chk_grid)
        controls.addStretch(1)
        controls.addWidget(self.lbl_status)
        controls.addWidget(self.btn_save)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 6)
        layout.setSpacing(2)
        layout.addLayout(controls)
        layout.addWidget(self.canvas, 1)

        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.clear("No data yet")

    # -- painting --------------------------------------------------------

    def set_palette(self, palette: theme.Palette) -> None:
        self._palette = palette
        theme.apply_matplotlib_style(palette)
        self.toolbar.setStyleSheet(f"background: transparent; color: {palette.muted};")
        self._redraw()

    def show_spec(self, spec: PlotSpec) -> None:
        self._spec = spec
        self.chk_xlog.blockSignals(True)
        self.chk_ylog.blockSignals(True)
        self.chk_xlog.setChecked(spec.xlog)
        self.chk_ylog.setChecked(spec.ylog)
        self.chk_xlog.blockSignals(False)
        self.chk_ylog.blockSignals(False)
        self._redraw()

    def clear(self, message: str = "") -> None:
        self._spec = None
        self._message = message
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self.axes.set_axis_off()
        if message:
            self.axes.text(0.5, 0.5, message, ha="center", va="center",
                           color=self._palette.muted, fontsize=11,
                           transform=self.axes.transAxes)
        self.canvas.draw_idle()

    def _redraw(self) -> None:
        spec = self._spec
        if spec is None:
            return
        pal = self._palette
        self.figure.clear()
        self.axes = self.figure.add_subplot(111, polar=spec.polar)
        ax = self.axes

        drawn = 0
        for index, series in enumerate(spec.series):
            color = series.color or theme.CURVE_COLORS[index % len(theme.CURVE_COLORS)]
            x, y = np.asarray(series.x, dtype=float), np.asarray(series.y, dtype=float)
            if x.size == 0:
                continue
            if series.kind == "stick":
                # vlines from the axis floor keeps stick spectra readable on a log axis.
                base = np.nanmin(y[y > 0]) * 1e-3 if (self.chk_ylog.isChecked() and np.any(y > 0)) else 0.0
                ax.vlines(x, base, y, color=color, linewidth=1.8, label=series.label)
                ax.plot(x, y, linestyle="none", marker="o", markersize=3.5, color=color)
            elif series.kind == "bar":
                ax.bar(x, y, color=color, label=series.label, width=0.62)
                if series.annotations:
                    ax.set_xticks(x)
                    ax.set_xticklabels(series.annotations)
            elif series.kind == "scatter":
                ax.plot(x, y, linestyle="none", marker="o", markersize=4.5,
                        color=color, label=series.label)
            else:
                ax.plot(x, y, color=color, label=series.label)
            drawn += 1

            # Bars already carry their annotations as tick labels.
            if series.annotations and series.kind != "bar":
                order = np.argsort(-np.nan_to_num(y))[:12]
                for i in order:
                    if i < len(series.annotations) and np.isfinite(y[i]):
                        ax.annotate(series.annotations[i], (x[i], y[i]),
                                    textcoords="offset points", xytext=(0, 6),
                                    ha="center", fontsize=8, color=pal.muted)

        has_bars = any(s.kind == "bar" for s in spec.series)
        self.chk_xlog.setEnabled(not (spec.polar or has_bars))
        if not spec.polar:
            if self.chk_xlog.isChecked() and not has_bars:
                ax.set_xscale("log")
            if self.chk_ylog.isChecked():
                ax.set_yscale("log")
            ax.set_xlabel(spec.xlabel)
            ax.set_ylabel(spec.ylabel)
        else:
            ax.set_theta_zero_location("E")
            ax.set_title(spec.xlabel, pad=14, fontsize=9, color=pal.muted)

        if spec.title:
            ax.set_title(spec.title)
        # Passing line properties alongside False makes matplotlib turn the grid
        # back on, so the styling only goes with the enabling call.
        if self.chk_grid.isChecked():
            ax.grid(True, color=pal.grid, linewidth=0.8)
        else:
            ax.grid(False)
        for spine in ax.spines.values():
            spine.set_color(pal.border_hi)

        if spec.legend and drawn:
            legend = ax.legend(loc="best", frameon=True)
            if legend:
                legend.get_frame().set_facecolor(pal.surface_alt)
                legend.get_frame().set_edgecolor(pal.border)
                for text in legend.get_texts():
                    text.set_color(pal.text)

        self.figure.set_facecolor(pal.surface)
        ax.set_facecolor(pal.surface)
        self.canvas.draw_idle()

    # -- interaction -----------------------------------------------------

    def _on_motion(self, event) -> None:
        if event.inaxes is None or self._spec is None:
            self.lbl_status.setText("")
            return
        if self._spec.polar:
            self.lbl_status.setText(f"θ = {np.degrees(event.xdata):.1f}°   r = {event.ydata:.4g}")
        else:
            self.lbl_status.setText(f"x = {event.xdata:.6g}    y = {event.ydata:.6g}")

    def save_image(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save plot", "plot.png",
            "PNG image (*.png);;SVG image (*.svg);;PDF document (*.pdf)")
        if path:
            self.figure.savefig(path, dpi=200, facecolor=self._palette.surface)
