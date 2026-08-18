"""Shared scaffolding for the feature tabs."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..widgets import PlotPanel, TablePanel
from ..widgets.inputs import subtitle_label, title_label


class TabBase(QWidget):
    """A tab with a scrollable control column on the left and results on the right.

    Subclasses fill ``self.controls`` with cards and implement :meth:`recompute`.
    Control changes are funnelled through :meth:`schedule` so a burst of signals
    (typing in a spin box, toggling several checkboxes) triggers one recompute.
    """

    #: Short blurb shown under the tab heading.
    DESCRIPTION = ""
    TITLE = ""

    status = Signal(str)

    def __init__(self, parent=None, control_width: int = 350):
        super().__init__(parent)
        self._palette = theme.DARK
        self._dirty = False

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._run)

        # left: controls -------------------------------------------------
        self.controls = QVBoxLayout()
        self.controls.setContentsMargins(0, 0, 8, 0)
        self.controls.setSpacing(10)

        header = QVBoxLayout()
        header.setSpacing(2)
        if self.TITLE:
            header.addWidget(title_label(self.TITLE))
        if self.DESCRIPTION:
            header.addWidget(subtitle_label(self.DESCRIPTION))
        self.controls.addLayout(header)

        holder = QWidget()
        holder.setLayout(self.controls)
        scroll = QScrollArea()
        scroll.setWidget(holder)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumWidth(control_width)
        scroll.setMaximumWidth(control_width + 130)
        self._scroll = scroll

        # right: results -------------------------------------------------
        self.results = QSplitter(Qt.Vertical)
        self.results.setChildrenCollapsible(True)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)
        outer.addWidget(scroll)
        outer.addWidget(self.results, 1)

    # -- convenience -----------------------------------------------------

    def add_plot(self, stretch: int = 3, **kwargs) -> PlotPanel:
        panel = PlotPanel(**kwargs)
        self.results.addWidget(panel)
        self.results.setStretchFactor(self.results.count() - 1, stretch)
        return panel

    def add_table(self, stretch: int = 2, **kwargs) -> TablePanel:
        panel = TablePanel(**kwargs)
        self.results.addWidget(panel)
        self.results.setStretchFactor(self.results.count() - 1, stretch)
        return panel

    def finish_controls(self) -> None:
        """Call once every control card has been added."""
        self.controls.addStretch(1)
        # Long combo entries (NIST material names, unit labels) otherwise force
        # the control column wider than its viewport and get clipped.
        for combo in self._scroll.widget().findChildren(QComboBox):
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(10)

    def bind(self, *signals) -> None:
        """Connect any number of signals to :meth:`schedule`."""
        for signal in signals:
            signal.connect(self.schedule)

    # -- recompute plumbing ---------------------------------------------

    def schedule(self, *_args) -> None:
        self._dirty = True
        if self.isVisible():
            self._timer.start()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        if self._dirty:
            self._timer.start()

    def _run(self) -> None:
        self._dirty = False
        try:
            self.recompute()
        except Exception as exc:  # a bad input should never kill the window
            self.status.emit(f"{type(exc).__name__}: {exc}")
            self.on_error(exc)

    def recompute(self) -> None:
        raise NotImplementedError

    def on_error(self, exc: Exception) -> None:
        for panel in self.results.findChildren(PlotPanel):
            panel.clear(str(exc))

    # -- theming ---------------------------------------------------------

    def set_palette(self, palette: theme.Palette) -> None:
        self._palette = palette
        for panel in self.findChildren(PlotPanel):
            panel.set_palette(palette)
        from ..widgets import PeriodicTable
        for table in self.findChildren(PeriodicTable):
            table.set_palette(palette)
