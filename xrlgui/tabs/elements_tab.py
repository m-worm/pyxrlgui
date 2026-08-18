"""Periodic-table browser with a detail panel for the selected element."""

from __future__ import annotations

import math

import xraylib as xrl
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .. import core, elements as elem, theme
from ..widgets import PeriodicTable, TablePanel
from ..widgets.inputs import Card, ResultTiles, fmt, subtitle_label, title_label

#: Quantities that can tint the periodic table.
HEATMAPS: dict[str, tuple[str, callable, bool]] = {
    "None (element category)": ("", None, False),
    "K absorption edge [keV]": ("keV", lambda z: core.safe(xrl.EdgeEnergy, z, xrl.K_SHELL), True),
    "Kα1 line energy [keV]": ("keV", lambda z: core.safe(xrl.LineEnergy, z, xrl.KA1_LINE), True),
    "L3 absorption edge [keV]": ("keV", lambda z: core.safe(xrl.EdgeEnergy, z, xrl.L3_SHELL), True),
    "Atomic weight [g/mol]": ("g/mol", lambda z: core.safe(xrl.AtomicWeight, z), True),
    "Density [g/cm³]": ("g/cm³", lambda z: core.safe(xrl.ElementDensity, z), True),
    "K fluorescence yield": ("", lambda z: core.safe(xrl.FluorYield, z, xrl.K_SHELL), False),
    "μ/ρ at 10 keV [cm²/g]": ("cm²/g", lambda z: core.safe(xrl.CS_Total, z, 10.0), True),
}


