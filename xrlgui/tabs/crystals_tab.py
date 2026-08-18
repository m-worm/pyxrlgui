"""Crystal diffraction: d-spacings, Bragg angles and structure factors."""

from __future__ import annotations

import math

import numpy as np
import xraylib as xrl
from PySide6.QtWidgets import QComboBox, QHBoxLayout

from .. import core, elements
from ..widgets.inputs import Card, EnergyGridBox, ResultTiles, fmt, int_spin, spin, subtitle_label
from .base import TabBase

MODES = [
    ("bragg_vs_energy", "Bragg angle vs photon energy"),
    ("reflections", "Reflection table for this crystal"),
    ("structure_factor", "Structure factor vs energy"),
    ("unit_cell", "Unit cell atom positions"),
]

#: Reflections enumerated for the reflection table.
MAX_INDEX = 6


class CrystalsTab(TabBase):
    TITLE = "Crystals"
    DESCRIPTION = ("Unit cells, d-spacings, Bragg angles and complex structure "
                   "factors for xraylib's crystal database.")

    def __init__(self, parent=None):
        super().__init__(parent, control_width=340)

        crystal_card = Card("Crystal")
        self.combo_crystal = QComboBox()
        self.combo_crystal.addItems(core.crystals())
        index = self.combo_crystal.findText("Si")
        if index >= 0:
            self.combo_crystal.setCurrentIndex(index)
        self.combo_crystal.currentIndexChanged.connect(self._crystal_changed)
        crystal_card.add(self.combo_crystal)
        self.lbl_cell = subtitle_label("")
        crystal_card.add(self.lbl_cell)
        self.controls.addWidget(crystal_card)

        mode_card = Card("What to show")
        self.combo_mode = QComboBox()
        for key, label in MODES:
            self.combo_mode.addItem(label, key)
        self.combo_mode.currentIndexChanged.connect(self._mode_changed)
        mode_card.add(self.combo_mode)
        self.controls.addWidget(mode_card)

        hkl_card = Card("Miller indices")
        self.spin_h = int_spin(-12, 12, 1)
        self.spin_k = int_spin(-12, 12, 1)
        self.spin_l = int_spin(-12, 12, 1)
        row = QHBoxLayout()
        row.setSpacing(5)
        for box in (self.spin_h, self.spin_k, self.spin_l):
            box.setMinimumWidth(60)
            row.addWidget(box)
        hkl_card.add_layout(row)
        self.spin_debye = spin(0.0, 10.0, 1.0, decimals=4, step=0.05)
        self.spin_debye.setToolTip("Debye–Waller factor applied to the structure factor.")
        self.spin_rel_angle = spin(0.0, 90.0, 0.0, decimals=4, step=1.0, suffix=" °")
        self.spin_rel_angle.setToolTip("Relative angle to the Bragg condition, in degrees.")
        form = hkl_card.add_form()
        form.addRow("Debye–Waller", self.spin_debye)
        form.addRow("Rel. angle", self.spin_rel_angle)
        self.tiles = ResultTiles(columns=2)
        hkl_card.add(self.tiles)
        self._hkl_card = hkl_card
        self.controls.addWidget(hkl_card)

        self.energy_box = EnergyGridBox(2.0, 60.0, 500, False, title="Energy range")
        self.controls.addWidget(self.energy_box)

        limit_card = Card("Reflection table")
        self.spin_max_index = int_spin(1, MAX_INDEX, 3)
        self.spin_ref_energy = spin(0.01, 1_000_000.0, 8.048, decimals=4, step=1.0, suffix=" keV")
        self.spin_ref_energy.setToolTip("Energy used for the Bragg angle column (Cu Kα1 by default).")
        lform = limit_card.add_form()
        lform.addRow("Max |h|,|k|,|l|", self.spin_max_index)
        lform.addRow("At energy", self.spin_ref_energy)
        limit_card.add(subtitle_label(
            "Reflections are sorted by decreasing d-spacing. Structure factors "
            "near zero indicate forbidden reflections."))
        self._limit_card = limit_card
        self.controls.addWidget(limit_card)

        self.bind(self.spin_h.valueChanged, self.spin_k.valueChanged,
                  self.spin_l.valueChanged, self.spin_debye.valueChanged,
                  self.spin_rel_angle.valueChanged, self.energy_box.changed,
                  self.spin_max_index.valueChanged, self.spin_ref_energy.valueChanged)
        self.finish_controls()

        self.plot = self.add_plot(stretch=3)
        self.table = self.add_table(stretch=2)

        self._crystal_changed()

    # -- crystal ---------------------------------------------------------

    def _crystal(self) -> dict:
        return xrl.Crystal_GetCrystal(self.combo_crystal.currentText())

    def _crystal_changed(self) -> None:
        crystal = self._crystal()
        self.lbl_cell.setText(
            f"a = {crystal['a']:.5f} Å, b = {crystal['b']:.5f} Å, c = {crystal['c']:.5f} Å · "
            f"α = {crystal['alpha']:g}°, β = {crystal['beta']:g}°, γ = {crystal['gamma']:g}° · "
            f"V = {crystal['volume']:.4f} Å³ · {crystal['n_atom']} atoms/cell")
        self.schedule()

    def _mode_changed(self) -> None:
        mode = self.combo_mode.currentData()
        self._limit_card.setVisible(mode in ("reflections", "unit_cell"))
        self._hkl_card.setVisible(mode != "unit_cell")
        self.energy_box.setVisible(mode in ("bragg_vs_energy", "structure_factor"))
        self.schedule()

    # -- compute ---------------------------------------------------------

    def recompute(self) -> None:
        crystal = self._crystal()
        self._refresh_tiles(crystal)
        {
            "bragg_vs_energy": self._bragg_vs_energy,
            "reflections": self._reflections,
            "structure_factor": self._structure_factor,
            "unit_cell": self._unit_cell,
        }[self.combo_mode.currentData()](crystal)

    def _hkl(self) -> tuple[int, int, int]:
        return self.spin_h.value(), self.spin_k.value(), self.spin_l.value()

    def _refresh_tiles(self, crystal: dict) -> None:
        h, k, l = self._hkl()
        d = core.safe(xrl.Crystal_dSpacing, crystal, h, k, l)
        energy = self.spin_ref_energy.value()
        items = [
            (f"d({h}{k}{l})", fmt(d, 6), "Å"),
            ("Unit cell volume", fmt(crystal["volume"], 6), "Å³"),
        ]
        if math.isfinite(d) and d > 0:
            # The lowest energy that satisfies Bragg at theta = 90 degrees.
            e_min = core.KEV2ANGST / (2 * d)
            items.append(("Lowest Bragg energy", fmt(e_min, 5), "keV (θ = 90°)"))
            angle = core.safe(xrl.Bragg_angle, crystal, energy, h, k, l)
            items.append((f"θB at {energy:g} keV",
                          f"{math.degrees(angle):.5g}" if math.isfinite(angle) else "—", "°"))
        self.tiles.set_values(items)

    def _bragg_vs_energy(self, crystal: dict) -> None:
        h, k, l = self._hkl()
        energies = self.energy_box.grid()
        angles = np.degrees(core.sweep(
            lambda e: xrl.Bragg_angle(crystal, e, h, k, l), energies))
        d = core.safe(xrl.Crystal_dSpacing, crystal, h, k, l)

        if not np.any(np.isfinite(angles)):
            self.plot.clear(f"({h} {k} {l}) has no Bragg solution in this energy range.")
            self.table.clear()
            return

        self.plot.show_spec(core.PlotSpec(
            series=[core.Series(f"({h} {k} {l})  d = {d:.5f} Å", energies, angles)],
            xlabel="Photon energy [keV]",
            ylabel="Bragg angle θB [deg]",
            title=f"{crystal['name']} ({h} {k} {l}) Bragg angle",
            xlog=self.energy_box.is_log(),
        ))
        rows = [(energies[i], angles[i], 2 * angles[i],
                 core.wavelength(energies[i])) for i in range(len(energies))]
        self.table.set_table(core.Table(
            columns=[
                core.Column("E", "Energy [keV]", "{:.6g}"),
                core.Column("theta", "θB [deg]", "{:.6g}"),
                core.Column("twotheta", "2θ [deg]", "{:.6g}"),
                core.Column("lam", "λ [Å]", "{:.6g}"),
            ],
            rows=rows,
            title=f"{crystal['name']} ({h}{k}{l}) Bragg angles",
            note=f"d = {d:.6f} Å",
        ))
        self.status.emit(f"{crystal['name']} ({h} {k} {l}), d = {d:.6f} Å")

    def _reflections(self, crystal: dict) -> None:
        limit = self.spin_max_index.value()
        energy = self.spin_ref_energy.value()
        debye = self.spin_debye.value()
        rel_angle = self.spin_rel_angle.value()

        rows = []
        for h in range(0, limit + 1):
            for k in range(0, limit + 1):
                for l in range(0, limit + 1):
                    if h == k == l == 0:
                        continue
                    d = core.safe(xrl.Crystal_dSpacing, crystal, h, k, l)
                    if not math.isfinite(d) or d <= 0:
                        continue
                    angle = core.safe(xrl.Bragg_angle, crystal, energy, h, k, l)
                    factor = _f_h(crystal, energy, h, k, l, debye, rel_angle)
                    rows.append((
                        f"{h} {k} {l}", h, k, l, d,
                        math.degrees(angle) if math.isfinite(angle) else float("nan"),
                        abs(factor) if factor is not None else float("nan"),
                        factor.real if factor is not None else float("nan"),
                        factor.imag if factor is not None else float("nan"),
                        core.KEV2ANGST / (2 * d),
                    ))
        rows.sort(key=lambda r: -r[4])

        self.table.set_table(core.Table(
            columns=[
                core.Column("hkl", "hkl", numeric=False),
                core.Column("h", "h", "{:.0f}"),
                core.Column("k", "k", "{:.0f}"),
                core.Column("l", "l", "{:.0f}"),
                core.Column("d", "d [Å]", "{:.6f}"),
                core.Column("theta", f"θB at {energy:g} keV [deg]", "{:.5g}"),
                core.Column("absF", "|F_H|", "{:.5g}"),
                core.Column("reF", "Re F_H", "{:.5g}"),
                core.Column("imF", "Im F_H", "{:.5g}"),
                core.Column("emin", "Min. energy [keV]", "{:.5g}"),
            ],
            rows=rows,
            title=f"{crystal['name']} reflections",
            note=f"|h|,|k|,|l| ≤ {limit}; Debye–Waller {debye:g}",
        ))

        # A stick pattern against 2-theta reads far better than a categorical
        # bar chart, and is the form a diffractionist expects.
        peaks = [r for r in rows
                 if math.isfinite(r[5]) and math.isfinite(r[6]) and r[6] > 1e-6]
        # Symmetry-equivalent reflections land on the same angle; keep one stick
        # each so the hkl labels stay legible.
        merged: dict[float, tuple] = {}
        for row in peaks:
            key = round(row[4], 6)          # identical d-spacing
            if key not in merged or row[6] > merged[key][6]:
                merged[key] = row
        peaks = sorted(merged.values(), key=lambda r: r[5])
        if peaks:
            two_theta = np.array([2 * r[5] for r in peaks])
            intensity = np.array([r[6] ** 2 for r in peaks])
            self.plot.show_spec(core.PlotSpec(
                series=[core.Series("|F_H|²", two_theta, intensity, kind="stick",
                                    annotations=[r[0].replace(" ", "") for r in peaks])],
                xlabel="Scattering angle 2θ [deg]",
                ylabel="|F_H|²  [electrons²]",
                title=(f"{crystal['name']} allowed reflections at {energy:g} keV "
                       f"({len(peaks)} distinct of {len(rows)} indexed)"),
                legend=False,
            ))
        else:
            self.plot.clear(
                f"No reflection satisfies the Bragg condition at {energy:g} keV.")
        self.status.emit(f"{len(rows)} reflections for {crystal['name']}, "
                         f"{len(peaks)} distinct peaks at {energy:g} keV")

    def _unit_cell(self, crystal: dict) -> None:
        energy = self.spin_ref_energy.value()
        rows = []
        for index, atom in enumerate(crystal["atom"]):
            z = atom["Zatom"]
            rows.append((
                index + 1,
                elements.symbol(z),
                z,
                atom["fraction"],
                atom["x"], atom["y"], atom["z"],
                core.safe(xrl.AtomicWeight, z),
                core.safe_positive(xrl.Fi, z, energy),
                core.safe_positive(xrl.Fii, z, energy),
            ))
        self.table.set_table(core.Table(
            columns=[
                core.Column("i", "#", "{:.0f}"),
                core.Column("sym", "Element", numeric=False),
                core.Column("z", "Z", "{:.0f}"),
                core.Column("frac", "Occupancy", "{:.4g}"),
                core.Column("x", "x", "{:.5f}"),
                core.Column("y", "y", "{:.5f}"),
                core.Column("z_", "z", "{:.5f}"),
                core.Column("aw", "Atomic weight", "{:.4f}"),
                core.Column("fi", f"f′ @ {energy:g} keV", "{:.5f}"),
                core.Column("fii", f"f″ @ {energy:g} keV", "{:.5f}"),
            ],
            rows=rows,
            title=f"{crystal['name']} unit cell",
            note=f"{crystal['n_atom']} atoms, V = {crystal['volume']:.4f} Å³",
        ))

        # Project the fractional coordinates onto the a-b plane.
        series = []
        for z in sorted({atom["Zatom"] for atom in crystal["atom"]}):
            xs = np.array([a["x"] for a in crystal["atom"] if a["Zatom"] == z])
            ys = np.array([a["y"] for a in crystal["atom"] if a["Zatom"] == z])
            series.append(core.Series(elements.symbol(z), xs, ys, kind="scatter"))
        self.plot.show_spec(core.PlotSpec(
            series=series,
            xlabel="fractional a",
            ylabel="fractional b",
            title=f"{crystal['name']} unit cell projected along c",
            xlog=False, ylog=False,
        ))
        self.status.emit(f"{crystal['name']}: {len(rows)} atoms in the unit cell")

    def _structure_factor(self, crystal: dict) -> None:
        h, k, l = self._hkl()
        energies = self.energy_box.grid()
        debye = self.spin_debye.value()
        rel_angle = self.spin_rel_angle.value()

        real = np.full(len(energies), np.nan)
        imag = np.full(len(energies), np.nan)
        for i, energy in enumerate(energies):
            factor = _f_h(crystal, energy, h, k, l, debye, rel_angle)
            if factor is not None:
                real[i], imag[i] = factor.real, factor.imag
        magnitude = np.hypot(real, imag)

        if not np.any(np.isfinite(magnitude)):
            self.plot.clear(f"No structure factor available for ({h} {k} {l}).")
            self.table.clear()
            return

        self.plot.show_spec(core.PlotSpec(
            series=[
                core.Series("|F_H|", energies, magnitude),
                core.Series("Re F_H", energies, real),
                core.Series("Im F_H", energies, imag),
            ],
            xlabel="Photon energy [keV]",
            ylabel="Structure factor [electrons]",
            title=f"{crystal['name']} ({h} {k} {l}) structure factor",
            xlog=self.energy_box.is_log(),
        ))
        rows = [(energies[i], magnitude[i], real[i], imag[i]) for i in range(len(energies))]
        self.table.set_table(core.Table(
            columns=[
                core.Column("E", "Energy [keV]", "{:.6g}"),
                core.Column("absF", "|F_H|", "{:.6g}"),
                core.Column("reF", "Re F_H", "{:.6g}"),
                core.Column("imF", "Im F_H", "{:.6g}"),
            ],
            rows=rows,
            title=f"{crystal['name']} ({h}{k}{l}) structure factor",
            note=f"Debye–Waller {debye:g}, relative angle {rel_angle:g}°",
        ))
        self.status.emit(f"{crystal['name']} ({h} {k} {l}) structure factor over "
                         f"{len(energies)} energies")


def _f_h(crystal: dict, energy: float, h: int, k: int, l: int,
         debye: float, rel_angle: float) -> complex | None:
    try:
        return xrl.Crystal_F_H_StructureFactor(crystal, energy, h, k, l, debye, rel_angle)
    except Exception:
        return None
