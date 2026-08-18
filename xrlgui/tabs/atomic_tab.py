"""Sweep any per-element atomic quantity across a range of atomic numbers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
import xraylib as xrl
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from .. import core, elements as elem
from ..widgets.inputs import Card, int_spin, spin, subtitle_label
from .base import TabBase


@dataclass(frozen=True)
class Quantity:
    key: str
    label: str
    unit: str
    param: str                       # none | shell | line | ck | auger
    fn: Callable                     # (z, param_value, energy) -> float
    fmt: str = "{:.6g}"
    log_default: bool = False


def _no_param(fn):
    return lambda z, _p, _e: core.safe(fn, z)


def _with_param(fn):
    return lambda z, p, _e: core.safe(fn, z, p)


def _with_param_rate(fn):
    return lambda z, p, _e: core.safe_positive(fn, z, p)


def _cs(fn):
    return lambda z, _p, e: core.safe(fn, z, e)


QUANTITIES: list[Quantity] = [
    Quantity("edge", "Absorption edge energy", "keV", "shell",
             _with_param(xrl.EdgeEnergy), "{:.5f}", True),
    Quantity("line", "Emission line energy", "keV", "line",
             _with_param(xrl.LineEnergy), "{:.5f}", True),
    Quantity("radrate", "Radiative rate", "", "line",
             _with_param_rate(xrl.RadRate), "{:.5f}"),
    Quantity("fluor", "Fluorescence yield ω", "", "shell",
             _with_param_rate(xrl.FluorYield), "{:.5f}"),
    Quantity("auger_yield", "Auger yield", "", "shell",
             _with_param_rate(xrl.AugerYield), "{:.5f}"),
    Quantity("width", "Atomic level width", "keV", "shell",
             _with_param(xrl.AtomicLevelWidth), "{:.6g}", True),
    Quantity("jump", "Edge jump factor", "", "shell",
             _with_param(xrl.JumpFactor), "{:.4f}"),
    Quantity("config", "Electron occupancy", "electrons", "shell",
             _with_param(xrl.ElectronConfig), "{:.0f}"),
    Quantity("ck", "Coster–Kronig probability", "", "ck",
             _with_param_rate(xrl.CosKronTransProb), "{:.5f}"),
    Quantity("auger_rate", "Auger transition rate", "", "auger",
             _with_param_rate(xrl.AugerRate), "{:.6g}"),
    Quantity("weight", "Atomic weight", "g/mol", "none",
             _no_param(xrl.AtomicWeight), "{:.4f}"),
    Quantity("density", "Element density", "g/cm³", "none",
             _no_param(xrl.ElementDensity), "{:.5g}"),
    Quantity("cs_total", "μ/ρ total at energy", "cm²/g", "energy",
             _cs(xrl.CS_Total), "{:.6g}", True),
    Quantity("cs_photo", "μ/ρ photoelectric at energy", "cm²/g", "energy",
             _cs(xrl.CS_Photo), "{:.6g}", True),
    Quantity("cs_rayl", "μ/ρ Rayleigh at energy", "cm²/g", "energy",
             _cs(xrl.CS_Rayl), "{:.6g}", True),
    Quantity("cs_compt", "μ/ρ Compton at energy", "cm²/g", "energy",
             _cs(xrl.CS_Compt), "{:.6g}", True),
    Quantity("cs_energy", "Mass energy-absorption at energy", "cm²/g", "energy",
             _cs(xrl.CS_Energy), "{:.6g}", True),
    Quantity("fi", "Anomalous scattering f′", "e/atom", "energy",
             _cs(xrl.Fi), "{:.5f}"),
    Quantity("fii", "Anomalous scattering f″", "e/atom", "energy",
             _cs(xrl.Fii), "{:.5f}"),
]

QUANTITIES_BY_KEY = {q.key: q for q in QUANTITIES}

#: Default parameter selections per parameter type.
DEFAULTS = {
    "shell": ["K", "L1", "L2", "L3"],
    "line": ["Ka1", "Ka2", "Kb1", "La1", "Lb1"],
    "ck": ["L12", "L13", "L23"],
    "auger": ["K-L2L3"],
}


class AtomicDataTab(TabBase):
    TITLE = "Atomic data"
    DESCRIPTION = ("Tabulate and plot any per-element quantity across a range of "
                   "atomic numbers — edges, yields, level widths, rates.")

    def __init__(self, parent=None):
        super().__init__(parent, control_width=340)

        quantity_card = Card("Quantity")
        self.combo_quantity = QComboBox()
        for q in QUANTITIES:
            self.combo_quantity.addItem(q.label, q.key)
        self.combo_quantity.currentIndexChanged.connect(self._quantity_changed)
        self.spin_energy = spin(0.001, 1_000_000.0, 10.0, decimals=4, step=1.0, suffix=" keV")
        form = quantity_card.add_form()
        form.addRow("Show", self.combo_quantity)
        form.addRow("At energy", self.spin_energy)
        self._energy_row = self.spin_energy
        self._form = form
        self.controls.addWidget(quantity_card)

        param_card = Card("Shells / lines / transitions")
        self.edit_filter = QLineEdit()
        self.edit_filter.setPlaceholderText("Filter…")
        self.edit_filter.setClearButtonEnabled(True)
        self.edit_filter.textChanged.connect(self._filter_params)
        self.list_params = QListWidget()
        self.list_params.setMinimumHeight(190)
        self.list_params.itemChanged.connect(self._param_toggled)
        btn_none = QPushButton("None")
        btn_none.setProperty("role", "ghost")
        btn_none.clicked.connect(lambda: self._set_all(False))
        btn_all = QPushButton("All visible")
        btn_all.setProperty("role", "ghost")
        btn_all.clicked.connect(lambda: self._set_all(True))
        row = QHBoxLayout()
        row.addWidget(btn_none)
        row.addWidget(btn_all)
        param_card.add(self.edit_filter)
        param_card.add(self.list_params)
        param_card.add_layout(row)
        self._param_card = param_card
        self.controls.addWidget(param_card)

        range_card = Card("Atomic number range")
        self.spin_zmin = int_spin(1, elem.ZMAX, 20)
        self.spin_zmax = int_spin(1, elem.ZMAX, 92)
        rform = range_card.add_form()
        rform.addRow("From Z", self.spin_zmin)
        rform.addRow("To Z", self.spin_zmax)
        range_card.add(subtitle_label(
            "Missing values mean the quantity is not tabulated for that element."))
        self.controls.addWidget(range_card)

        self.bind(self.spin_zmin.valueChanged, self.spin_zmax.valueChanged,
                  self.spin_energy.valueChanged)
        self.finish_controls()

        self.plot = self.add_plot(stretch=3)
        self.table = self.add_table(stretch=2)

        self._quantity_changed()

    # -- parameter list --------------------------------------------------

    def _quantity(self) -> Quantity:
        return QUANTITIES_BY_KEY[self.combo_quantity.currentData()]

    def _quantity_changed(self) -> None:
        quantity = self._quantity()
        needs_energy = quantity.param == "energy"
        self.spin_energy.setVisible(needs_energy)
        label = self._form.labelForField(self.spin_energy)
        if label:
            label.setVisible(needs_energy)

        options = self._options_for(quantity.param)
        self._param_card.setVisible(bool(options))

        self.list_params.blockSignals(True)
        self.list_params.clear()
        defaults = set(DEFAULTS.get(quantity.param, []))
        for name, value in options:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name in defaults else Qt.Unchecked)
            self.list_params.addItem(item)
        if options and not any(self.list_params.item(i).checkState() == Qt.Checked
                               for i in range(self.list_params.count())):
            self.list_params.item(0).setCheckState(Qt.Checked)
        self.list_params.blockSignals(False)
        self.edit_filter.clear()
        self.schedule()

    def _options_for(self, param: str) -> list[tuple[str, object]]:
        if param == "shell":
            return [(s.name, s.value) for s in core.SHELLS]
        if param == "line":
            seen, out = set(), []
            for group in ("K lines", "L lines", "M lines", "All lines"):
                for spec in core.LINE_GROUPS[group]:
                    if spec.value in seen:
                        continue
                    seen.add(spec.value)
                    out.append((spec.short or spec.iupac, spec.value))
            return out
        if param == "ck":
            return list(core.CK_TRANSITIONS.items())
        if param == "auger":
            out = []
            for shell in sorted(core.AUGER_GROUPS):
                out.extend(core.AUGER_GROUPS[shell])
            return out
        return []

    def _filter_params(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.list_params.count()):
            item = self.list_params.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _set_all(self, checked: bool) -> None:
        self.list_params.blockSignals(True)
        for i in range(self.list_params.count()):
            item = self.list_params.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.list_params.blockSignals(False)
        self.schedule()

    def _param_toggled(self, _item) -> None:
        self.schedule()

    def _checked_params(self) -> list[tuple[str, object]]:
        out = []
        for i in range(self.list_params.count()):
            item = self.list_params.item(i)
            if item.checkState() == Qt.Checked:
                out.append((item.text(), item.data(Qt.UserRole)))
        return out

    # -- compute ---------------------------------------------------------

    def recompute(self) -> None:
        quantity = self._quantity()
        zmin, zmax = self.spin_zmin.value(), self.spin_zmax.value()
        if zmin > zmax:
            zmin, zmax = zmax, zmin
        zs = list(range(zmin, zmax + 1))
        energy = self.spin_energy.value()

        params = self._checked_params()
        if quantity.param in ("none", "energy"):
            params = [("", None)]
        elif not params:
            self.plot.clear("Select at least one shell / line / transition.")
            self.table.clear()
            return

        columns = [
            core.Column("sym", "Element", numeric=False),
            core.Column("z", "Z", "{:.0f}"),
        ]
        series, data_columns = [], []
        for name, value in params:
            values = np.array([quantity.fn(z, value, energy) for z in zs], dtype=float)
            label = name or quantity.label
            if np.any(np.isfinite(values)):
                series.append(core.Series(label, np.array(zs, dtype=float), values,
                                          kind="line"))
            columns.append(core.Column(f"p{name}", f"{label} [{quantity.unit}]"
                                       if quantity.unit else label, quantity.fmt))
            data_columns.append(values)

        title = quantity.label
        if quantity.param == "energy":
            title += f" at {energy:g} keV"

        if not series:
            self.plot.clear(f"No tabulated values for {title} in Z = {zmin}–{zmax}.")
        else:
            self.plot.show_spec(core.PlotSpec(
                series=series,
                xlabel="Atomic number Z",
                ylabel=f"{quantity.label} [{quantity.unit}]" if quantity.unit else quantity.label,
                title=title,
                xlog=False,
                ylog=quantity.log_default,
            ))

        rows = []
        for i, z in enumerate(zs):
            rows.append((elem.symbol(z), z, *(col[i] for col in data_columns)))
        self.table.set_table(core.Table(
            columns=columns, rows=rows, title=title,
            note=f"Z = {zmin}–{zmax}"))
        filled = sum(int(math.isfinite(v)) for col in data_columns for v in col)
        self.status.emit(f"{len(rows)} elements × {len(params)} column(s) · "
                         f"{filled} tabulated values")