class ElementsTab(QWidget):
    """Landing page: pick an element, see everything xraylib knows about it."""

    TITLE = "Elements"
    DESCRIPTION = "Browse the periodic table and inspect per-element atomic data."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._palette = theme.DARK
        self._z = 26

        # -- top: periodic table ----------------------------------------
        self.table = PeriodicTable(cell_size=36, mode="single")
        self.table.set_selection([self._z])
        self.table.elementActivated.connect(self.select_element)

        self.combo_heatmap = QComboBox()
        self.combo_heatmap.addItems(list(HEATMAPS))
        self.combo_heatmap.setMinimumWidth(230)
        self.combo_heatmap.currentIndexChanged.connect(self._apply_heatmap)

        heat_row = QHBoxLayout()
        heat_row.setContentsMargins(0, 0, 0, 0)
        heat_row.addWidget(title_label("Elements"))
        heat_row.addSpacing(14)
        heat_row.addWidget(subtitle_label("Color by"))
        heat_row.addWidget(self.combo_heatmap)
        heat_row.addStretch(1)
        self.lbl_scale = subtitle_label("")
        heat_row.addWidget(self.lbl_scale)

        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)
        top_layout.addLayout(heat_row)
        top_layout.addWidget(self.table)

        # -- bottom: detail ---------------------------------------------
        self.lbl_name = QLabel()
        self.lbl_name.setProperty("role", "title")
        self.lbl_meta = subtitle_label("")
        self.tiles = ResultTiles(columns=5)

        summary = Card()
        summary.body().addWidget(self.lbl_name)
        summary.body().addWidget(self.lbl_meta)
        summary.body().addWidget(self.tiles)

        self.tbl_edges = TablePanel(show_filter=False)
        self.tbl_lines = TablePanel(show_filter=False)
        self.tbl_shells = TablePanel(show_filter=False)

        tables = QSplitter(Qt.Horizontal)
        tables.addWidget(self.tbl_edges)
        tables.addWidget(self.tbl_lines)
        tables.addWidget(self.tbl_shells)
        tables.setSizes([320, 420, 420])

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)
        bottom_layout.addWidget(summary)
        bottom_layout.addWidget(tables, 1)

        splitter = QSplitter(Qt.Vertical)
        top_scroll = QScrollArea()
        top_scroll.setWidget(top)
        top_scroll.setWidgetResizable(True)
        top_scroll.setFrameShape(QScrollArea.NoFrame)
        splitter.addWidget(top_scroll)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        # Give the periodic table the height it actually wants; the scroll area
        # takes over when the window is too short for it.
        splitter.setSizes([top.sizeHint().height() + 8, 470])

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.addWidget(splitter)

        self.select_element(self._z)

    # -- interaction -----------------------------------------------------

    def select_element(self, z: int) -> None:
        self._z = z
        self.table.set_selection([z])
        self._refresh_detail()

    def _apply_heatmap(self) -> None:
        key = self.combo_heatmap.currentText()
        unit, fn, log = HEATMAPS[key]
        if fn is None:
            self.table.set_heatmap(None)
            self.table.set_extras(None)
            self.lbl_scale.setText("")
            return
        values = {z: fn(z) for z in self.table.cells}
        clean = {z: v for z, v in values.items() if v is not None and math.isfinite(v)}
        self.table.set_heatmap(clean, log=log)
        self.table.set_extras({z: f"{v:.4g}" for z, v in clean.items()})
        if clean:
            lo, hi = min(clean.values()), max(clean.values())
            scale = "log" if log else "linear"
            self.lbl_scale.setText(f"{lo:.4g} → {hi:.4g} {unit}  ({scale} scale)")

    # -- detail panel ----------------------------------------------------

    def _refresh_detail(self) -> None:
        z = self._z
        element = elem.BY_Z[z]
        weight = core.safe(xrl.AtomicWeight, z)
        density = core.safe(xrl.ElementDensity, z)

        self.lbl_name.setText(f"{element.name}  ·  {element.symbol}")
        self.lbl_meta.setText(
            f"Z = {z} · {elem.CATEGORY_LABELS[element.category]} · "
            f"period {element.period}" +
            (f" · group {element.group}" if element.group else ""))

        k_edge = core.safe(xrl.EdgeEnergy, z, xrl.K_SHELL)
        ka1 = core.safe(xrl.LineEnergy, z, xrl.KA1_LINE)
        la1 = core.safe(xrl.LineEnergy, z, xrl.LA1_LINE)
        yield_k = core.safe(xrl.FluorYield, z, xrl.K_SHELL)
        self.tiles.set_values([
            ("Atomic weight", fmt(weight, 6), "g/mol"),
            ("Density", fmt(density, 5), "g/cm³ (solid, 20 °C)"),
            ("K edge", fmt(k_edge, 6), "keV"),
            ("Kα1", fmt(ka1, 6), "keV"),
            ("Lα1", fmt(la1, 6), "keV"),
            ("ω(K)", fmt(yield_k, 4), "fluorescence yield"),
            ("μ/ρ @ 10 keV", fmt(core.safe(xrl.CS_Total, z, 10.0), 5), "cm²/g"),
            ("μ/ρ @ 30 keV", fmt(core.safe(xrl.CS_Total, z, 30.0), 5), "cm²/g"),
            ("Compton @ 10 keV", fmt(core.safe(xrl.CS_Compt, z, 10.0), 4), "cm²/g"),
            ("Rayleigh @ 10 keV", fmt(core.safe(xrl.CS_Rayl, z, 10.0), 4), "cm²/g"),
        ])

        self._fill_edges(z)
        self._fill_lines(z)
        self._fill_shells(z)

    def _fill_edges(self, z: int) -> None:
        rows = []
        for spec in core.SHELLS:
            energy = core.safe(xrl.EdgeEnergy, z, spec.value)
            if not math.isfinite(energy):
                continue
            rows.append((
                spec.name,
                energy,
                core.wavelength(energy),
                core.safe(xrl.JumpFactor, z, spec.value),
                core.safe(xrl.AtomicLevelWidth, z, spec.value),
            ))
        self.tbl_edges.set_table(core.Table(
            columns=[
                core.Column("shell", "Shell", numeric=False),
                core.Column("E", "Edge [keV]", "{:.5f}"),
                core.Column("lam", "λ [Å]", "{:.4f}"),
                core.Column("jump", "Jump factor", "{:.4f}"),
                core.Column("width", "Level width [keV]", "{:.5g}"),
            ],
            rows=rows,
            title=f"{elem.symbol(z)} absorption edges",
        ))

    def _fill_lines(self, z: int) -> None:
        rows = []
        for group in ("K lines", "L lines", "M lines"):
            for spec in core.LINE_GROUPS[group]:
                energy = core.safe(xrl.LineEnergy, z, spec.value)
                if not math.isfinite(energy):
                    continue
                rows.append((
                    spec.short,
                    spec.iupac,
                    energy,
                    core.wavelength(energy),
                    core.safe_positive(xrl.RadRate, z, spec.value),
                ))
        rows.sort(key=lambda r: -r[2])
        self.tbl_lines.set_table(core.Table(
            columns=[
                core.Column("sieg", "Line", numeric=False),
                core.Column("iupac", "IUPAC", numeric=False),
                core.Column("E", "Energy [keV]", "{:.5f}"),
                core.Column("lam", "λ [Å]", "{:.4f}"),
                core.Column("rate", "Rad. rate", "{:.5f}"),
            ],
            rows=rows,
            title=f"{elem.symbol(z)} emission lines",
            note="radiative rate is relative to its shell",
        ))

    def _fill_shells(self, z: int) -> None:
        rows = []
        for spec in core.MAIN_SHELLS:
            occupancy = core.safe(xrl.ElectronConfig, z, spec.value)
            fluor = core.safe(xrl.FluorYield, z, spec.value)
            auger = core.safe(xrl.AugerYield, z, spec.value)
            if not any(math.isfinite(v) for v in (occupancy, fluor, auger)):
                continue
            rows.append((
                spec.name,
                occupancy,
                fluor,
                auger,
                core.safe(xrl.CS_Photo_Partial, z, spec.value, 20.0),
            ))
        self.tbl_shells.set_table(core.Table(
            columns=[
                core.Column("shell", "Shell", numeric=False),
                core.Column("occ", "Electrons", "{:.0f}"),
                core.Column("fluor", "Fluor. yield ω", "{:.5f}"),
                core.Column("auger", "Auger yield", "{:.5f}"),
                core.Column("photo", "σ_photo @20 keV", "{:.5g}"),
            ],
            rows=rows,
            title=f"{elem.symbol(z)} shells",
            note="partial photoelectric cross section in cm²/g",
        ))

    # -- theming ---------------------------------------------------------

    def set_palette(self, palette: theme.Palette) -> None:
        self._palette = palette
        self.table.set_palette(palette)
        self._apply_heatmap()
