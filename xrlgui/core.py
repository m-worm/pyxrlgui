"""Thin, GUI-agnostic layer over xraylib.

Everything the interface needs to *compute* lives here: registries of xraylib's
line/shell/transition constants, a :class:`Material` abstraction that treats
elements, chemical formulae, NIST materials and custom mixtures uniformly, and
small ``Table``/``Series`` containers that the table and plot widgets consume.

xraylib raises ``ValueError`` for physically meaningless requests (a K-alpha
line for hydrogen, an M5 edge for carbon).  That is useful, but a GUI that lets
users sweep a whole element range needs those to become gaps rather than
exceptions, so every call goes through :func:`safe` or :func:`sweep`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

import numpy as np
import xraylib as xrl

from . import elements as elem

NAN = float("nan")

#: Conversion constant: wavelength [Å] = KEV2ANGST / energy [keV].
KEV2ANGST = xrl.KEV2ANGST
#: Classical electron radius in cm (xraylib exposes it in meters).
R_E_CM = xrl.R_E * 1e2
AVOGADRO = 6.02214076e23

XRAYLIB_VERSION = f"{xrl.XRAYLIB_MAJOR}.{xrl.XRAYLIB_MINOR}.{xrl.XRAYLIB_MICRO}"


# --------------------------------------------------------------------------
# error-tolerant calling
# --------------------------------------------------------------------------


def safe(fn: Callable, *args, default: float = NAN):
    """Call ``fn(*args)``, returning ``default`` instead of raising.

    xraylib signals "no such line/edge for this element" with ``ValueError``;
    for tables and plots that is a missing cell, not a failure.  It also
    returns a bare ``0.0`` for quantities that exist in the API but not in the
    tables, which is likewise reported as ``default``.
    """
    try:
        value = fn(*args)
    except Exception:
        return default
    if isinstance(value, float) and value == 0.0:
        return default
    return value


def safe_positive(fn: Callable, *args) -> float:
    """Like :func:`safe`, but zero is a legitimate result (rates, yields)."""
    try:
        value = float(fn(*args))
    except Exception:
        return NAN
    return value if math.isfinite(value) else NAN


def sweep(fn: Callable, values: Iterable[float], *args) -> np.ndarray:
    """Evaluate ``fn(value, *args)`` across ``values`` into a float array."""
    out = np.empty(len(values), dtype=float)  # type: ignore[arg-type]
    for i, v in enumerate(values):  # type: ignore[arg-type]
        try:
            out[i] = fn(v, *args)
        except Exception:
            out[i] = NAN
    return out


# --------------------------------------------------------------------------
# constant registries
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LineSpec:
    """One X-ray emission line, identified by its xraylib constant."""

    value: int
    iupac: str          # e.g. "KL3"
    siegbahn: str       # e.g. "Ka1" (may be empty)
    shell: str          # originating hole: "K", "L1", ...

    @property
    def label(self) -> str:
        return f"{self.siegbahn} ({self.iupac})" if self.siegbahn else self.iupac

    @property
    def short(self) -> str:
        return self.siegbahn or self.iupac


# Siegbahn name -> IUPAC name for the lines people actually ask for.
_SIEGBAHN = {
    "KA1": "KL3", "KA2": "KL2", "KA3": "KL1",
    "KB1": "KM3", "KB2": "KN3", "KB3": "KM2", "KB4": "KN5", "KB5": "KM5",
    "LA1": "L3M5", "LA2": "L3M4",
    "LB1": "L2M4", "LB2": "L3N5", "LB3": "L1M3", "LB4": "L1M2",
    "LB5": "L3O45", "LB6": "L3N1", "LB7": "L3O1", "LB9": "L1M5",
    "LB10": "L1M4", "LB15": "L3N4", "LB17": "L2M3",
    "LG1": "L2N4", "LG2": "L1N2", "LG3": "L1N3", "LG4": "L1O3",
    "LG5": "L2N1", "LG6": "L2O4", "LG8": "L2O1",
    "LE": "L2M1", "LL": "L3M1", "LS": "L3M3", "LT": "L3M2",
    "LU": "L3N67", "LV": "L2N6",
    "MA1": "M5N7", "MA2": "M5N6", "MB": "M4N6", "MG": "M3N5",
}

_PRETTY_SIEGBAHN = {
    "KA": "Ka", "KB": "Kb", "LA": "La", "LB": "Lb", "LG": "Lg",
    "MA": "Ma", "MB": "Mb", "MG": "Mg",
}

_IUPAC_RE = re.compile(r"^(K|[LMNOPQ][1-7])([KLMNOPQ][1-7]?)$")
_SHELL_PREFIX_RE = re.compile(r"^(K|[LMNOPQ][1-7])")


def _pretty(siegbahn: str) -> str:
    """``"KA1"`` -> ``"Ka1"``, ``"LL"`` -> ``"Ll"``."""
    for prefix, nice in _PRETTY_SIEGBAHN.items():
        if siegbahn.startswith(prefix):
            return nice + siegbahn[len(prefix):].lower()
    return siegbahn[0] + siegbahn[1:].lower()


def _build_lines() -> list[LineSpec]:
    by_value: dict[int, dict[str, str]] = {}
    for attr in dir(xrl):
        if not attr.endswith("_LINE"):
            continue
        stem = attr[: -len("_LINE")]
        value = getattr(xrl, attr)
        if not isinstance(value, int):
            continue
        entry = by_value.setdefault(value, {"iupac": "", "siegbahn": ""})
        if _IUPAC_RE.match(stem):
            entry["iupac"] = stem
        elif stem in _SIEGBAHN or entry["siegbahn"] == "":
            entry["siegbahn"] = stem

    specs: list[LineSpec] = []
    for value, entry in by_value.items():
        iupac = entry["iupac"]
        sieg = entry["siegbahn"]
        if not iupac and sieg in _SIEGBAHN:
            iupac = _SIEGBAHN[sieg]
        name = iupac or sieg
        if not name:
            continue
        match = _SHELL_PREFIX_RE.match(name)
        shell = match.group(1) if match else name[0]
        specs.append(LineSpec(value, name, _pretty(sieg) if sieg else "", shell))
    # Descending constant value == roughly increasing shell depth; sort so that
    # K lines come first and, within a shell, the strongest lines lead.
    specs.sort(key=lambda s: (-s.value))
    return specs


LINES: list[LineSpec] = _build_lines()
LINES_BY_VALUE: dict[int, LineSpec] = {s.value: s for s in LINES}


def line_spec(value: int) -> LineSpec:
    return LINES_BY_VALUE.get(value, LineSpec(value, f"line {value}", "", "?"))


def _curated(names: Sequence[str]) -> list[LineSpec]:
    out = []
    for n in names:
        value = getattr(xrl, n + "_LINE", None)
        if isinstance(value, int) and value in LINES_BY_VALUE:
            out.append(LINES_BY_VALUE[value])
    return out


#: The line groups offered in the UI, in the order they are presented.
LINE_GROUPS: dict[str, list[LineSpec]] = {
    "K lines": _curated(["KA1", "KA2", "KA3", "KB1", "KB2", "KB3", "KB4", "KB5"]),
    "L lines": _curated([
        "LA1", "LA2", "LB1", "LB2", "LB3", "LB4", "LB5", "LB6", "LB7",
        "LB9", "LB10", "LB15", "LB17", "LG1", "LG2", "LG3", "LG4",
        "LG5", "LG6", "LG8", "LE", "LL", "LS", "LT", "LU", "LV",
    ]),
    "M lines": _curated(["MA1", "MA2", "MB", "MG"]),
}
LINE_GROUPS["All lines"] = LINES


@dataclass(frozen=True)
class ShellSpec:
    value: int
    name: str  # "K", "L1", ...


def _build_shells() -> list[ShellSpec]:
    out = []
    for attr in dir(xrl):
        if attr.endswith("_SHELL"):
            value = getattr(xrl, attr)
            if isinstance(value, int):
                out.append(ShellSpec(value, attr[: -len("_SHELL")]))
    out.sort(key=lambda s: s.value)
    return out


SHELLS: list[ShellSpec] = _build_shells()
SHELLS_BY_VALUE = {s.value: s for s in SHELLS}
#: Shells that carry the data most users want (fluorescence yields, edges).
MAIN_SHELLS = [s for s in SHELLS if s.name in
               ("K", "L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5")]


def shell_name(value: int) -> str:
    spec = SHELLS_BY_VALUE.get(value)
    return spec.name if spec else str(value)


#: Coster-Kronig transitions, ``label -> xraylib constant`` (``FL12_TRANS`` -> ``L12``).
CK_TRANSITIONS: dict[str, int] = {
    attr[1: -len("_TRANS")]: getattr(xrl, attr)
    for attr in sorted(dir(xrl)) if attr.endswith("_TRANS")
}


def _build_augers() -> dict[str, list[tuple[str, int]]]:
    """Auger transitions grouped by the shell holding the initial vacancy."""
    groups: dict[str, list[tuple[str, int]]] = {}
    for attr in dir(xrl):
        if not attr.endswith("_AUGER"):
            continue
        value = getattr(xrl, attr)
        if not isinstance(value, int):
            continue
        stem = attr[: -len("_AUGER")]
        shell = stem.split("_")[0]
        groups.setdefault(shell, []).append((stem.replace("_", "-"), value))
    for items in groups.values():
        items.sort(key=lambda kv: kv[1])
    return groups


AUGER_GROUPS: dict[str, list[tuple[str, int]]] = _build_augers()


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------


@dataclass
class Material:
    """An element, formula, NIST material or arbitrary mixture.

    Cross sections are always evaluated per element and combined by mass
    fraction, which is exactly what xraylib's ``*_CP`` helpers do internally
    but also works for mixtures that have no formula string.
    """

    name: str
    composition: tuple[tuple[int, float], ...]  # (Z, mass fraction), normalized
    density: float | None = None                # g/cm3
    formula: str | None = None
    kind: str = "element"                       # element | formula | nist | mixture
    stoichiometry: tuple[tuple[int, float], ...] = ()  # (Z, atoms per formula unit)
    molar_mass: float | None = None

    # -- constructors ----------------------------------------------------

    @classmethod
    def from_element(cls, z: int) -> "Material":
        sym = elem.symbol(z)
        return cls(
            name=f"{sym} ({z})",
            composition=((z, 1.0),),
            density=safe(xrl.ElementDensity, z, default=None),
            formula=sym,
            kind="element",
            stoichiometry=((z, 1.0),),
            molar_mass=safe(xrl.AtomicWeight, z, default=None),
        )

    @classmethod
    def from_formula(cls, formula: str, density: float | None = None) -> "Material":
        parsed = xrl.CompoundParser(formula)  # raises ValueError on bad input
        comp = tuple(zip(parsed["Elements"], parsed["massFractions"]))
        if density is None and len(comp) == 1:
            density = safe(xrl.ElementDensity, comp[0][0], default=None)
        return cls(
            name=formula,
            composition=comp,
            density=density,
            formula=formula,
            kind="element" if len(comp) == 1 else "formula",
            stoichiometry=tuple(zip(parsed["Elements"], parsed["nAtoms"])),
            molar_mass=parsed["molarMass"],
        )

    @classmethod
    def from_nist(cls, name: str) -> "Material":
        data = xrl.GetCompoundDataNISTByName(name)
        return cls(
            name=data["name"],
            composition=tuple(zip(data["Elements"], data["massFractions"])),
            density=data["density"],
            formula=None,
            kind="nist",
        )

    @classmethod
    def from_mixture(cls, parts: Sequence[tuple["Material", float]],
                     name: str = "Mixture",
                     density: float | None = None) -> "Material":
        """Combine materials weighted by mass fraction (weights are normalized)."""
        total = sum(w for _, w in parts)
        if total <= 0:
            raise ValueError("Mixture weights must sum to a positive number.")
        merged: dict[int, float] = {}
        for mat, weight in parts:
            share = weight / total
            for z, w in mat.composition:
                merged[z] = merged.get(z, 0.0) + share * w
        if density is None:
            # Volume-additive rule; only valid if every component has a density.
            if all(m.density for m, _ in parts):
                inv = sum((w / total) / m.density for m, w in parts)  # type: ignore[operator]
                density = 1.0 / inv if inv > 0 else None
        return cls(
            name=name,
            composition=tuple(sorted(merged.items())),
            density=density,
            kind="mixture",
        )

    # -- derived quantities ---------------------------------------------

    @property
    def is_element(self) -> bool:
        return len(self.composition) == 1

    @property
    def z(self) -> int | None:
        return self.composition[0][0] if self.is_element else None

    @property
    def mean_atomic_mass(self) -> float:
        """Molar mass per average atom, used for barn/atom conversions."""
        acc = 0.0
        for z, w in self.composition:
            a = safe(xrl.AtomicWeight, z)
            if math.isfinite(a) and a > 0:
                acc += w / a
        return 1.0 / acc if acc > 0 else NAN

    @property
    def mean_z(self) -> float:
        """Mass-weighted mean atomic number."""
        return sum(z * w for z, w in self.composition)

    def describe(self) -> str:
        rho = f"{self.density:g} g/cm³" if self.density else "density unset"
        return f"{self.name} — {len(self.composition)} element(s), {rho}"

    # -- cross sections --------------------------------------------------

    def cs(self, kind: str, energy: float) -> float:
        """Mass attenuation coefficient in cm²/g at ``energy`` keV."""
        fn = CS_KINDS[kind].fn
        total = 0.0
        for z, w in self.composition:
            value = safe(fn, z, energy, default=NAN)
            if not math.isfinite(value):
                return NAN
            total += w * value
        return total

    def cs_curve(self, kind: str, energies: np.ndarray) -> np.ndarray:
        fn = CS_KINDS[kind].fn
        out = np.zeros_like(energies, dtype=float)
        for z, w in self.composition:
            out += w * sweep(lambda e, zz=z: fn(zz, e), energies)
        return out

    def convert(self, values: np.ndarray | float, unit: str):
        """Convert cm²/g to the requested display unit."""
        if unit == "cm^2/g":
            return values
        if unit == "1/cm":
            if not self.density:
                return values * NAN
            return values * self.density
        if unit == "barn/atom":
            a = self.mean_atomic_mass
            return values * a / AVOGADRO * 1e24
        raise ValueError(f"Unknown unit {unit!r}")

    # -- optics ----------------------------------------------------------

    def delta_beta(self, energy: float, density: float | None = None):
        """Refractive index decrement ``(delta, beta)`` with ``n = 1 - delta - i*beta``."""
        rho = density if density is not None else self.density
        if not rho:
            return NAN, NAN
        lam_cm = (KEV2ANGST / energy) * 1e-8
        acc = 0.0
        for z, w in self.composition:
            a = safe(xrl.AtomicWeight, z)
            fp = safe_positive(xrl.Fi, z, energy)
            if not (math.isfinite(a) and math.isfinite(fp)):
                return NAN, NAN
            acc += w / a * (z + fp)
        delta = R_E_CM * lam_cm**2 / (2 * math.pi) * rho * AVOGADRO * acc
        mu = self.cs("total", energy) * rho          # 1/cm
        beta = mu * lam_cm / (4 * math.pi)
        return delta, beta


CS_UNITS = ["cm^2/g", "1/cm", "barn/atom"]
CS_UNIT_LABELS = {
    "cm^2/g": "Mass attenuation  μ/ρ  [cm²/g]",
    "1/cm": "Linear attenuation  μ  [1/cm]",
    "barn/atom": "Cross section  σ  [barn/atom]",
}


@dataclass(frozen=True)
class CSKind:
    key: str
    label: str
    fn: Callable[[int, float], float]
    note: str = ""


CS_KINDS: dict[str, CSKind] = {k.key: k for k in [
    CSKind("total", "Total attenuation", xrl.CS_Total),
    CSKind("photo", "Photoelectric absorption", xrl.CS_Photo),
    CSKind("rayl", "Rayleigh (coherent) scattering", xrl.CS_Rayl),
    CSKind("compt", "Compton (incoherent) scattering", xrl.CS_Compt),
    CSKind("total_kissel", "Total attenuation (Kissel)", xrl.CS_Total_Kissel,
           "Uses Kissel's partial photoelectric data."),
    CSKind("photo_kissel", "Photoelectric absorption (Kissel)", xrl.CS_Photo_Total,
           "Uses Kissel's partial photoelectric data."),
    CSKind("energy", "Mass energy-absorption", xrl.CS_Energy),
]}


# --------------------------------------------------------------------------
# fluorescence-line cross sections
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FluorKind:
    key: str
    label: str
    line_fn: Callable[[int, int, float], float]
    shell_fn: Callable[[int, int, float], float]


FLUOR_KINDS: dict[str, FluorKind] = {k.key: k for k in [
    FluorKind("jump", "Jump-factor approximation",
              xrl.CS_FluorLine, xrl.CS_FluorShell),
    FluorKind("kissel", "Kissel, full cascade",
              xrl.CS_FluorLine_Kissel_Cascade, xrl.CS_FluorShell_Kissel_Cascade),
    FluorKind("kissel_rad", "Kissel, radiative cascade only",
              xrl.CS_FluorLine_Kissel_Radiative_Cascade,
              xrl.CS_FluorShell_Kissel_Radiative_Cascade),
    FluorKind("kissel_nonrad", "Kissel, non-radiative cascade only",
              xrl.CS_FluorLine_Kissel_Nonradiative_Cascade,
              xrl.CS_FluorShell_Kissel_Nonradiative_Cascade),
    FluorKind("kissel_nocascade", "Kissel, no cascade",
              xrl.CS_FluorLine_Kissel_no_Cascade,
              xrl.CS_FluorShell_Kissel_no_Cascade),
]}


# --------------------------------------------------------------------------
# result containers
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    fmt: str = "{:.6g}"
    numeric: bool = True

    def render(self, value) -> str:
        if value is None:
            return ""
        if self.numeric:
            try:
                fvalue = float(value)
            except (TypeError, ValueError):
                return str(value)
            if not math.isfinite(fvalue):
                return "—"
            return self.fmt.format(fvalue)
        return str(value)


@dataclass
class Table:
    """A rectangular result set, ready for display and export."""

    columns: list[Column]
    rows: list[tuple] = field(default_factory=list)
    title: str = ""
    note: str = ""

    def __len__(self) -> int:
        return len(self.rows)


@dataclass
class Series:
    """One curve or stick set on a plot."""

    label: str
    x: np.ndarray
    y: np.ndarray
    kind: str = "line"          # line | stick | scatter
    color: str | None = None
    annotations: list[str] | None = None


@dataclass
class PlotSpec:
    """Everything the plot widget needs to draw a figure."""

    series: list[Series] = field(default_factory=list)
    xlabel: str = ""
    ylabel: str = ""
    title: str = ""
    xlog: bool = False
    ylog: bool = False
    legend: bool = True
    polar: bool = False


# --------------------------------------------------------------------------
# energy grids
# --------------------------------------------------------------------------


def energy_grid(emin: float, emax: float, points: int, log: bool) -> np.ndarray:
    emin = max(emin, 1e-3)
    emax = max(emax, emin * 1.000001)
    points = max(2, min(int(points), 20000))
    if log:
        return np.logspace(math.log10(emin), math.log10(emax), points)
    return np.linspace(emin, emax, points)


def wavelength(energy_kev: float) -> float:
    """Å from keV."""
    return KEV2ANGST / energy_kev if energy_kev > 0 else NAN


# --------------------------------------------------------------------------
# convenience lookups used across several tabs
# --------------------------------------------------------------------------


def absorption_edges(z: int) -> list[tuple[str, float]]:
    """``[(shell name, edge energy keV)]`` for every tabulated edge of ``z``."""
    out = []
    for spec in SHELLS:
        energy = safe(xrl.EdgeEnergy, z, spec.value)
        if math.isfinite(energy):
            out.append((spec.name, energy))
    return out


def strongest_lines(z: int, limit: int = 8) -> list[tuple[LineSpec, float, float]]:
    """``[(line, energy, radiative rate)]`` sorted by decreasing rate."""
    found = []
    for group in ("K lines", "L lines", "M lines"):
        for spec in LINE_GROUPS[group]:
            energy = safe(xrl.LineEnergy, z, spec.value)
            rate = safe_positive(xrl.RadRate, z, spec.value)
            if math.isfinite(energy) and math.isfinite(rate) and rate > 0:
                found.append((spec, energy, rate))
    found.sort(key=lambda t: -t[2])
    return found[:limit]


def nist_materials() -> list[str]:
    return list(xrl.GetCompoundDataNISTList())


def radionuclides() -> list[str]:
    return list(xrl.GetRadioNuclideDataList())


def crystals() -> list[str]:
    return list(xrl.Crystal_GetCrystalsList())
