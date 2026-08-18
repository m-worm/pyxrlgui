"""Form controls shared by the feature tabs."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import core, elements as elem
from .periodic import ElementDialog

# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def title_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "title")
    return label


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "section")
    return label


def subtitle_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "subtitle")
    label.setWordWrap(True)
    return label


class Card(QFrame):
    """Rounded panel with an optional small-caps heading."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("role", "card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 14)
        self._layout.setSpacing(9)
        if title:
            self._layout.addWidget(section_label(title))

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget, stretch: int = 0) -> QWidget:
        self._layout.addWidget(widget, stretch)
        return widget

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)

    def add_form(self) -> QFormLayout:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(7)
        self._layout.addLayout(form)
        return form


def spin(minimum: float, maximum: float, value: float, decimals: int = 3,
         step: float = 1.0, suffix: str = "") -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    box.setKeyboardTracking(False)
    if suffix:
        box.setSuffix(suffix)
    box.setMinimumWidth(96)
    return box


def int_spin(minimum: int, maximum: int, value: int, step: int = 1) -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setSingleStep(step)
    box.setValue(value)
    box.setKeyboardTracking(False)
    box.setMinimumWidth(96)
    return box


# --------------------------------------------------------------------------
# element pickers
# --------------------------------------------------------------------------


class ElementPicker(QWidget):
    """Searchable element combo with a periodic-table popup."""

    changed = Signal(int)

    def __init__(self, z: int = 26, parent=None):
        super().__init__(parent)
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        for element in elem.ELEMENTS:
            self.combo.addItem(f"{element.symbol} · {element.name}", element.Z)
        completer = self.combo.completer()
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.combo.setMinimumWidth(150)
        self.combo.currentIndexChanged.connect(self._emit)

        self.button = QToolButton()
        self.button.setText("⊞")
        self.button.setToolTip("Pick from the periodic table")
        self.button.clicked.connect(self._open_dialog)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.combo, 1)
        layout.addWidget(self.button)
        self.set_z(z)

    def _emit(self) -> None:
        self.changed.emit(self.z())

    def z(self) -> int:
        data = self.combo.currentData()
        if data is not None:
            return int(data)
        resolved = elem.lookup(self.combo.currentText().split("·")[0])
        return resolved or 26

    def set_z(self, z: int) -> None:
        index = self.combo.findData(z)
        if index >= 0:
            self.combo.setCurrentIndex(index)

    def _open_dialog(self) -> None:
        dialog = ElementDialog(self, current=self.z(), mode="single")
        if dialog.exec() == QDialog.Accepted:
            chosen = dialog.chosen()
            if chosen:
                self.set_z(chosen[0])


class MultiElementPicker(QWidget):
    """Free-text list of elements (``Fe, Cu, 82``) backed by the table popup."""

    changed = Signal(list)

    def __init__(self, zs: list[int] | None = None, parent=None):
        super().__init__(parent)
        self._zs: list[int] = list(zs or [26])

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Fe, Cu, Pb …")
        self.edit.editingFinished.connect(self._parse_text)

        self.button = QToolButton()
        self.button.setText("⊞")
        self.button.setToolTip("Pick from the periodic table")
        self.button.clicked.connect(self._open_dialog)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button)
        self._refresh_text()

    def zs(self) -> list[int]:
        return list(self._zs)

    def set_zs(self, zs: list[int]) -> None:
        self._zs = list(dict.fromkeys(zs))
        self._refresh_text()
        self.changed.emit(self.zs())

    def _refresh_text(self) -> None:
        self.edit.setText(", ".join(elem.symbol(z) for z in self._zs))

    def _parse_text(self) -> None:
        resolved = []
        for token in self.edit.text().replace(";", ",").split(","):
            z = elem.lookup(token)
            if z:
                resolved.append(z)
        if resolved and resolved != self._zs:
            self._zs = list(dict.fromkeys(resolved))
            self.changed.emit(self.zs())
        self._refresh_text()

    def _open_dialog(self) -> None:
        dialog = ElementDialog(self, mode="multi", selection=self._zs)
        if dialog.exec() == QDialog.Accepted:
            self.set_zs(dialog.chosen() or self._zs)


