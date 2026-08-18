"""Main window and application entry point."""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QSettings, Qt, qVersion
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, __version__, core, theme
from .branding import app_icon, render_pixmap
from .tabs import TAB_ORDER

ORG = "pyxrlgui"


def _make_icon() -> QIcon:
    """The shared application mark, rendered at several sizes."""
    return app_icon()


class AboutDialog(QDialog):
    """Credits, citations and the third-party license notices.

    The Qt/LGPL paragraph is not decoration: the LGPL requires a distributed
    application to state that it uses Qt under the LGPL and to point at the
    library's source.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumSize(660, 560)

        palette = getattr(parent.window(), "active_palette", theme.DARK) if parent else theme.DARK

        mark = QLabel()
        mark.setPixmap(render_pixmap(64))
        mark.setFixedSize(64, 64)

        heading = QLabel(f"<div style='font-size:20px;font-weight:600'>{APP_NAME}</div>"
                         f"<div style='color:{palette.muted}'>version {__version__} · "
                         f"xraylib {core.XRAYLIB_VERSION} · Qt {qVersion()}</div>")
        heading.setTextFormat(Qt.RichText)

        header = QHBoxLayout()
        header.setSpacing(14)
        header.addWidget(mark)
        header.addWidget(heading, 1)

        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setHtml(self._html(palette))

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addWidget(body, 1)
        layout.addWidget(buttons)

    @staticmethod
    def _html(palette: theme.Palette) -> str:
        muted, accent = palette.muted, palette.accent
        return f"""
<style>
  body {{ font-size: 13px; }}
  h3 {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
        color: {muted}; margin-top: 16px; margin-bottom: 4px; }}
  a  {{ color: {accent}; text-decoration: none; }}
  p  {{ margin: 5px 0; }}
  .cite {{ color: {muted}; margin: 6px 0 6px 12px; }}
</style>

<p>A cross-platform desktop front end for
<b>xraylib</b>, the X-ray physics database. Every number shown comes straight
from xraylib; this application only arranges, converts, tabulates and plots it.</p>

<h3>Citing xraylib</h3>
<p>If you publish results obtained with this program, the xraylib authors ask
that you cite their work. The 2011 paper supersedes the 2004 original and is the
one to cite for current versions:</p>
<p class="cite">T. Schoonjans, A. Brunetti, B. Golosio, M. Sanchez del Rio,
V.&nbsp;A.&nbsp;Sol&eacute;, C. Ferrero and L. Vincze,
&ldquo;The xraylib library for X-ray&ndash;matter interactions. Recent
developments&rdquo;, <i>Spectrochimica Acta Part B</i> <b>66</b> (2011)
776&ndash;784.<br>
<a href="https://doi.org/10.1016/j.sab.2011.09.011">doi:10.1016/j.sab.2011.09.011</a></p>
<p class="cite">A. Brunetti, M. Sanchez del Rio, B. Golosio, A. Simionovici and
A. Somogyi, &ldquo;A library for X-ray matter interaction cross sections for
X-ray fluorescence applications&rdquo;, <i>Spectrochimica Acta Part B</i>
<b>59</b> (2004) 1725&ndash;1731.<br>
<a href="https://doi.org/10.1016/j.sab.2004.03.014">doi:10.1016/j.sab.2004.03.014</a></p>
<p>xraylib is by Tom Schoonjans and contributors, under the BSD 3-Clause
license &mdash;
<a href="https://github.com/tschoonj/xraylib">github.com/tschoonj/xraylib</a></p>

<h3>Qt and PySide6</h3>
<p>This program uses the <b>Qt</b> toolkit through <b>PySide6</b>, licensed
under the <b>GNU Lesser General Public License version&nbsp;3</b>. Qt is not
modified by this program, and is bundled as separate shared libraries so that
you may replace them with your own build of Qt.</p>
<p>LGPL v3 text:
<a href="https://www.gnu.org/licenses/lgpl-3.0.html">gnu.org/licenses/lgpl-3.0.html</a><br>
Qt source code:
<a href="https://download.qt.io/official_releases/qt/">download.qt.io/official_releases/qt/</a><br>
PySide6:
<a href="https://doc.qt.io/qtforpython/">doc.qt.io/qtforpython</a></p>

