"""The feature tabs, in the order they appear in the window."""

from .atomic_tab import AtomicDataTab
from .compounds_tab import CompoundsTab
from .cross_sections_tab import CrossSectionsTab
from .crystals_tab import CrystalsTab
from .elements_tab import ElementsTab
from .lines_tab import LinesTab
from .optics_tab import OpticsTab
from .radionuclides_tab import RadionuclidesTab
from .scattering_tab import ScatteringTab

#: ``(class, tab label)`` in display order.
TAB_ORDER = [
    (ElementsTab, "Elements"),
    (CrossSectionsTab, "Cross sections"),
    (LinesTab, "Emission lines"),
    (AtomicDataTab, "Atomic data"),
    (CompoundsTab, "Compounds"),
    (ScatteringTab, "Scattering"),
    (OpticsTab, "Optics"),
    (CrystalsTab, "Crystals"),
    (RadionuclidesTab, "Radionuclides"),
]

__all__ = ["TAB_ORDER", "AtomicDataTab", "CompoundsTab", "CrossSectionsTab",
           "CrystalsTab", "ElementsTab", "LinesTab", "OpticsTab",
           "RadionuclidesTab", "ScatteringTab"]
