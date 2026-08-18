"""Periodic-table reference data.

xraylib only exposes symbols (up to Z=107), so element names, categories and
periodic-table coordinates live here.  ``COLUMN``/``ROW`` are 1-based grid
positions for the classic 18-column layout, with the lanthanides and actinides
placed on two detached rows below the main block.
"""

from __future__ import annotations

from dataclasses import dataclass

# Category keys drive the color coding of the periodic table widget.
ALKALI = "alkali"
ALKALINE = "alkaline"
TRANSITION = "transition"
POST_TRANSITION = "post-transition"
METALLOID = "metalloid"
NONMETAL = "nonmetal"
HALOGEN = "halogen"
NOBLE = "noble"
LANTHANIDE = "lanthanide"
ACTINIDE = "actinide"

CATEGORY_LABELS = {
    ALKALI: "Alkali metal",
    ALKALINE: "Alkaline earth metal",
    TRANSITION: "Transition metal",
    POST_TRANSITION: "Post-transition metal",
    METALLOID: "Metalloid",
    NONMETAL: "Reactive nonmetal",
    HALOGEN: "Halogen",
    NOBLE: "Noble gas",
    LANTHANIDE: "Lanthanide",
    ACTINIDE: "Actinide",
}


@dataclass(frozen=True)
class Element:
    Z: int
    symbol: str
    name: str
    category: str
    period: int
    group: int  # 0 for lanthanides/actinides, which sit outside the main groups

    @property
    def column(self) -> int:
        """1-based column in the 18-wide display grid."""
        if self.category in (LANTHANIDE, ACTINIDE):
            # 57..71 -> columns 4..18, 89..103 -> columns 4..18
            base = 57 if self.category == LANTHANIDE else 89
            return self.Z - base + 4
        return self.group

    @property
    def row(self) -> int:
        """1-based row in the display grid (rows 9 and 10 hold the f-block)."""
        if self.category == LANTHANIDE:
            return 9
        if self.category == ACTINIDE:
            return 10
        return self.period


