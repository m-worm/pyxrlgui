"""Color palettes, the Qt stylesheet and the matplotlib style that matches it."""

from __future__ import annotations

from dataclasses import dataclass, asdict

from . import elements as elem


@dataclass(frozen=True)
class Palette:
    name: str
    window: str
    surface: str
    surface_alt: str
    surface_hi: str
    border: str
    border_hi: str
    text: str
    muted: str
    accent: str
    accent_hi: str
    accent_soft: str
    grid: str
    success: str
    warning: str
    danger: str
    shadow: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


DARK = Palette(
    name="dark",
    window="#13151a",
    surface="#1b1e25",
    surface_alt="#22262f",
    surface_hi="#2b303b",
    border="#2e333d",
    border_hi="#3f4653",
    text="#e7eaf0",
    muted="#98a1b2",
    accent="#5aa9ff",
    accent_hi="#8cc4ff",
    accent_soft="rgba(90, 169, 255, 0.16)",
    grid="#2a2f39",
    success="#4ade80",
    warning="#fbbf24",
    danger="#f87171",
    shadow="rgba(0, 0, 0, 0.45)",
)

LIGHT = Palette(
    name="light",
    window="#f2f4f7",
    surface="#ffffff",
    surface_alt="#f7f8fa",
    surface_hi="#e9edf3",
    border="#d8dde5",
    border_hi="#bcc4d0",
    text="#1a1f29",
    muted="#5f6b7e",
    accent="#2563eb",
    accent_hi="#1d4ed8",
    accent_soft="rgba(37, 99, 235, 0.12)",
    grid="#e3e7ee",
    success="#15803d",
    warning="#b45309",
    danger="#b91c1c",
    shadow="rgba(15, 23, 42, 0.12)",
)

PALETTES = {"dark": DARK, "light": LIGHT}

#: Qualitative curve colors, chosen to stay legible on both backgrounds.
CURVE_COLORS = [
    "#4c9aff", "#ff7a59", "#2dd4bf", "#f5c542", "#c084fc",
    "#f472b6", "#84cc16", "#fb923c", "#38bdf8", "#a78bfa",
]

#: Fill colors for the periodic table, keyed by element category.
CATEGORY_COLORS = {
    elem.ALKALI: "#ef6f6c",
    elem.ALKALINE: "#f0a05a",
    elem.TRANSITION: "#5aa9ff",
    elem.POST_TRANSITION: "#7dd3fc",
    elem.METALLOID: "#2dd4bf",
    elem.NONMETAL: "#84cc16",
    elem.HALOGEN: "#facc15",
    elem.NOBLE: "#c084fc",
    elem.LANTHANIDE: "#f472b6",
    elem.ACTINIDE: "#fb923c",
}