<h3>Other components</h3>
<p><a href="https://matplotlib.org/">matplotlib</a> &mdash; Matplotlib License
(BSD-style)<br>
<a href="https://numpy.org/">NumPy</a> &mdash; BSD 3-Clause<br>
<a href="https://python-pillow.org/">Pillow</a> &mdash; MIT-CMU<br>
CPython &mdash; Python Software Foundation License<br>
<a href="https://pyinstaller.org/">PyInstaller</a> &mdash; GPL v2 with the
bootloader exception</p>
<p style="color:{muted}">Full details, including the obligations that come with
redistributing a build, are in THIRD-PARTY-NOTICES.md alongside the
application.</p>

<h3>This application</h3>
<p>Copyright &copy; 2026 Matthew Wormington &lt;<a href="mailto:m_wormington@hotmail.com">m_wormington@hotmail.com</a>&gt;.<br>
Released under the MIT License. Written with the assistance of generative AI;
see the project README for the disclosure.</p>
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG, APP_NAME)
        self.active_palette = theme.PALETTES[
            self.settings.value("theme", "dark", type=str)]

        self.setWindowTitle(f"{APP_NAME} — a front end for xraylib {core.XRAYLIB_VERSION}")
        self.resize(1500, 950)
        self.setMinimumSize(1050, 680)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self._tab_widgets: list[QWidget] = []
        for factory, label in TAB_ORDER:
            widget = factory()
            if hasattr(widget, "status"):
                widget.status.connect(self._show_status)
            self.tabs.addTab(widget, label)
            self._tab_widgets.append(widget)

        self._build_menu()

        self.lbl_status = QLabel("Ready")
        self.lbl_version = QLabel(
            f"xraylib {core.XRAYLIB_VERSION}   ·   {APP_NAME} {__version__}")
        self.lbl_version.setProperty("role", "subtitle")
        self.statusBar().addWidget(self.lbl_status, 1)
        self.statusBar().addPermanentWidget(self.lbl_version)
        # Connected only now: adding the first tab emits currentChanged, and the
        # handler needs the status bar to exist.
        self.tabs.currentChanged.connect(self._tab_changed)

        self.apply_theme(self.active_palette.name)
        self._restore_geometry()

    # -- chrome ----------------------------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        export = QAction("Export current table…", self)
        export.setShortcut(QKeySequence("Ctrl+E"))
        export.triggered.connect(self._export_current)
        file_menu.addAction(export)

        save_plot = QAction("Save current plot…", self)
        save_plot.setShortcut(QKeySequence("Ctrl+S"))
        save_plot.triggered.connect(self._save_current_plot)
        file_menu.addAction(save_plot)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu("&View")
        self.action_theme = QAction("Use light theme", self)
        self.action_theme.setCheckable(True)
        self.action_theme.setChecked(self.active_palette.name == "light")
        self.action_theme.setShortcut(QKeySequence("Ctrl+T"))
        self.action_theme.toggled.connect(
            lambda light: self.apply_theme("light" if light else "dark"))
        view_menu.addAction(self.action_theme)

        view_menu.addSeparator()
        for index, (_factory, label) in enumerate(TAB_ORDER):
            action = QAction(label, self)
            if index < 9:
                action.setShortcut(QKeySequence(f"Ctrl+{index + 1}"))
            action.triggered.connect(lambda _checked=False, i=index: self.tabs.setCurrentIndex(i))
            view_menu.addAction(action)

        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("About", self)
        about.triggered.connect(self._about)
        help_menu.addAction(about)

    def _show_status(self, message: str) -> None:
        self.lbl_status.setText(message)

    def _tab_changed(self, _index: int) -> None:
        self.lbl_status.setText("Ready")

    # -- actions ---------------------------------------------------------

    def _current_widget(self) -> QWidget:
        return self.tabs.currentWidget()

    def _export_current(self) -> None:
        from .widgets import TablePanel
        panels = self._current_widget().findChildren(TablePanel)
        panels = [p for p in panels if p.isVisible() and p.model.rowCount()]
        if not panels:
            QMessageBox.information(self, "Nothing to export",
                                    "This tab has no table with data in it.")
            return
        panels[0].export_csv()

    def _save_current_plot(self) -> None:
        from .widgets import PlotPanel
        panels = [p for p in self._current_widget().findChildren(PlotPanel) if p.isVisible()]
        if not panels:
            QMessageBox.information(self, "Nothing to save", "This tab has no plot.")
            return
        panels[0].save_image()

    def _about(self) -> None:
        AboutDialog(self).exec()

    # -- theme and geometry ----------------------------------------------

    def apply_theme(self, name: str) -> None:
        palette = theme.PALETTES[name]
        self.active_palette = palette
        QApplication.instance().setStyleSheet(theme.stylesheet(palette))
        theme.apply_matplotlib_style(palette)
        for widget in self._tab_widgets:
            if hasattr(widget, "set_palette"):
                widget.set_palette(palette)
        self.setWindowIcon(_make_icon())
        self.settings.setValue("theme", name)

    def _restore_geometry(self) -> None:
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            screen = QGuiApplication.primaryScreen()
            if screen:
                available = screen.availableGeometry()
                self.resize(min(1500, int(available.width() * 0.92)),
                            min(950, int(available.height() * 0.9)))
                self.move(available.center() - self.rect().center())

    def closeEvent(self, event):  # noqa: N802
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def _self_test(window: "MainWindow") -> int:
    """Exercise every tab once and report. Used to verify packaged builds.

    Triggered by setting ``XRAYEXPLORER_SELFTEST=1``; the app computes each tab
    and exits instead of entering the event loop.
    """
    from .tabs.base import TabBase

    failures = []
    for index in range(window.tabs.count()):
        widget = window.tabs.widget(index)
        label = window.tabs.tabText(index)
        if not isinstance(widget, TabBase):
            continue
        try:
            widget.recompute()
        except Exception as exc:
            failures.append(f"{label}: {type(exc).__name__}: {exc}")

    # Exercise the figure export path too: it is the part most likely to break
    # when the bundle is trimmed (matplotlib's PNG/SVG/PDF writers).
    import tempfile
    from .widgets import PlotPanel
    panels = window.findChildren(PlotPanel)
    if panels:
        with tempfile.TemporaryDirectory() as tmp:
            for suffix in (".png", ".svg", ".pdf"):
                target = os.path.join(tmp, f"selftest{suffix}")
                try:
                    panels[0].figure.savefig(target)
                    if os.path.getsize(target) == 0:
                        failures.append(f"savefig{suffix}: wrote an empty file")
                except Exception as exc:
                    failures.append(f"savefig{suffix}: {type(exc).__name__}: {exc}")

    import xraylib as xrl
    checks = {
        "Fe K edge": (xrl.EdgeEnergy(26, xrl.K_SHELL), 7.112),
        "Cu Ka1": (xrl.LineEnergy(29, xrl.KA1_LINE), 8.0478),
        "H2O mu/rho @10keV": (xrl.CS_Total_CP("H2O", 10.0), 5.3287),
    }
    for name, (got, expected) in checks.items():
        if abs(got - expected) > 1e-3 * max(abs(expected), 1.0):
            failures.append(f"{name}: got {got}, expected ~{expected}")

    for problem in failures:
        print(f"FAIL {problem}", file=sys.stderr)
    if failures:
        return 1
    print(f"self-test OK: {window.tabs.count()} tabs, xraylib {core.XRAYLIB_VERSION}")
    return 0


def main() -> int:
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(_make_icon())

    window = MainWindow()
    if os.environ.get("XRAYEXPLORER_SELFTEST"):
        return _self_test(window)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
