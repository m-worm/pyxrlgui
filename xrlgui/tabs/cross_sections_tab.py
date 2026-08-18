"""Attenuation and scattering cross sections versus photon energy."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from .. import core
from ..widgets.inputs import Card, EnergyGridBox, MaterialBox, ResultTiles, fmt, spin
from .base import TabBase

#: Cross-section kinds offered, in display order.
KIND_ORDER = ["total", "photo", "rayl", "compt", "energy", "total_kissel", "photo_kissel"]

THICKNESS_UNITS = {"µm": 1e-4, "mm": 0.1, "cm": 1.0}


class CrossSectionsTab(TabBase):
    TITLE = "Cross sections"
    DESCRIPTION = ("Mass attenuation and scattering cross sections versus energy, "
                   "for elements, compounds and NIST materials.")

    def __init__(self, parent=None):
        super().__init__(parent, control_width=330)

        # -- material + comparison list ---------------------------------
        self.material_box = MaterialBox("Target material")
        self.controls.addWidget(self.material_box)

        compare = Card("Compare")
        self.list_targets = QListWidget()
        self.list_targets.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_targets.setMaximumHeight(120)
        btn_add = QPushButton("Add current")
        btn_add.setProperty("role", "primary")
        btn_add.clicked.connect(self._add_target)
        btn_remove = QPushButton("Remove")
        btn_remove.setProperty("role", "ghost")
        btn_remove.clicked.connect(self._remove_targets)
        btn_clear = QPushButton("Clear")
        btn_clear.setProperty("role", "ghost")
        btn_clear.clicked.connect(self._clear_targets)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(btn_add)
        row.addWidget(btn_remove)
        row.addWidget(btn_clear)
        compare.add(self.list_targets)
        compare.add_layout(row)
        compare.add(_hint("The target above is always plotted; added materials "
                          "are overlaid for comparison."))
        self.controls.addWidget(compare)

        # -- quantities --------------------------------------------------
        kinds = Card("Quantities")
        self.kind_boxes: dict[str, QCheckBox] = {}
        for key in KIND_ORDER:
            spec = core.CS_KINDS[key]
            box = QCheckBox(spec.label)
            box.setChecked(key in ("total", "photo", "rayl", "compt"))
            if spec.note:
                box.setToolTip(spec.note)
            box.toggled.connect(self.schedule)
            self.kind_boxes[key] = box
            kinds.add(box)

        self.combo_unit = QComboBox()
        for unit in core.CS_UNITS:
            self.combo_unit.addItem(core.CS_UNIT_LABELS[unit], unit)
        self.combo_unit.currentIndexChanged.connect(self.schedule)
        form = kinds.add_form()
        form.addRow("Units", self.combo_unit)
        self.controls.addWidget(kinds)

        # -- energy grid -------------------------------------------------
        self.energy_box = EnergyGridBox(1.0, 100.0, 800, True)
        self.controls.addWidget(self.energy_box)

        # -- probe / transmission ---------------------------------------
        probe = Card("Probe energy & transmission")
        self.spin_probe = spin(0.001, 1_000_000.0, 10.0, decimals=4, step=1.0, suffix=" keV")
        self.spin_thickness = spin(0.0, 1e6, 100.0, decimals=4, step=10.0)
        self.combo_thickness_unit = QComboBox()
        self.combo_thickness_unit.addItems(list(THICKNESS_UNITS))
        self.chk_marker = QCheckBox("Mark probe energy on the plot")
        self.chk_marker.setChecked(True)
        pform = probe.add_form()
        pform.addRow("Energy", self.spin_probe)
        thickness_row = QHBoxLayout()
        thickness_row.setSpacing(5)
        thickness_row.addWidget(self.spin_thickness, 1)
        thickness_row.addWidget(self.combo_thickness_unit)
        pform.addRow("Thickness", thickness_row)
        probe.add(self.chk_marker)
        self.tiles = ResultTiles(columns=2)
        probe.add(self.tiles)
        self.controls.addWidget(probe)

        self.bind(self.material_box.changed, self.energy_box.changed,
                  self.spin_probe.valueChanged, self.spin_thickness.valueChanged,
                  self.combo_thickness_unit.currentIndexChanged,
                  self.chk_marker.toggled)
        self.finish_controls()

        # -- results -----------------------------------------------------
        self.plot = self.add_plot(stretch=3, xlog=True, ylog=True)
        self.table = self.add_table(stretch=2)
        self.schedule()

    # -- comparison list -------------------------------------------------

    def _add_target(self) -> None:
        material = self.material_box.material_or_none()
        if material is None:
            return
        item = QListWidgetItem(material.describe())
        item.setData(Qt.UserRole, material)
        self.list_targets.addItem(item)
        self.schedule()

    def _remove_targets(self) -> None:
        for item in self.list_targets.selectedItems():
            self.list_targets.takeItem(self.list_targets.row(item))
        self.schedule()

    def _clear_targets(self) -> None:
        self.list_targets.clear()
        self.schedule()

    def _targets(self) -> list[core.Material]:
        targets = []
        current = self.material_box.material_or_none()
        if current is not None:
            targets.append(current)
        for i in range(self.list_targets.count()):
            targets.append(self.list_targets.item(i).data(Qt.UserRole))
        return targets

    # -- compute ---------------------------------------------------------

    def recompute(self) -> None:
        error = self.material_box.error()
        targets = self._targets()
        kinds = [k for k in KIND_ORDER if self.kind_boxes[k].isChecked()]

        if not targets:
            self.plot.clear(error or "Choose a valid material.")
            self.table.clear()
            self.tiles.set_values([])
            return
        if not kinds:
            self.plot.clear("Select at least one quantity.")
            self.table.clear()
            return

        unit = self.combo_unit.currentData()
        energies = self.energy_box.grid()
        single_target = len(targets) == 1
        single_kind = len(kinds) == 1

        series: list[core.Series] = []
        columns = [core.Column("E", "Energy [keV]", "{:.6g}")]
        data = [energies]
        missing_density = []

        for material in targets:
            if unit == "1/cm" and not material.density:
                missing_density.append(material.name)
            for kind in kinds:
                values = material.convert(material.cs_curve(kind, energies), unit)
                if single_target:
                    label = core.CS_KINDS[kind].label
                elif single_kind:
                    label = material.name
                else:
                    label = f"{material.name} · {core.CS_KINDS[kind].label}"
                series.append(core.Series(label, energies, values))
                columns.append(core.Column(f"{material.name}:{kind}", label, "{:.6g}"))
                data.append(values)

        if self.chk_marker.isChecked():
            probe = self.spin_probe.value()
            if energies[0] <= probe <= energies[-1]:
                finite = np.concatenate([np.asarray(s.y)[np.isfinite(s.y)] for s in series]) \
                    if series else np.array([])
                if finite.size:
                    series.append(core.Series(
                        f"probe = {probe:g} keV",
                        np.array([probe, probe]),
                        np.array([np.nanmin(finite), np.nanmax(finite)]),
                        color="#8892a4"))

        note = core.CS_UNIT_LABELS[unit]
        if missing_density:
            note += "  ·  density unset for: " + ", ".join(missing_density)

        self.plot.show_spec(core.PlotSpec(
            series=series,
            xlabel="Photon energy [keV]",
            ylabel=core.CS_UNIT_LABELS[unit],
            title="Attenuation and scattering cross sections",
            xlog=self.energy_box.is_log(),
            ylog=True,
        ))

        rows = [tuple(column[i] for column in data) for i in range(len(energies))]
        self.table.set_table(core.Table(
            columns=columns, rows=rows, title="Cross sections", note=note))

        self._refresh_tiles(targets[0], unit)
        self.status.emit(
            f"{len(series)} curve(s) · {len(energies)} points · "
            f"{energies[0]:g}–{energies[-1]:g} keV")

    def _refresh_tiles(self, material: core.Material, unit: str) -> None:
        probe = self.spin_probe.value()
        mass_cs = material.cs("total", probe)
        rho = material.density
        thickness_cm = self.spin_thickness.value() * THICKNESS_UNITS[
            self.combo_thickness_unit.currentText()]

        items = [
            ("μ/ρ total", fmt(mass_cs, 6), "cm²/g"),
            ("σ per atom", fmt(material.convert(mass_cs, "barn/atom"), 6), "barn"),
        ]
        if rho and math.isfinite(mass_cs):
            mu = mass_cs * rho
            length = 1.0 / mu if mu > 0 else float("nan")
            transmission = math.exp(-mu * thickness_cm) if thickness_cm >= 0 else float("nan")
            items += [
                ("μ linear", fmt(mu, 6), "1/cm"),
                ("Attenuation length 1/μ", _length_str(length), "1/e depth"),
                ("Transmission", f"{transmission * 100:.4g} %",
                 f"through {self.spin_thickness.value():g} {self.combo_thickness_unit.currentText()}"),
                ("Absorbed", f"{(1 - transmission) * 100:.4g} %", "of incident beam"),
            ]
        else:
            items.append(("μ linear", "—", "set a density"))
        self.tiles.set_values(items)


def _length_str(length_cm: float) -> str:
    if not math.isfinite(length_cm):
        return "—"
    if length_cm < 1e-4:
        return f"{length_cm * 1e7:.4g} nm"
    if length_cm < 0.1:
        return f"{length_cm * 1e4:.4g} µm"
    if length_cm < 10:
        return f"{length_cm * 10:.4g} mm"
    return f"{length_cm:.4g} cm"


def _hint(text: str):
    from ..widgets.inputs import subtitle_label
    return subtitle_label(text)