STYLESHEET = """
* {{
    font-family: "Segoe UI", "Inter", "SF Pro Text", "Ubuntu", sans-serif;
    font-size: 13px;
}}

QWidget {{
    background-color: {window};
    color: {text};
}}

QMainWindow, QDialog {{ background-color: {window}; }}

QLabel {{ background: transparent; }}
QLabel[role="title"] {{ font-size: 19px; font-weight: 600; }}
QLabel[role="subtitle"] {{ color: {muted}; font-size: 12px; }}
QLabel[role="section"] {{
    color: {muted}; font-size: 11px; font-weight: 700;
    letter-spacing: 0.6px;
    padding-top: 2px;
}}
QLabel[role="metric"] {{ font-size: 19px; font-weight: 600; color: {accent}; }}
QLabel[role="mono"] {{ font-family: "Cascadia Mono", "Consolas", "Menlo", monospace; }}
QLabel[role="error"] {{ color: {danger}; }}

/* ---------------------------------------------------------------- cards */
QFrame[role="card"] {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}
QFrame[role="tile"] {{
    background-color: {surface_alt};
    border: 1px solid {border};
    border-radius: 8px;
}}
QFrame[role="hline"] {{ background: {border}; max-height: 1px; border: none; }}

/* ----------------------------------------------------------------- tabs */
QTabWidget::pane {{
    border: none;
    background: {window};
    top: -1px;
}}
QTabBar {{ qproperty-drawBase: 0; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {muted};
    padding: 9px 16px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 500;
}}
QTabBar::tab:hover {{ color: {text}; background: {surface}; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
QTabBar::tab:selected {{
    color: {accent};
    border-bottom: 2px solid {accent};
    font-weight: 600;
}}

/* -------------------------------------------------------------- buttons */
QPushButton {{
    background-color: {surface_alt};
    border: 1px solid {border_hi};
    border-radius: 6px;
    padding: 6px 14px;
    color: {text};
    font-weight: 500;
}}
QPushButton:hover {{ background-color: {surface_hi}; border-color: {accent}; }}
QPushButton:pressed {{ background-color: {surface}; }}
QPushButton:disabled {{ color: {muted}; border-color: {border}; background: {surface}; }}
QPushButton[role="primary"] {{
    background-color: {accent};
    border: 1px solid {accent};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{ background-color: {accent_hi}; border-color: {accent_hi}; }}
QPushButton[role="ghost"] {{ background: transparent; border-color: {border}; }}
QPushButton[role="ghost"]:hover {{ background: {surface_alt}; }}

QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px;
}}
QToolButton:hover {{ background: {surface_alt}; border-color: {border_hi}; }}
QToolButton:checked {{ background: {accent_soft}; border-color: {accent}; }}

/* --------------------------------------------------------------- inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background-color: {surface_alt};
    border: 1px solid {border_hi};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {accent};
    selection-color: #ffffff;
    color: {text};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {accent};
    background-color: {surface_hi};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {muted}; background: {surface};
}}
QLineEdit[state="invalid"] {{ border: 1px solid {danger}; }}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    border: none;
    width: 18px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {muted};
    margin-right: 6px;
}}
QComboBox::down-arrow:hover {{ border-top-color: {accent}; }}
QComboBox QAbstractItemView {{
    background-color: {surface_alt};
    border: 1px solid {border_hi};
    border-radius: 6px;
    selection-background-color: {accent};
    selection-color: #ffffff;
    outline: none;
    padding: 4px;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    background: transparent; border: none;
    width: 16px; margin-right: 3px;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    background: transparent; border: none;
    width: 16px; margin-right: 3px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none; width: 0; height: 0;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-bottom: 5px solid {muted};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none; width: 0; height: 0;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {muted};
}}
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{ border-bottom-color: {accent}; }}
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{ border-top-color: {accent}; }}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
    border-bottom-color: {border}; border-top-color: {border};
}}

QCheckBox, QRadioButton {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QCheckBox::indicator {{
    border: 1px solid {border_hi}; border-radius: 4px; background: {surface_alt};
}}
QCheckBox::indicator:hover {{ border-color: {accent}; }}
QCheckBox::indicator:checked {{
    background: {accent}; border-color: {accent};
    image: none;
}}
QRadioButton::indicator {{
    border: 1px solid {border_hi}; border-radius: 8px; background: {surface_alt};
}}
QRadioButton::indicator:checked {{ background: {accent}; border: 4px solid {surface_alt}; }}

QGroupBox {{
    border: 1px solid {border};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    background-color: {surface};
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
    color: {muted};
    font-size: 11px;
    font-weight: 700;
}}

QSlider::groove:horizontal {{ height: 4px; background: {surface_hi}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {accent}; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}

/* --------------------------------------------------------------- tables */
QTableView, QTreeView, QListView {{
    background-color: {surface};
    alternate-background-color: {surface_alt};
    border: 1px solid {border};
    border-radius: 8px;
    gridline-color: {grid};
    selection-background-color: {accent_soft};
    selection-color: {text};
    outline: none;
}}
QTableView::item, QTreeView::item, QListView::item {{ padding: 3px 6px; border: none; }}
QTableView::item:selected, QListView::item:selected {{ background: {accent_soft}; color: {text}; }}

QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background-color: {surface_alt};
    color: {muted};
    padding: 6px 8px;
    border: none;
    border-right: 1px solid {border};
    border-bottom: 1px solid {border};
    font-weight: 600;
}}
QHeaderView::section:hover {{ color: {text}; background: {surface_hi}; }}
QTableCornerButton::section {{ background: {surface_alt}; border: none; }}

/* ----------------------------------------------------------- scrollbars */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {border_hi}; border-radius: 5px; min-height: 28px; min-width: 28px;
}}
QScrollBar::handle:hover {{ background: {muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; border: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* --------------------------------------------------------- chrome, misc */
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 8px; }}
QSplitter::handle:vertical {{ height: 8px; }}
QSplitter::handle:hover {{ background: {accent_soft}; }}

QStatusBar {{ background: {surface}; color: {muted}; border-top: 1px solid {border}; }}
QStatusBar::item {{ border: none; }}

QMenuBar {{ background: {window}; border-bottom: 1px solid {border}; }}
QMenuBar::item {{ padding: 6px 11px; background: transparent; border-radius: 5px; }}
QMenuBar::item:selected {{ background: {surface_alt}; }}
QMenu {{
    background: {surface_alt}; border: 1px solid {border_hi};
    border-radius: 8px; padding: 5px;
}}
QMenu::item {{ padding: 6px 22px 6px 14px; border-radius: 5px; }}
QMenu::item:selected {{ background: {accent}; color: #ffffff; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 5px 8px; }}

QToolTip {{
    background-color: {surface_hi};
    color: {text};
    border: 1px solid {border_hi};
    border-radius: 6px;
    padding: 5px 8px;
}}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QProgressBar {{
    border: 1px solid {border}; border-radius: 5px;
    background: {surface_alt}; text-align: center; height: 6px;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
"""


def stylesheet(palette: Palette) -> str:
    return STYLESHEET.format(**palette.as_dict())


def apply_matplotlib_style(palette: Palette) -> None:
    """Point matplotlib's rcParams at the active palette."""
    import matplotlib as mpl
    from cycler import cycler

    mpl.rcParams.update({
        "figure.facecolor": palette.surface,
        "axes.facecolor": palette.surface,
        "savefig.facecolor": palette.surface,
        "savefig.edgecolor": palette.surface,
        "axes.edgecolor": palette.border_hi,
        "axes.labelcolor": palette.text,
        "axes.titlecolor": palette.text,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": palette.grid,
        "grid.linewidth": 0.8,
        "grid.alpha": 0.9,
        "text.color": palette.text,
        "xtick.color": palette.muted,
        "ytick.color": palette.muted,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.facecolor": palette.surface_alt,
        "legend.edgecolor": palette.border,
        "legend.framealpha": 0.95,
        "legend.fontsize": 9,
        "lines.linewidth": 1.9,
        "lines.antialiased": True,
        "font.size": 10,
        "figure.autolayout": False,
        "axes.prop_cycle": cycler(color=CURVE_COLORS),
    })