# --------------------------------------------------------------------------
# energy grid
# --------------------------------------------------------------------------


class EnergyGridBox(Card):
    """Min / max / point-count controls producing a numpy energy grid."""

    changed = Signal()

    def __init__(self, emin: float = 1.0, emax: float = 100.0, points: int = 800,
                 log: bool = True, title: str = "Energy range", parent=None):
        super().__init__(title, parent)
        self.spin_min = spin(0.001, 1_000_000.0, emin, decimals=3, step=1.0, suffix=" keV")
        self.spin_max = spin(0.002, 1_000_000.0, emax, decimals=3, step=1.0, suffix=" keV")
        self.spin_points = int_spin(2, 20000, points, step=100)
        self.combo_spacing = QComboBox()
        self.combo_spacing.addItems(["Logarithmic", "Linear"])
        self.combo_spacing.setCurrentIndex(0 if log else 1)

        form = self.add_form()
        form.addRow("From", self.spin_min)
        form.addRow("To", self.spin_max)
        form.addRow("Points", self.spin_points)
        form.addRow("Spacing", self.combo_spacing)

        for widget in (self.spin_min, self.spin_max, self.spin_points):
            widget.valueChanged.connect(self.changed)
        self.combo_spacing.currentIndexChanged.connect(self.changed)

    def is_log(self) -> bool:
        return self.combo_spacing.currentIndex() == 0

    def grid(self):
        return core.energy_grid(self.spin_min.value(), self.spin_max.value(),
                                self.spin_points.value(), self.is_log())

    def set_range(self, emin: float, emax: float) -> None:
        self.spin_min.setValue(emin)
        self.spin_max.setValue(emax)


# --------------------------------------------------------------------------
# material selection
# --------------------------------------------------------------------------


