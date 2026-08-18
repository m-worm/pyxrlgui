"""Refractive index, critical angle and penetration depth for X-ray optics."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QCheckBox

from .. import core
from ..widgets.inputs import Card, EnergyGridBox, MaterialBox, ResultTiles, fmt, spin
from .base import TabBase


class OpticsTab(TabBase):
    TITLE = "Optical constants"
    DESCRIPTION = ("Complex refractive index n = 1 − δ − iβ, total-external-reflection "
                   "critical angle and attenuation length.")

    def __init__(self, parent=None):
        super().__init__(parent, control_width=330)

        self.material_box = MaterialBox("Material", default_formula="SiO2")
        self.material_box.combo_mode.setCurrentIndex(1)
        self.material_box.spin_density.setValue(2.65)
        self.controls.addWidget(self.material_box)

        curves = Card("Curves")
        self.chk_delta = QCheckBox("δ  (refractive index decrement)")
        self.chk_beta = QCheckBox("β  (absorption index)")
        self.chk_critical = QCheckBox("Critical angle θc [mrad]")
        self.chk_atten = QCheckBox("Attenuation length 1/μ [µm]")
        self.chk_delta.setChecked(True)
        self.chk_beta.setChecked(True)
        for box in (self.chk_delta, self.chk_beta, self.chk_critical, self.chk_atten):
            box.toggled.connect(self.schedule)
            curves.add(box)
        self.controls.addWidget(curves)

        self.energy_box = EnergyGridBox(1.0, 50.0, 600, True)
        self.controls.addWidget(self.energy_box)

        probe = Card("At a single energy")
        self.spin_probe = spin(0.001, 1_000_000.0, 8.0, decimals=4, step=1.0, suffix=" keV")
        probe.add_form().addRow("Energy", self.spin_probe)
        self.tiles = ResultTiles(columns=2)
        probe.add(self.tiles)
        self.controls.addWidget(probe)

        self.bind(self.material_box.changed, self.energy_box.changed,
                  self.spin_probe.valueChanged)
        self.finish_controls()

        self.plot = self.add_plot(stretch=3, xlog=True, ylog=True)
        self.table = self.add_table(stretch=2)
        self.schedule()

    # -- compute ---------------------------------------------------------

    def recompute(self) -> None:
        material = self.material_box.material_or_none()
        if material is None:
            self.plot.clear(self.material_box.error() or "Choose a valid material.")
            self.table.clear()
            self.tiles.set_values([])
            return
        if not material.density:
            self.plot.clear("Set a density — the refractive index scales with it.")
            self.table.clear()
            self.tiles.set_values([])
            self.status.emit("Density required for optical constants.")
            return

        energies = self.energy_box.grid()
        deltas = np.empty_like(energies)
        betas = np.empty_like(energies)
        for i, energy in enumerate(energies):
            deltas[i], betas[i] = material.delta_beta(energy)

        with np.errstate(invalid="ignore", divide="ignore"):
            critical = np.sqrt(np.maximum(2 * deltas, 0.0)) * 1000.0        # mrad
            mu = material.cs_curve("total", energies) * material.density    # 1/cm
            atten_um = np.where(mu > 0, 1.0 / mu * 1e4, np.nan)             # µm
        lam_um = np.array([core.wavelength(e) for e in energies]) * 1e-4
        phase = 2 * math.pi * deltas / lam_um                               # rad per µm

        series, columns, data = [], [core.Column("E", "Energy [keV]", "{:.6g}")], [energies]
        if self.chk_delta.isChecked():
            series.append(core.Series("δ", energies, deltas))
        if self.chk_beta.isChecked():
            series.append(core.Series("β", energies, betas))
        if self.chk_critical.isChecked():
            series.append(core.Series("θc [mrad]", energies, critical))
        if self.chk_atten.isChecked():
            series.append(core.Series("1/μ [µm]", energies, atten_um))

        columns += [
            core.Column("delta", "δ", "{:.6g}"),
            core.Column("beta", "β", "{:.6g}"),
            core.Column("lam", "λ [Å]", "{:.6g}"),
            core.Column("thetac", "θc [mrad]", "{:.6g}"),
            core.Column("atten", "1/μ [µm]", "{:.6g}"),
            core.Column("phase", "Phase shift [rad/µm]", "{:.6g}"),
        ]
        data += [deltas, betas, lam_um * 1e4, critical, atten_um, phase]

        if not series:
            self.plot.clear("Select at least one curve.")
        else:
            self.plot.show_spec(core.PlotSpec(
                series=series,
                xlabel="Photon energy [keV]",
                ylabel="value (see legend)",
                title=f"Optical constants of {material.name} at ρ = {material.density:g} g/cm³",
                xlog=self.energy_box.is_log(),
                ylog=True,
            ))

        rows = [tuple(column[i] for column in data) for i in range(len(energies))]
        self.table.set_table(core.Table(
            columns=columns, rows=rows, title=f"Optical constants — {material.name}",
            note=f"n = 1 − δ − iβ at ρ = {material.density:g} g/cm³"))

        self._refresh_tiles(material)
        self.status.emit(f"{len(energies)} points · {energies[0]:g}–{energies[-1]:g} keV")

    def _refresh_tiles(self, material: core.Material) -> None:
        energy = self.spin_probe.value()
        delta, beta = material.delta_beta(energy)
        lam = core.wavelength(energy)
        items = [
            ("δ", fmt(delta, 6), "1 − Re(n)"),
            ("β", fmt(beta, 6), "−Im(n)"),
            ("Wavelength", fmt(lam, 6), "Å"),
        ]
        if math.isfinite(delta) and delta > 0:
            theta_c = math.sqrt(2 * delta)
            items.append(("Critical angle", f"{theta_c * 1000:.5g}",
                          f"mrad  ({math.degrees(theta_c):.4g}°)"))
        mu = material.cs("total", energy) * material.density
        if mu > 0:
            items.append(("Attenuation length", f"{1.0 / mu * 1e4:.5g}", "µm (1/e)"))
            items.append(("Phase shift", f"{2 * math.pi * delta / (lam * 1e-4):.5g}", "rad per µm"))
        self.tiles.set_values(items)
