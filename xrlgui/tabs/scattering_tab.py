"""Elastic and inelastic scattering: form factors, differential cross sections, profiles."""

from __future__ import annotations

import math

import numpy as np
import xraylib as xrl
from PySide6.QtWidgets import QCheckBox, QComboBox

from .. import core, elements as elem
from ..widgets.inputs import Card, MultiElementPicker, int_spin, spin, subtitle_label
from .base import TabBase

MODES = [
    ("dcs_angle", "Differential cross section vs scattering angle"),
    ("form_factors", "Form factors vs momentum transfer"),
    ("compton_profile", "Compton profile J(pz)"),
    ("compton_shift", "Compton energy shift vs angle"),
]


class ScatteringTab(TabBase):
    TITLE = "Scattering"
    DESCRIPTION = ("Rayleigh and Compton differential cross sections, atomic form "
                   "factors, Compton profiles and the Compton energy shift.")

    def __init__(self, parent=None):
        super().__init__(parent, control_width=340)

        mode_card = Card("What to plot")
        self.combo_mode = QComboBox()
        for key, label in MODES:
            self.combo_mode.addItem(label, key)
        self.combo_mode.currentIndexChanged.connect(self._mode_changed)
        mode_card.add(self.combo_mode)
        self.controls.addWidget(mode_card)

        element_card = Card("Elements")
        self.picker = MultiElementPicker([6, 26, 79])
        element_card.add(self.picker)
        self.controls.addWidget(element_card)

        beam_card = Card("Beam")
        self.spin_energy = spin(0.01, 1_000_000.0, 20.0, decimals=4, step=5.0, suffix=" keV")
        self.spin_azimuth = spin(0.0, 360.0, 0.0, decimals=2, step=15.0, suffix=" °")
        self.spin_azimuth.setToolTip(
            "Azimuthal angle φ for the polarized differential cross sections.")
        self.chk_polarized = QCheckBox("Linearly polarized beam (use φ)")
        self.spin_points = int_spin(16, 4000, 361, step=20)
        form = beam_card.add_form()
        form.addRow("Energy", self.spin_energy)
        form.addRow("Points", self.spin_points)
        form.addRow("Azimuth φ", self.spin_azimuth)
        beam_card.add(self.chk_polarized)
        self._beam_form = form
        self.controls.addWidget(beam_card)

        curves_card = Card("Components")
        self.chk_rayl = QCheckBox("Rayleigh (coherent)")
        self.chk_compt = QCheckBox("Compton (incoherent)")
        self.chk_thomson = QCheckBox("Thomson (free electron)")
        self.chk_kn = QCheckBox("Klein–Nishina (free electron)")
        self.chk_rayl.setChecked(True)
        self.chk_compt.setChecked(True)
        for box in (self.chk_rayl, self.chk_compt, self.chk_thomson, self.chk_kn):
            box.toggled.connect(self.schedule)
            curves_card.add(box)
        self._curves_card = curves_card
        self.controls.addWidget(curves_card)

        extra_card = Card("Axis range")
        self.spin_qmax = spin(0.1, 1000.0, 10.0, decimals=3, step=1.0, suffix=" Å⁻¹")
        self.spin_pzmax = spin(0.1, 500.0, 20.0, decimals=3, step=5.0, suffix=" a.u.")
        self.chk_polar = QCheckBox("Polar plot")
        self.chk_polar.toggled.connect(self.schedule)
        eform = extra_card.add_form()
        eform.addRow("Max q", self.spin_qmax)
        eform.addRow("Max pz", self.spin_pzmax)
        extra_card.add(self.chk_polar)
        extra_card.add(subtitle_label(
            "q = sin(θ/2)/λ is xraylib's momentum-transfer convention, in Å⁻¹."))
        self._extra_form = eform
        self._extra_card = extra_card
        self.controls.addWidget(extra_card)

        self.bind(self.picker.changed, self.spin_energy.valueChanged,
                  self.spin_azimuth.valueChanged, self.spin_points.valueChanged,
                  self.chk_polarized.toggled, self.spin_qmax.valueChanged,
                  self.spin_pzmax.valueChanged)
        self.finish_controls()

        self.plot = self.add_plot(stretch=3)
        self.table = self.add_table(stretch=2)

        self._mode_changed()

    # -- control visibility ----------------------------------------------

    def _row_visible(self, form, widget, visible: bool) -> None:
        widget.setVisible(visible)
        label = form.labelForField(widget)
        if label:
            label.setVisible(visible)

    def _mode_changed(self) -> None:
        mode = self.combo_mode.currentData()
        angular = mode in ("dcs_angle", "compton_shift")
        self._curves_card.setVisible(mode in ("dcs_angle", "form_factors"))
        self.chk_polar.setVisible(angular)
        self._row_visible(self._beam_form, self.spin_azimuth,
                          mode == "dcs_angle")
        self.chk_polarized.setVisible(mode == "dcs_angle")
        self._row_visible(self._extra_form, self.spin_qmax, mode == "form_factors")
        self._row_visible(self._extra_form, self.spin_pzmax, mode == "compton_profile")
        self._extra_card.setVisible(angular or mode in ("form_factors", "compton_profile"))
        self.schedule()

    # -- compute ---------------------------------------------------------

    def recompute(self) -> None:
        zs = self.picker.zs()
        if not zs:
            self.plot.clear("Choose at least one element.")
            self.table.clear()
            return
        {
            "dcs_angle": self._dcs_angle,
            "form_factors": self._form_factors,
            "compton_profile": self._compton_profile,
            "compton_shift": self._compton_shift,
        }[self.combo_mode.currentData()](zs)

    # -- individual modes -------------------------------------------------

    def _dcs_angle(self, zs: list[int]) -> None:
        energy = self.spin_energy.value()
        n = self.spin_points.value()
        theta = np.linspace(0.0, math.pi, n)
        phi = math.radians(self.spin_azimuth.value())
        polarized = self.chk_polarized.isChecked()

        series, columns, data = [], [core.Column("theta", "θ [deg]", "{:.4g}")], [np.degrees(theta)]
        for z in zs:
            if self.chk_rayl.isChecked():
                fn = ((lambda t, zz=z: xrl.DCSP_Rayl(zz, energy, t, phi)) if polarized
                      else (lambda t, zz=z: xrl.DCS_Rayl(zz, energy, t)))
                values = core.sweep(fn, theta)
                series.append(core.Series(f"{elem.symbol(z)} Rayleigh", np.degrees(theta), values))
                columns.append(core.Column(f"r{z}", f"{elem.symbol(z)} Rayleigh", "{:.6g}"))
                data.append(values)
            if self.chk_compt.isChecked():
                fn = ((lambda t, zz=z: xrl.DCSP_Compt(zz, energy, t, phi)) if polarized
                      else (lambda t, zz=z: xrl.DCS_Compt(zz, energy, t)))
                values = core.sweep(fn, theta)
                series.append(core.Series(f"{elem.symbol(z)} Compton", np.degrees(theta), values))
                columns.append(core.Column(f"c{z}", f"{elem.symbol(z)} Compton", "{:.6g}"))
                data.append(values)

        if self.chk_thomson.isChecked():
            fn = ((lambda t: xrl.DCSP_Thoms(t, phi)) if polarized
                  else (lambda t: xrl.DCS_Thoms(t)))
            values = core.sweep(fn, theta)
            series.append(core.Series("Thomson", np.degrees(theta), values, color="#8892a4"))
            columns.append(core.Column("thoms", "Thomson", "{:.6g}"))
            data.append(values)
        if self.chk_kn.isChecked():
            fn = ((lambda t: xrl.DCSP_KN(energy, t, phi)) if polarized
                  else (lambda t: xrl.DCS_KN(energy, t)))
            values = core.sweep(fn, theta)
            series.append(core.Series("Klein–Nishina", np.degrees(theta), values, color="#b6bfd0"))
            columns.append(core.Column("kn", "Klein–Nishina", "{:.6g}"))
            data.append(values)

        if not series:
            self.plot.clear("Select at least one component.")
            self.table.clear()
            return

        polar = self.chk_polar.isChecked()
        spec = core.PlotSpec(
            series=[core.Series(s.label, np.radians(s.x) if polar else s.x, s.y, s.kind, s.color)
                    for s in series],
            xlabel="Scattering angle θ [deg]" if not polar else "θ",
            ylabel="dσ/dΩ  [cm²/g/sr]",
            title=(f"Differential scattering cross section at {energy:g} keV"
                   + (f", φ = {self.spin_azimuth.value():g}°" if polarized else "")),
            polar=polar,
            ylog=not polar,
        )
        self.plot.show_spec(spec)
        self._emit_table(columns, data, "Differential cross sections",
                         f"{energy:g} keV" + (", polarized" if polarized else ", unpolarized"))

    def _form_factors(self, zs: list[int]) -> None:
        n = self.spin_points.value()
        q = np.linspace(0.0, self.spin_qmax.value(), n)
        series, columns, data = [], [core.Column("q", "q [1/Å]", "{:.5g}")], [q]
        for z in zs:
            if self.chk_rayl.isChecked():
                values = core.sweep(lambda qq, zz=z: xrl.FF_Rayl(zz, qq), q)
                series.append(core.Series(f"{elem.symbol(z)} F(q) Rayleigh", q, values))
                columns.append(core.Column(f"ff{z}", f"{elem.symbol(z)} F(q)", "{:.6g}"))
                data.append(values)
            if self.chk_compt.isChecked():
                values = core.sweep(lambda qq, zz=z: xrl.SF_Compt(zz, qq), q)
                series.append(core.Series(f"{elem.symbol(z)} S(q) Compton", q, values))
                columns.append(core.Column(f"sf{z}", f"{elem.symbol(z)} S(q)", "{:.6g}"))
                data.append(values)
        if not series:
            self.plot.clear("Select Rayleigh and/or Compton.")
            self.table.clear()
            return
        self.plot.show_spec(core.PlotSpec(
            series=series,
            xlabel="Momentum transfer q [Å⁻¹]",
            ylabel="Form factor [electrons]",
            title="Atomic form factor F(q) and incoherent scattering function S(q)",
        ))
        self._emit_table(columns, data, "Form factors", "q = sin(θ/2)/λ")

    def _compton_profile(self, zs: list[int]) -> None:
        n = self.spin_points.value()
        pz = np.linspace(0.0, self.spin_pzmax.value(), n)
        series, columns, data = [], [core.Column("pz", "pz [a.u.]", "{:.5g}")], [pz]
        for z in zs:
            values = core.sweep(lambda p, zz=z: xrl.ComptonProfile(zz, p), pz)
            series.append(core.Series(f"{elem.symbol(z)} total", pz, values))
            columns.append(core.Column(f"j{z}", f"{elem.symbol(z)} J(pz)", "{:.6g}"))
            data.append(values)
        if not series:
            return
        self.plot.show_spec(core.PlotSpec(
            series=series,
            xlabel="Projected momentum pz [atomic units]",
            ylabel="Compton profile J(pz) [a.u.]",
            title="Total Compton profile",
            ylog=True,
        ))
        self._emit_table(columns, data, "Compton profiles", "non-relativistic impulse approximation")

    def _compton_shift(self, _zs: list[int]) -> None:
        energy = self.spin_energy.value()
        n = self.spin_points.value()
        theta = np.linspace(0.0, math.pi, n)
        scattered = core.sweep(lambda t: xrl.ComptonEnergy(energy, t), theta)
        transfer = core.sweep(lambda t: xrl.MomentTransf(energy, t), theta)
        shift = energy - scattered

        polar = self.chk_polar.isChecked()
        x = np.radians(np.degrees(theta)) if polar else np.degrees(theta)
        self.plot.show_spec(core.PlotSpec(
            series=[
                core.Series("Scattered energy", x, scattered),
                core.Series("Energy transferred to electron", x, shift),
            ],
            xlabel="Scattering angle θ [deg]" if not polar else "θ",
            ylabel="Energy [keV]",
            title=f"Compton scattering of a {energy:g} keV photon",
            polar=polar,
        ))
        self._emit_table(
            [core.Column("theta", "θ [deg]", "{:.4g}"),
             core.Column("e", "Scattered E′ [keV]", "{:.6g}"),
             core.Column("shift", "ΔE [keV]", "{:.6g}"),
             core.Column("lam", "λ′ [Å]", "{:.6g}"),
             core.Column("q", "q [1/Å]", "{:.6g}")],
            [np.degrees(theta), scattered, shift,
             np.array([core.wavelength(e) for e in scattered]), transfer],
            "Compton energy shift", f"incident {energy:g} keV")

    # -- shared ----------------------------------------------------------

    def _emit_table(self, columns, data, title: str, note: str) -> None:
        rows = [tuple(column[i] for column in data) for i in range(len(data[0]))]
        self.table.set_table(core.Table(columns=columns, rows=rows, title=title, note=note))
        self.status.emit(f"{len(rows)} points · {len(columns) - 1} curve(s)")