class MaterialBox(Card):
    """Choose a target as an element, a chemical formula or a NIST material."""

    changed = Signal()

    MODES = ["Element", "Chemical formula", "NIST material"]

    def __init__(self, title: str = "Material", parent=None,
                 default_formula: str = "H2O"):
        super().__init__(title, parent)
        self._error = ""

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(self.MODES)

        self.picker = ElementPicker(26)

        self.edit_formula = QLineEdit(default_formula)
        self.edit_formula.setPlaceholderText("e.g. Ca5(PO4)3F")

        self.combo_nist = QComboBox()
        self.combo_nist.setEditable(True)
        self.combo_nist.setInsertPolicy(QComboBox.NoInsert)
        self.combo_nist.addItems(core.nist_materials())
        nist_completer = self.combo_nist.completer()
        nist_completer.setFilterMode(Qt.MatchContains)
        nist_completer.setCaseSensitivity(Qt.CaseInsensitive)
        index = self.combo_nist.findText("Water, Liquid")
        if index >= 0:
            self.combo_nist.setCurrentIndex(index)

        self.spin_density = spin(0.0, 30.0, 0.0, decimals=4, step=0.1, suffix=" g/cm³")
        self.spin_density.setSpecialValueText("auto")
        self.spin_density.setToolTip(
            "Leave on 'auto' to use the tabulated density.\n"
            "Needed for linear attenuation, transmission and refractive index.")

        form = self.add_form()
        form.addRow("Source", self.combo_mode)
        self._row_element = self.picker
        self._row_formula = self.edit_formula
        self._row_nist = self.combo_nist
        form.addRow("Element", self.picker)
        form.addRow("Formula", self.edit_formula)
        form.addRow("Material", self.combo_nist)
        form.addRow("Density", self.spin_density)
        self._form = form

        self.lbl_info = subtitle_label("")
        self.add(self.lbl_info)

        self.combo_mode.currentIndexChanged.connect(self._mode_changed)
        self.picker.changed.connect(self._on_changed)
        self.edit_formula.editingFinished.connect(self._on_changed)
        self.combo_nist.currentIndexChanged.connect(self._on_changed)
        self.spin_density.valueChanged.connect(self._on_changed)

        self._mode_changed()

    # -- state -----------------------------------------------------------

    def _set_row_visible(self, widget: QWidget, visible: bool) -> None:
        widget.setVisible(visible)
        label = self._form.labelForField(widget)
        if label:
            label.setVisible(visible)

    def _mode_changed(self) -> None:
        mode = self.combo_mode.currentIndex()
        self._set_row_visible(self.picker, mode == 0)
        self._set_row_visible(self.edit_formula, mode == 1)
        self._set_row_visible(self.combo_nist, mode == 2)
        self._on_changed()

    def _on_changed(self) -> None:
        self._refresh_info()
        self.changed.emit()

    def _refresh_info(self) -> None:
        try:
            material = self.material()
        except ValueError as exc:
            self._error = str(exc)
            self.edit_formula.setProperty("state", "invalid")
            self.lbl_info.setText(f"⚠ {exc}")
            self.lbl_info.setProperty("role", "error")
        else:
            self._error = ""
            self.edit_formula.setProperty("state", "")
            bits = [f"{len(material.composition)} element(s)"]
            if material.molar_mass:
                bits.append(f"M = {material.molar_mass:.3f} g/mol")
            bits.append(f"ρ = {material.density:g} g/cm³" if material.density
                        else "ρ unknown — set it for μ, transmission and optics")
            self.lbl_info.setText(" · ".join(bits))
            self.lbl_info.setProperty("role", "subtitle")
        # Re-polish so the property-driven styling refreshes.
        for widget in (self.edit_formula, self.lbl_info):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def error(self) -> str:
        return self._error

    def material(self) -> core.Material:
        """Build the selected material, or raise ``ValueError``."""
        override = self.spin_density.value() or None
        mode = self.combo_mode.currentIndex()
        if mode == 0:
            material = core.Material.from_element(self.picker.z())
        elif mode == 1:
            text = self.edit_formula.text().strip()
            if not text:
                raise ValueError("Enter a chemical formula.")
            try:
                material = core.Material.from_formula(text)
            except Exception:
                raise ValueError(f"'{text}' is not a valid chemical formula.") from None
        else:
            name = self.combo_nist.currentText()
            try:
                material = core.Material.from_nist(name)
            except Exception:
                raise ValueError(f"'{name}' is not a known NIST material.") from None
        if override:
            material.density = override
        return material

    def material_or_none(self) -> core.Material | None:
        try:
            return self.material()
        except ValueError:
            return None


# --------------------------------------------------------------------------
# metric tiles
# --------------------------------------------------------------------------


class ResultTiles(QWidget):
    """A responsive grid of label/value tiles for headline numbers."""

    def __init__(self, columns: int = 4, parent=None):
        super().__init__(parent)
        self._columns = columns
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(8)
        self._tiles: list[QFrame] = []

    def set_values(self, items: list[tuple[str, str, str]]) -> None:
        """``items`` are ``(caption, value, unit)`` triples."""
        for tile in self._tiles:
            self._grid.removeWidget(tile)
            tile.deleteLater()
        self._tiles.clear()

        for index, (caption, value, unit) in enumerate(items):
            tile = QFrame()
            tile.setProperty("role", "tile")
            tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout = QVBoxLayout(tile)
            layout.setContentsMargins(11, 7, 11, 8)
            layout.setSpacing(1)

            # Deliberately not upper-cased: captions carry Greek symbols, and
            # str.upper() turns "μ/ρ" into "Μ/Ρ", which reads as "M/P".
            cap = QLabel(caption)
            cap.setProperty("role", "section")
            value_label = QLabel(value)
            value_label.setProperty("role", "metric")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(cap)
            layout.addWidget(value_label)
            if unit:
                unit_label = QLabel(unit)
                unit_label.setProperty("role", "subtitle")
                layout.addWidget(unit_label)

            self._grid.addWidget(tile, index // self._columns, index % self._columns)
            self._tiles.append(tile)


def fmt(value: float, digits: int = 6, dash: str = "—") -> str:
    """Format a float for display, collapsing NaN/None to an em dash."""
    if value is None:
        return dash
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(value):
        return dash
    return f"{value:.{digits}g}"
