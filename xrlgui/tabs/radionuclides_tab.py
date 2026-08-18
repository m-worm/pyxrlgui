"""X-ray and gamma emission of the radionuclides in xraylib's database."""

from __future__ import annotations

import math

import numpy as np
import xraylib as xrl
from PySide6.QtWidgets import QCheckBox, QComboBox

from .. import core, elements as elem
from ..widgets.inputs import Card, ResultTiles, fmt, spin, subtitle_label
from .base import TabBase


class RadionuclidesTab(TabBase):
    TITLE = "Radionuclides"
    DESCRIPTION = ("Characteristic X-ray and gamma emission of the calibration "
                   "sources bundled with xraylib.")

    def __init__(self, parent=None):
        super().__init__(parent, control_width=330)

        source = Card("Source")
        self.combo_source = QComboBox()
        self.combo_source.addItems(core.radionuclides())
        self.combo_source.currentIndexChanged.connect(self.schedule)
        source.add(self.combo_source)
        self.lbl_meta = subtitle_label("")
        source.add(self.lbl_meta)
        self.tiles = ResultTiles(columns=2)
        source.add(self.tiles)
        self.controls.addWidget(source)

        display = Card("Spectrum")
        self.chk_xrays = QCheckBox("X-ray lines")
        self.chk_gammas = QCheckBox("Gamma lines")
        self.chk_xrays.setChecked(True)
        self.chk_gammas.setChecked(True)
        self.chk_log = QCheckBox("Logarithmic intensity axis")
        self.chk_log.setChecked(True)
        self.spin_threshold = spin(0.0, 100.0, 0.0, decimals=6, step=0.01, suffix=" %")
        self.spin_threshold.setToolTip("Hide lines weaker than this fraction of the strongest line.")
        for box in (self.chk_xrays, self.chk_gammas, self.chk_log):
            box.toggled.connect(self.schedule)
            display.add(box)
        display.add_form().addRow("Cut-off", self.spin_threshold)
        display.add(subtitle_label(
            "Intensities are emitted photons per decay, as tabulated by xraylib."))
        self.controls.addWidget(display)

        self.bind(self.spin_threshold.valueChanged)
        self.finish_controls()

        self.plot = self.add_plot(stretch=3, ylog=True)
        self.table = self.add_table(stretch=2)
        self.schedule()

    # -- compute ---------------------------------------------------------

    def recompute(self) -> None:
        name = self.combo_source.currentText()
        data = xrl.GetRadioNuclideDataByName(name)

        z_parent, z_xray = data["Z"], data["Z_xray"]
        self.lbl_meta.setText(
            f"{elem.name(z_parent)}-{data['A']} · Z = {z_parent}, N = {data['N']} · "
            f"X-rays are those of {elem.name(z_xray)} ({elem.symbol(z_xray)}), "
            f"the daughter element")

        # X-ray lines ----------------------------------------------------
        x_energies, x_intensities, x_labels = [], [], []
        for line_value, intensity in zip(data["XrayLines"], data["XrayIntensities"]):
            energy = core.safe(xrl.LineEnergy, z_xray, line_value)
            if not math.isfinite(energy):
                continue
            spec = core.line_spec(line_value)
            x_energies.append(energy)
            x_intensities.append(intensity)
            x_labels.append(spec.short or spec.iupac)

        g_energies = list(data["GammaEnergies"])
        g_intensities = list(data["GammaIntensities"])

        show_x = self.chk_xrays.isChecked() and x_energies
        show_g = self.chk_gammas.isChecked() and g_energies
        pool = ([*x_intensities] if show_x else []) + ([*g_intensities] if show_g else [])
        if not pool:
            self.plot.clear("Nothing selected to display.")
            self.table.clear()
            self.tiles.set_values([])
            return

        cutoff = (self.spin_threshold.value() / 100.0) * max(pool)

        series, rows = [], []
        if show_x:
            keep = [i for i, v in enumerate(x_intensities) if v >= cutoff]
            if keep:
                series.append(core.Series(
                    f"{elem.symbol(z_xray)} X-ray lines",
                    np.array([x_energies[i] for i in keep]),
                    np.array([x_intensities[i] for i in keep]),
                    kind="stick",
                    annotations=[x_labels[i] for i in keep]))
            for i in keep:
                rows.append(("X-ray", x_labels[i], x_energies[i],
                             core.wavelength(x_energies[i]), x_intensities[i]))
        if show_g:
            keep = [i for i, v in enumerate(g_intensities) if v >= cutoff]
            if keep:
                series.append(core.Series(
                    "Gamma lines",
                    np.array([g_energies[i] for i in keep]),
                    np.array([g_intensities[i] for i in keep]),
                    kind="stick",
                    annotations=[f"γ{i + 1}" for i in keep],
                    color="#ff7a59"))
            for i in keep:
                rows.append(("Gamma", f"γ{i + 1}", g_energies[i],
                             core.wavelength(g_energies[i]), g_intensities[i]))

        if not series:
            self.plot.clear("Every line falls below the cut-off.")
            self.table.clear()
            return

        self.plot.show_spec(core.PlotSpec(
            series=series,
            xlabel="Energy [keV]",
            ylabel="Intensity [photons per decay]",
            title=f"{name} emission spectrum",
            ylog=self.chk_log.isChecked(),
        ))

        rows.sort(key=lambda r: -r[4])
        self.table.set_table(core.Table(
            columns=[
                core.Column("type", "Type", numeric=False),
                core.Column("line", "Line", numeric=False),
                core.Column("E", "Energy [keV]", "{:.5f}"),
                core.Column("lam", "λ [Å]", "{:.5g}"),
                core.Column("I", "Intensity [/decay]", "{:.6g}"),
            ],
            rows=rows,
            title=f"{name} emission lines",
            note=f"X-rays from {elem.symbol(z_xray)}",
        ))

        strongest = max(rows, key=lambda r: r[4]) if rows else None
        self.tiles.set_values([
            ("X-ray lines", str(data["nXrays"]), f"from {elem.symbol(z_xray)}"),
            ("Gamma lines", str(data["nGammas"]), ""),
            ("Strongest line", fmt(strongest[2], 6) if strongest else "—",
             f"keV ({strongest[1]})" if strongest else ""),
            ("Its intensity", fmt(strongest[4], 4) if strongest else "—", "per decay"),
        ])
        self.status.emit(f"{name}: {len(rows)} lines shown")