# fmt: off
_RAW = [
    (1, "H", "Hydrogen", NONMETAL, 1, 1),
    (2, "He", "Helium", NOBLE, 1, 18),
    (3, "Li", "Lithium", ALKALI, 2, 1),
    (4, "Be", "Beryllium", ALKALINE, 2, 2),
    (5, "B", "Boron", METALLOID, 2, 13),
    (6, "C", "Carbon", NONMETAL, 2, 14),
    (7, "N", "Nitrogen", NONMETAL, 2, 15),
    (8, "O", "Oxygen", NONMETAL, 2, 16),
    (9, "F", "Fluorine", HALOGEN, 2, 17),
    (10, "Ne", "Neon", NOBLE, 2, 18),
    (11, "Na", "Sodium", ALKALI, 3, 1),
    (12, "Mg", "Magnesium", ALKALINE, 3, 2),
    (13, "Al", "Aluminum", POST_TRANSITION, 3, 13),
    (14, "Si", "Silicon", METALLOID, 3, 14),
    (15, "P", "Phosphorus", NONMETAL, 3, 15),
    (16, "S", "Sulfur", NONMETAL, 3, 16),
    (17, "Cl", "Chlorine", HALOGEN, 3, 17),
    (18, "Ar", "Argon", NOBLE, 3, 18),
    (19, "K", "Potassium", ALKALI, 4, 1),
    (20, "Ca", "Calcium", ALKALINE, 4, 2),
    (21, "Sc", "Scandium", TRANSITION, 4, 3),
    (22, "Ti", "Titanium", TRANSITION, 4, 4),
    (23, "V", "Vanadium", TRANSITION, 4, 5),
    (24, "Cr", "Chromium", TRANSITION, 4, 6),
    (25, "Mn", "Manganese", TRANSITION, 4, 7),
    (26, "Fe", "Iron", TRANSITION, 4, 8),
    (27, "Co", "Cobalt", TRANSITION, 4, 9),
    (28, "Ni", "Nickel", TRANSITION, 4, 10),
    (29, "Cu", "Copper", TRANSITION, 4, 11),
    (30, "Zn", "Zinc", TRANSITION, 4, 12),
    (31, "Ga", "Gallium", POST_TRANSITION, 4, 13),
    (32, "Ge", "Germanium", METALLOID, 4, 14),
    (33, "As", "Arsenic", METALLOID, 4, 15),
    (34, "Se", "Selenium", NONMETAL, 4, 16),
    (35, "Br", "Bromine", HALOGEN, 4, 17),
    (36, "Kr", "Krypton", NOBLE, 4, 18),
    (37, "Rb", "Rubidium", ALKALI, 5, 1),
    (38, "Sr", "Strontium", ALKALINE, 5, 2),
    (39, "Y", "Yttrium", TRANSITION, 5, 3),
    (40, "Zr", "Zirconium", TRANSITION, 5, 4),
    (41, "Nb", "Niobium", TRANSITION, 5, 5),
    (42, "Mo", "Molybdenum", TRANSITION, 5, 6),
    (43, "Tc", "Technetium", TRANSITION, 5, 7),
    (44, "Ru", "Ruthenium", TRANSITION, 5, 8),
    (45, "Rh", "Rhodium", TRANSITION, 5, 9),
    (46, "Pd", "Palladium", TRANSITION, 5, 10),
    (47, "Ag", "Silver", TRANSITION, 5, 11),
    (48, "Cd", "Cadmium", TRANSITION, 5, 12),
    (49, "In", "Indium", POST_TRANSITION, 5, 13),
    (50, "Sn", "Tin", POST_TRANSITION, 5, 14),
    (51, "Sb", "Antimony", METALLOID, 5, 15),
    (52, "Te", "Tellurium", METALLOID, 5, 16),
    (53, "I", "Iodine", HALOGEN, 5, 17),
    (54, "Xe", "Xenon", NOBLE, 5, 18),
    (55, "Cs", "Cesium", ALKALI, 6, 1),
    (56, "Ba", "Barium", ALKALINE, 6, 2),
    (57, "La", "Lanthanum", LANTHANIDE, 6, 0),
    (58, "Ce", "Cerium", LANTHANIDE, 6, 0),
    (59, "Pr", "Praseodymium", LANTHANIDE, 6, 0),
    (60, "Nd", "Neodymium", LANTHANIDE, 6, 0),
    (61, "Pm", "Promethium", LANTHANIDE, 6, 0),
    (62, "Sm", "Samarium", LANTHANIDE, 6, 0),
    (63, "Eu", "Europium", LANTHANIDE, 6, 0),
    (64, "Gd", "Gadolinium", LANTHANIDE, 6, 0),
    (65, "Tb", "Terbium", LANTHANIDE, 6, 0),
    (66, "Dy", "Dysprosium", LANTHANIDE, 6, 0),
    (67, "Ho", "Holmium", LANTHANIDE, 6, 0),
    (68, "Er", "Erbium", LANTHANIDE, 6, 0),
    (69, "Tm", "Thulium", LANTHANIDE, 6, 0),
    (70, "Yb", "Ytterbium", LANTHANIDE, 6, 0),
    (71, "Lu", "Lutetium", LANTHANIDE, 6, 0),
    (72, "Hf", "Hafnium", TRANSITION, 6, 4),
    (73, "Ta", "Tantalum", TRANSITION, 6, 5),
    (74, "W", "Tungsten", TRANSITION, 6, 6),
    (75, "Re", "Rhenium", TRANSITION, 6, 7),
    (76, "Os", "Osmium", TRANSITION, 6, 8),
    (77, "Ir", "Iridium", TRANSITION, 6, 9),
    (78, "Pt", "Platinum", TRANSITION, 6, 10),
    (79, "Au", "Gold", TRANSITION, 6, 11),
    (80, "Hg", "Mercury", TRANSITION, 6, 12),
    (81, "Tl", "Thallium", POST_TRANSITION, 6, 13),
    (82, "Pb", "Lead", POST_TRANSITION, 6, 14),
    (83, "Bi", "Bismuth", POST_TRANSITION, 6, 15),
    (84, "Po", "Polonium", POST_TRANSITION, 6, 16),
    (85, "At", "Astatine", HALOGEN, 6, 17),
    (86, "Rn", "Radon", NOBLE, 6, 18),
    (87, "Fr", "Francium", ALKALI, 7, 1),
    (88, "Ra", "Radium", ALKALINE, 7, 2),
    (89, "Ac", "Actinium", ACTINIDE, 7, 0),
    (90, "Th", "Thorium", ACTINIDE, 7, 0),
    (91, "Pa", "Protactinium", ACTINIDE, 7, 0),
    (92, "U", "Uranium", ACTINIDE, 7, 0),
    (93, "Np", "Neptunium", ACTINIDE, 7, 0),
    (94, "Pu", "Plutonium", ACTINIDE, 7, 0),
    (95, "Am", "Americium", ACTINIDE, 7, 0),
    (96, "Cm", "Curium", ACTINIDE, 7, 0),
    (97, "Bk", "Berkelium", ACTINIDE, 7, 0),
    (98, "Cf", "Californium", ACTINIDE, 7, 0),
    (99, "Es", "Einsteinium", ACTINIDE, 7, 0),
    (100, "Fm", "Fermium", ACTINIDE, 7, 0),
    (101, "Md", "Mendelevium", ACTINIDE, 7, 0),
    (102, "No", "Nobelium", ACTINIDE, 7, 0),
    (103, "Lr", "Lawrencium", ACTINIDE, 7, 0),
    (104, "Rf", "Rutherfordium", TRANSITION, 7, 4),
    (105, "Db", "Dubnium", TRANSITION, 7, 5),
    (106, "Sg", "Seaborgium", TRANSITION, 7, 6),
    (107, "Bh", "Bohrium", TRANSITION, 7, 7),
]
# fmt: on

#: Highest atomic number xraylib will map to a symbol.
ZMAX = 107

ELEMENTS: list[Element] = [Element(*row) for row in _RAW]
BY_Z: dict[int, Element] = {e.Z: e for e in ELEMENTS}
BY_SYMBOL: dict[str, Element] = {e.symbol.lower(): e for e in ELEMENTS}


def get(z: int) -> Element | None:
    return BY_Z.get(z)


def symbol(z: int) -> str:
    e = BY_Z.get(z)
    return e.symbol if e else f"Z={z}"


def name(z: int) -> str:
    e = BY_Z.get(z)
    return e.name if e else f"Element {z}"


def label(z: int) -> str:
    """``"Fe (26)"`` — the form used in combo boxes and legends."""
    e = BY_Z.get(z)
    return f"{e.symbol} ({z})" if e else str(z)


def lookup(text: str) -> int | None:
    """Resolve ``"Fe"``, ``"iron"``, ``"26"`` or ``"Fe (26)"`` to an atomic number."""
    text = text.strip()
    if not text:
        return None
    if "(" in text and text.endswith(")"):
        text = text[text.index("(") + 1 : -1].strip()
    if text.isdigit():
        z = int(text)
        return z if z in BY_Z else None
    key = text.lower()
    if key in BY_SYMBOL:
        return BY_SYMBOL[key].Z
    for e in ELEMENTS:
        if e.name.lower() == key:
            return e.Z
    return None
