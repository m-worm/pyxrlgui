"""Characteristic emission lines: energies, rates and fluorescence cross sections."""

from __future__ import annotations

import math

import numpy as np
import xraylib as xrl
from PySide6.QtWidgets import QCheckBox, QComboBox

from .. import core, elements as elem
from ..widgets.inputs import Card, MultiElementPicker, spin, subtitle_label
from .base import TabBase


class LinesTab(TabBase):
    TITLE = "Emission lines"
    DESCRIPTION = ("Characteristic line energies, radiative rates and fluorescence "
                   "cross sections, drawn as a stick spectrum.")

    def __init__(self, parent=None):
        super().__init__(parent, control_width=330)

        picker_card = Card("Elements")
        self.picker = MultiElementPicker([26, 29, 82])
        picker_card.add(self.picker)
        picker_card.add(subtitle_label("Type symbols, names or Z values separated by commas."))
        self.controls.addWidget(picker_card)

        groups = Card("Line families")
        self.group_boxes: dict[str, QCheckBox] = {}
        for name in ("K lines", "L lines", "M lines", "All lines"):
            box = QCheckBox(name)
            box.setChecked(name in ("K lines", "L lines"))
            box.toggled.connect(self.schedule)
            self.group_boxes[name] = box
            groups.add(box)
        self.group_boxes["All lines"].setToolTip(
            "Every line constant xraylib defines — hundreds of rows per element.")
        self.controls.addWidget(groups)

        excite = Card("Excitation")
        self.spin_energy = spin(0.01, 1_000_000.0, 30.0, decimals=4, step=5.0, suffix=" keV")
        self.combo_kind = QComboBox()
        for key, spec in core.FLUOR_KINDS.items():
            self.combo_kind.addItem(spec.label, key)
        self.combo_kind.setCurrentIndex(1)
        self.combo_intensity = QComboBox()
        self.combo_intensity.addItem("Fluorescence cross section [cm²/g]", "cs")
        self.combo_intensity.addItem("Radiative rate (relative)", "rate")
        self.chk_relative = QCheckBox("Normalize tallest stick to 1")
        self.chk_relative.setChecked(False)
        self.spin_threshold = spin(0.0, 100.0, 0.0, decimals=4, step=0.1, suffix=" %")
        self.spin_threshold.setToolTip("Hide lines weaker than this fraction of the strongest line.")

        form = excite.add_form()
        form.addRow("Beam energy", self.spin_energy)
        form.addRow("Stick height", self.combo_intensity)
        form.addRow("Model", self.combo_kind)
        form.addRow("Cut-off", self.spin_threshold)
        excite.add(self.chk_relative)
        excite.add(subtitle_label(
            "Lines whose absorption edge lies above the beam energy are not excited "
            "and are dropped from the spectrum."))
        self.controls.addWidget(excite)

        self.bind(self.picker.changed, self.spin_energy.valueChanged,
                  self.combo_kind.currentIndexChanged,
                  self.combo_intensity.currentIndexChanged,
                  self.chk_relative.toggled, self.spin_threshold.valueChanged)
        self.finish_controls()

        self.plot = self.add_plot(stretch=3, ylog=False)
        self.table = self.add_table(stretch=2)
        self.schedule()

    # -- compute ---------------------------------------------------------

    def _selected_lines(self) -> list[core.LineSpec]:
        chosen: dict[int, core.LineSpec] = {}
        for name, box in self.group_boxes.items():
            if box.isChecked():
                for spec in core.LINE_GROUPS[name]:
                    chosen.setdefault(spec.value, spec)
        return list(chosen.values())

    def recompute(self) -> None:
        zs = self.picker.zs()
        specs = self._selected_lines()
        if not zs:
            self.plot.clear("Choose at least one element.")
            self.table.clear()
            return
        if not specs:
            self.plot.clear("Choose at least one line family.")
            self.table.clear()
            return

        beam = self.spin_energy.value()
        kind = core.FLUOR_KINDS[self.combo_kind.currentData()]
        intensity_mode = self.combo_intensity.currentData()

        rows = []
        per_element: dict[int, list[tuple[core.LineSpec, float, float, float]]] = {}
        for z in zs:
            found = []
            for spec in specs:
                energy = core.safe(xrl.LineEnergy, z, spec.value)
                if not math.isfinite(energy):
                    continue
                rate = core.safe_positive(xrl.RadRate, z, spec.value)
                cs = core.safe(kind.line_fn, z, spec.value, beam)
                if intensity_mode == "cs" and not math.isfinite(cs):
                    # Not excited at this beam energy, or no Kissel data.
                    continue
                found.append((spec, energy, rate, cs))
            found.sort(key=lambda t: -t[1])
            per_element[z] = found

        intensities = {
            z: np.array([(cs if intensity_mode == "cs" else rate) for _s, _e, rate, cs in found],
                        dtype=float)
            for z, found in per_element.items()
        }
        all_values = np.concatenate([v for v in intensities.values() if v.size]) \
            if any(v.size for v in intensities.values()) else np.array([])
        if all_values.size == 0:
            self.plot.clear(f"No selected lines are excited at {beam:g} keV.")
            self.table.clear()
            self.status.emit("No lines to show.")
            return

        peak = np.nanmax(all_values)
        cutoff = (self.spin_threshold.value() / 100.0) * peak
        scale = (1.0 / peak) if (self.chk_relative.isChecked() and peak > 0) else 1.0

        series = []
        for z, found in per_element.items():
            values = intensities[z] * scale
            keep = np.isfinite(values) & (intensities[z] >= cutoff)
            if not keep.any():
                continue
            energies = np.array([e for _s, e, _r, _c in found], dtype=float)
            labels = [s.short for s, _e, _r, _c in found]
            series.append(core.Series(
                elem.label(z), energies[keep], values[keep], kind="stick",
                annotations=[l for l, k in zip(labels, keep) if k]))
            for (spec, energy, rate, cs), shown in zip(found, keep):
                if not shown:
                    continue
                rows.append((elem.symbol(z), z, spec.short, spec.iupac, spec.shell,
                             energy, core.wavelength(energy), rate, cs))

        if not series:
            self.plot.clear("Every line falls below the cut-off.")
            self.table.clear()
            return

        ylabel = ("Fluorescence cross section [cm²/g]" if intensity_mode == "cs"
                  else "Radiative rate (relative to shell)")
        if scale != 1.0:
            ylabel = "Relative intensity"

        self.plot.show_spec(core.PlotSpec(
            series=series,
            xlabel="Emission energy [keV]",
            ylabel=ylabel,
            title=f"Emission lines excited at {beam:g} keV — {kind.label}",
            xlog=False, ylog=False,
        ))

        rows.sort(key=lambda r: (r[1], -r[5]))
        self.table.set_table(core.Table(
            columns=[
                core.Column("sym", "Element", numeric=False),
                core.Column("z", "Z", "{:.0f}"),
                core.Column("line", "Line", numeric=False),
                core.Column("iupac", "IUPAC", numeric=False),
                core.Column("shell", "Hole", numeric=False),
                core.Column("E", "Energy [keV]", "{:.5f}"),
                core.Column("lam", "λ [Å]", "{:.5f}"),
                core.Column("rate", "Rad. rate", "{:.5f}"),
                core.Column("cs", f"σ_fluor @ {beam:g} keV [cm²/g]", "{:.6g}"),
            ],
            rows=rows,
            title="Emission lines",
            note=f"{kind.label}; beam {beam:g} keV",
        ))
        self.status.emit(f"{len(rows)} lines across {len(series)} element(s)")
