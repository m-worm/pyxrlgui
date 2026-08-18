"""Sortable, filterable, exportable result table."""

from __future__ import annotations

import csv
import math

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..core import Column, Table


class TableModel(QAbstractTableModel):
    """Adapts a :class:`~xrlgui.core.Table` to Qt's model/view framework."""

    def __init__(self, table: Table | None = None):
        super().__init__()
        self._table = table or Table(columns=[], rows=[])

    def set_table(self, table: Table) -> None:
        self.beginResetModel()
        self._table = table
        self.endResetModel()

    @property
    def table(self) -> Table:
        return self._table

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._table.rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._table.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        column: Column = self._table.columns[index.column()]
        value = self._table.rows[index.row()][index.column()]
        if role == Qt.DisplayRole:
            return column.render(value)
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignRight | Qt.AlignVCenter) if column.numeric \
                else int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.UserRole:
            # Sort on the underlying value, not the formatted string.
            if column.numeric:
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    return -math.inf
                return number if math.isfinite(number) else -math.inf
            return str(value)
        return None

    def headerData(self, section: int, orientation, role: int = Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._table.columns[section].label
        return str(section + 1)


class _SortProxy(QSortFilterProxyModel):
    def lessThan(self, left, right) -> bool:  # noqa: N802
        a = self.sourceModel().data(left, Qt.UserRole)
        b = self.sourceModel().data(right, Qt.UserRole)
        try:
            return a < b
        except TypeError:
            return str(a) < str(b)


class TablePanel(QFrame):
    """A results table with a filter box, copy-to-clipboard and CSV export."""

    def __init__(self, parent: QWidget | None = None, show_filter: bool = True):
        super().__init__(parent)
        self.setProperty("role", "card")

        self.model = TableModel()
        self.proxy = _SortProxy(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        # setSortingEnabled() installs a sort indicator on column 0; clear it so
        # freshly computed tables appear in their natural (computed) order.
        self.view.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.verticalHeader().setDefaultSectionSize(26)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.view.setWordWrap(False)

        self.lbl_title = QLabel("")
        self.lbl_title.setProperty("role", "section")
        self.lbl_count = QLabel("")
        self.lbl_count.setProperty("role", "subtitle")

        self.edit_filter = QLineEdit()
        self.edit_filter.setPlaceholderText("Filter rows…")
        self.edit_filter.setClearButtonEnabled(True)
        self.edit_filter.setMaximumWidth(190)
        self.edit_filter.textChanged.connect(self.proxy.setFilterFixedString)
        self.edit_filter.setVisible(show_filter)

        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setProperty("role", "ghost")
        self.btn_copy.setToolTip("Copy the selection, or the whole table if nothing is selected (Ctrl+C)")
        self.btn_copy.clicked.connect(self.copy_selection)

        self.btn_export = QPushButton("Export CSV…")
        self.btn_export.setProperty("role", "ghost")
        self.btn_export.clicked.connect(self.export_csv)

        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 10, 0)
        header.setSpacing(8)
        header.addWidget(self.lbl_title)
        header.addWidget(self.lbl_count)
        header.addStretch(1)
        header.addWidget(self.edit_filter)
        header.addWidget(self.btn_copy)
        header.addWidget(self.btn_export)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.view, 1)

        QShortcut(QKeySequence.Copy, self.view, activated=self.copy_selection)

    # -- content ---------------------------------------------------------

    def set_table(self, table: Table) -> None:
        self.proxy.sort(-1)
        self.view.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.model.set_table(table)
        self.lbl_title.setText(table.title)
        suffix = f" · {table.note}" if table.note else ""
        self.lbl_count.setText(f"{len(table.rows)} rows{suffix}")
        self.view.resizeColumnsToContents()
        header = self.view.horizontalHeader()
        for i in range(self.model.columnCount()):
            header.resizeSection(i, min(max(header.sectionSize(i) + 16, 70), 320))

    def clear(self) -> None:
        self.set_table(Table(columns=[], rows=[]))

    # -- export ----------------------------------------------------------

    def _visible_rows(self) -> list[list[str]]:
        rows = []
        for r in range(self.proxy.rowCount()):
            row = []
            for c in range(self.proxy.columnCount()):
                row.append(self.proxy.data(self.proxy.index(r, c), Qt.DisplayRole))
            rows.append(row)
        return rows

    def copy_selection(self) -> None:
        selected = self.view.selectionModel().selectedIndexes()
        if selected:
            rows = sorted({i.row() for i in selected})
            cols = sorted({i.column() for i in selected})
            lines = ["\t".join(self._headers()[c] for c in cols)]
            for r in rows:
                lines.append("\t".join(
                    str(self.proxy.data(self.proxy.index(r, c), Qt.DisplayRole) or "")
                    for c in cols))
        else:
            lines = ["\t".join(self._headers())]
            lines += ["\t".join(str(v or "") for v in row) for row in self._visible_rows()]
        QGuiApplication.clipboard().setText("\n".join(lines))

    def _headers(self) -> list[str]:
        return [c.label for c in self.model.table.columns]

    def export_csv(self) -> None:
        if not self.model.table.rows:
            QMessageBox.information(self, "Nothing to export", "The table is empty.")
            return
        default = (self.model.table.title or "xraylib-data").replace(" ", "_") + ".csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export table", default, "CSV file (*.csv);;Tab-separated (*.tsv)")
        if not path:
            return
        delimiter = "\t" if path.lower().endswith(".tsv") else ","
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, delimiter=delimiter)
                if self.model.table.note:
                    writer.writerow([f"# {self.model.table.title} — {self.model.table.note}"])
                writer.writerow(self._headers())
                writer.writerows(self._visible_rows())
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
