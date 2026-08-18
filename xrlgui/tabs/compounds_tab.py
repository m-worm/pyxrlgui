"""Formula parsing, the NIST material catalog and a mixture builder."""

from __future__ import annotations

import math

import numpy as np
import xraylib as xrl
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import core, elements as elem
from ..widgets.inputs import Card, ResultTiles, fmt, spin, subtitle_label
from .base import TabBase


class CompoundsTab(TabBase):
    TITLE = "Compounds & materials"
    DESCRIPTION = ("Parse chemical formulae, browse the 180 NIST reference materials "
                   "and blend arbitrary mixtures by mass.")

    def __init__(self, parent=None):
        super().__init__(parent, control_width=350)

        source = Card("Source")
        self.combo_source = QComboBox()
        self.combo_source.addItems(["Chemical formula", "NIST material", "Mixture"])
        self.combo_source.currentIndexChanged.connect(self._source_changed)
        source.add_form().addRow("Define by", self.combo_source)

        # -- formula page ------------------------------------------------
        formula_page = QWidget()
        formula_layout = QVBoxLayout(formula_page)
        formula_layout.setContentsMargins(0, 0, 0, 0)
        formula_layout.setSpacing(6)
        self.edit_formula = QLineEdit("Ca5(PO4)3F")
        self.edit_formula.setPlaceholderText("e.g. SiO2, Ca5(PO4)3F, Fe0.7Cr0.3")
        self.edit_formula.textEdited.connect(self.schedule)
        formula_layout.addWidget(self.edit_formula)
        formula_layout.addWidget(subtitle_label(
            "Nested groups and fractional subscripts are supported."))

        # -- NIST page ---------------------------------------------------
        nist_page = QWidget()
        nist_layout = QVBoxLayout(nist_page)
        nist_layout.setContentsMargins(0, 0, 0, 0)
        nist_layout.setSpacing(6)
        self.edit_nist_filter = QLineEdit()
        self.edit_nist_filter.setPlaceholderText("Search 180 materials…")
        self.edit_nist_filter.setClearButtonEnabled(True)
        self.edit_nist_filter.textChanged.connect(self._filter_nist)
        self.list_nist = QListWidget()
        self.list_nist.addItems(core.nist_materials())
        self.list_nist.setCurrentRow(0)
        self.list_nist.setMinimumHeight(200)
        self.list_nist.currentRowChanged.connect(self.schedule)
        nist_layout.addWidget(self.edit_nist_filter)
        nist_layout.addWidget(self.list_nist)

        # -- mixture page ------------------------------------------------
        mixture_page = QWidget()
        mixture_layout = QVBoxLayout(mixture_page)
        mixture_layout.setContentsMargins(0, 0, 0, 0)
        mixture_layout.setSpacing(6)
        self.edit_component = QLineEdit("SiO2")
        self.edit_component.setPlaceholderText("Formula or NIST name")
        self.spin_weight = spin(0.0001, 1000.0, 1.0, decimals=4, step=0.1)
        self.spin_weight.setToolTip("Relative weight; the mixture is normalized by mass.")
        add_row = QHBoxLayout()
        add_row.setSpacing(5)
        add_row.addWidget(self.edit_component, 1)
        add_row.addWidget(self.spin_weight)
        btn_add = QPushButton("Add component")
        btn_add.setProperty("role", "primary")
        btn_add.clicked.connect(self._add_component)
        self.list_mixture = QListWidget()
        self.list_mixture.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_mixture.setMinimumHeight(130)
        btn_remove = QPushButton("Remove selected")
        btn_remove.setProperty("role", "ghost")
        btn_remove.clicked.connect(self._remove_components)
        mixture_layout.addLayout(add_row)
        mixture_layout.addWidget(btn_add)
        mixture_layout.addWidget(self.list_mixture)
        mixture_layout.addWidget(btn_remove)
        mixture_layout.addWidget(subtitle_label(
            "Weights are mass ratios. Density is estimated by volume addition "
            "when every component has one."))

        # Plain show/hide rather than a QStackedWidget: QStackedLayout always
        # reserves the height of its tallest page, which would leave a large
        # gap under the short formula page.
        self._pages = [formula_page, nist_page, mixture_page]
        for page in self._pages:
            source.add(page)
        self.controls.addWidget(source)

        # -- probe -------------------------------------------------------
        probe = Card("Evaluate at")
        self.spin_energy = spin(0.001, 1_000_000.0, 10.0, decimals=4, step=1.0, suffix=" keV")
        self.spin_density = spin(0.0, 30.0, 0.0, decimals=4, step=0.1, suffix=" g/cm³")
        self.spin_density.setSpecialValueText("auto")
        pform = probe.add_form()
        pform.addRow("Energy", self.spin_energy)
        pform.addRow("Density", self.spin_density)
        self.tiles = ResultTiles(columns=2)
        probe.add(self.tiles)
        self.controls.addWidget(probe)

        self.bind(self.spin_energy.valueChanged, self.spin_density.valueChanged)
        self.finish_controls()

        self.plot = self.add_plot(stretch=2)
        self.table = self.add_table(stretch=3)

        self._mixture: list[tuple[str, float]] = [("SiO2", 0.7), ("Al2O3", 0.3)]
        self._refresh_mixture_list()
        self._source_changed()

    # -- source pages ----------------------------------------------------

    def _source_changed(self) -> None:
        current = self.combo_source.currentIndex()
        for index, page in enumerate(self._pages):
            page.setVisible(index == current)
        self.schedule()

    def _filter_nist(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.list_nist.count()):
            item = self.list_nist.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _add_component(self) -> None:
        name = self.edit_component.text().strip()
        if not name:
            return
        self._mixture.append((name, self.spin_weight.value()))
        self._refresh_mixture_list()
        self.schedule()

    def _remove_components(self) -> None:
        for item in self.list_mixture.selectedItems():
            index = self.list_mixture.row(item)
            if 0 <= index < len(self._mixture):
                self._mixture.pop(index)
        self._refresh_mixture_list()
        self.schedule()

    def _refresh_mixture_list(self) -> None:
        self.list_mixture.clear()
        total = sum(w for _n, w in self._mixture) or 1.0
        for name, weight in self._mixture:
            self.list_mixture.addItem(
                QListWidgetItem(f"{name}   —   {weight:g}  ({weight / total * 100:.1f} % by mass)"))

    # -- material --------------------------------------------------------

    def _component(self, name: str) -> core.Material:
        try:
            return core.Material.from_formula(name)
        except Exception:
            return core.Material.from_nist(name)

    def _material(self) -> core.Material:
        mode = self.combo_source.currentIndex()
        if mode == 0:
            text = self.edit_formula.text().strip()
            if not text:
                raise ValueError("Enter a chemical formula.")
            try:
                material = core.Material.from_formula(text)
            except Exception:
                raise ValueError(f"'{text}' is not a valid chemical formula.") from None
        elif mode == 1:
            item = self.list_nist.currentItem()
            if item is None:
                raise ValueError("Choose a NIST material.")
            material = core.Material.from_nist(item.text())
        else:
            if not self._mixture:
                raise ValueError("Add at least one mixture component.")
            parts = []
            for name, weight in self._mixture:
                try:
                    parts.append((self._component(name), weight))
                except Exception:
                    raise ValueError(f"'{name}' is neither a formula nor a NIST material.") from None
            material = core.Material.from_mixture(
                parts, name=" + ".join(n for n, _w in self._mixture))
        override = self.spin_density.value() or None
        if override:
            material.density = override
        return material

    # -- compute ---------------------------------------------------------

    def recompute(self) -> None:
        try:
            material = self._material()
        except ValueError as exc:
            self.plot.clear(str(exc))
            self.table.clear()
            self.tiles.set_values([])
            self.status.emit(str(exc))
            return

        energy = self.spin_energy.value()
        total_cs = material.cs("total", energy)

        rows = []
        stoich = dict(material.stoichiometry)
        atom_total = sum(stoich.values()) if stoich else 0.0
        for z, fraction in material.composition:
            weight = core.safe(xrl.AtomicWeight, z)
            element_cs = core.safe(xrl.CS_Total, z, energy)
            rows.append((
                elem.symbol(z),
                elem.name(z),
                z,
                stoich.get(z, float("nan")),
                (stoich.get(z, float("nan")) / atom_total) if atom_total else float("nan"),
                fraction,
                weight,
                element_cs,
                fraction * element_cs,
                (fraction * element_cs / total_cs) if total_cs else float("nan"),
            ))
        rows.sort(key=lambda r: -r[5])

        self.table.set_table(core.Table(
            columns=[
                core.Column("sym", "Element", numeric=False),
                core.Column("name", "Name", numeric=False),
                core.Column("z", "Z", "{:.0f}"),
                core.Column("atoms", "Atoms / unit", "{:.4g}"),
                core.Column("afrac", "Atomic fraction", "{:.5f}"),
                core.Column("wfrac", "Mass fraction", "{:.6f}"),
                core.Column("aw", "Atomic weight", "{:.4f}"),
                core.Column("cs", f"μ/ρ @ {energy:g} keV", "{:.5g}"),
                core.Column("contrib", "Contribution", "{:.5g}"),
                core.Column("share", "Share of μ/ρ", "{:.4%}"),
            ],
            rows=rows,
            title=material.name,
            note=f"composition at {energy:g} keV",
        ))

        positions = np.arange(len(rows), dtype=float)
        self.plot.show_spec(core.PlotSpec(
            series=[
                core.Series("Mass fraction", positions,
                            np.array([r[5] for r in rows]), kind="bar",
                            annotations=[r[0] for r in rows]),
            ],
            xlabel="Element",
            ylabel="Mass fraction",
            title=f"Composition of {material.name}",
            legend=False,
        ))

        self._refresh_tiles(material, energy, total_cs)
        self.status.emit(f"{material.name}: {len(rows)} elements")

    def _refresh_tiles(self, material: core.Material, energy: float, total_cs: float) -> None:
        electron_density = float("nan")
        if material.density:
            acc = 0.0
            for z, w in material.composition:
                a = core.safe(xrl.AtomicWeight, z)
                if math.isfinite(a):
                    acc += w * z / a
            electron_density = acc * core.AVOGADRO * material.density

        items = [
            ("Molar mass", fmt(material.molar_mass, 6) if material.molar_mass else "—", "g/mol"),
            ("Density", fmt(material.density, 5) if material.density else "—", "g/cm³"),
            ("Mean Z (by mass)", fmt(material.mean_z, 4), ""),
            ("Mean atomic mass", fmt(material.mean_atomic_mass, 5), "g/mol per atom"),
            ("μ/ρ total", fmt(total_cs, 6), f"cm²/g at {energy:g} keV"),
            ("Electron density", fmt(electron_density, 4), "e⁻/cm³"),
        ]
        if material.density and math.isfinite(total_cs):
            mu = total_cs * material.density
            items.append(("μ linear", fmt(mu, 6), "1/cm"))
            items.append(("1/e depth", fmt(1.0 / mu, 5) if mu > 0 else "—", "cm"))
        self.tiles.set_values(items)
