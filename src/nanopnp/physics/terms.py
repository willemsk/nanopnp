"""The terms of each registered model's equations in LaTeX, from sections 4 and 6, for display."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from nanopnp.materials.electrolyte import CONCENTRATION_FLOOR_M

__all__ = [
    "CONDITIONS",
    "EPNP_NS_TERMS",
    "PB_LINEAR_TERMS",
    "PB_TERMS",
    "PNP_NS_TERMS",
    "PNP_TERMS",
    "POISSON_TERMS",
    "SYMBOLS",
    "Symbol",
    "Term",
    "Written",
    "symbols_in",
    "written",
]

PARTS = "<parts>"
"""Where a host equation takes the parts that join it, on the right of its flux or force."""

PARTS_BELOW = "<parts-below>"
"""Where a host equation written in lines takes the parts that join it, on a line of their own."""

LEFT = "<left>"
"""Where a host equation takes the parts that join its left side."""


@dataclass(frozen=True)
class Term:
    """One term of a model's equations as the specification states it and the model assembles it.

    Parameters
    ----------
    clause
        The PHY or NUM clause the term is written from.
    equation
        The term in LaTeX: a whole equation, or, with ``joins``, the part it adds to another.
    switches
        The ``physics:`` switches that must all be true for the term to be assembled; empty
        for a term no switch leaves out.
    correction
        The case leaf whose ``none`` model leaves the term out, or None.
    joins
        The name of the term whose equation this part is written into, or None.
    left
        Whether the part joins its host's left side rather than its right.
    defines
        Definitions in LaTeX, written under the equation the term is part of.
    note
        A sentence written under the equation, its mathematics between ``$`` signs.
    absent
        A symbol, and what every equation and definition writes in its place while the term is
        not in force; the notes keep the symbol.
    """

    name: str
    clause: str
    equation: str
    switches: tuple[str, ...] = ()
    correction: str | None = None
    joins: str | None = None
    left: bool = False
    defines: tuple[str, ...] = ()
    note: str = ""
    absent: tuple[str, str] | None = None


@dataclass(frozen=True)
class Written:
    """One equation of a model as its terms in force write it."""

    term: Term
    equation: str
    defines: tuple[str, ...]
    notes: tuple[str, ...]
    joined: tuple[Term, ...]


def written(terms: Iterable[Term], in_force: Callable[[Term], bool]) -> tuple[Written, ...]:
    """Return each equation a model's terms in force write, the parts that join it written in.

    A part joins its host only while both are in force; a host's slots with no part are removed.
    """
    every = list(terms)
    kept = [term for term in every if in_force(term)]
    swaps = [term.absent for term in every if term.absent is not None and term not in kept]

    def held(text: str) -> str:
        for symbol, instead in swaps:
            # A replacement string would read its backslashes as escapes, so it is escaped.
            text = re.sub(rf"{re.escape(symbol)}(?![A-Za-z^])", instead.replace("\\", "\\\\"), text)
        return text

    def varies(term: Term) -> bool:
        # A term that writes a quantity the model holds constant has nothing to note of it.
        return held(term.equation) == term.equation

    hosts = [term for term in kept if term.joins is None]
    found = []
    for host in hosts:
        parts = [term for term in kept if term.joins == host.name]
        joined_right = [term.equation for term in parts if not term.left]
        # Two parts or more go on a line of their own, where the host is written in lines.
        spaced = r" \\ &\qquad " if len(joined_right) > 1 and "aligned" in host.equation else " "
        right = " ".join(joined_right)
        left = " ".join(term.equation for term in parts if term.left)
        equation = host.equation.replace(PARTS, f"{spaced}{right}" if right else "")
        equation = equation.replace(PARTS_BELOW, rf" \\ &\qquad {right}" if right else "")
        equation = equation.replace(LEFT, f"{left} " if left else "")
        found.append(
            Written(
                term=host,
                equation=held(equation),
                defines=tuple(held(item) for term in (host, *parts) for item in term.defines),
                notes=tuple(term.note for term in (host, *parts) if term.note and varies(term)),
                joined=tuple(parts),
            )
        )
    return tuple(found)


@dataclass(frozen=True)
class Symbol:
    """A symbol the equations use, with its meaning and unit as section 4.1.2 states them."""

    tex: str
    meaning: str
    unit: str


# Section 4.1.2's symbols, and section 4's derived ones, in the order a reader meets them.
SYMBOLS: tuple[Symbol, ...] = (
    Symbol(r"\phi", "electric potential", "V"),
    Symbol(r"\varepsilon_0", "vacuum permittivity", "F m⁻¹"),
    Symbol(r"\varepsilon_r", "relative permittivity", "1"),
    Symbol(r"\varepsilon_{r,f}", "relative permittivity of the electrolyte", "1"),
    Symbol(r"\varepsilon_p", "relative permittivity of the solid the blend goes to", "1"),
    Symbol(r"\chi", "solid fraction of PHY-20's dielectric blend", "1"),
    Symbol(r"\rho_{\mathrm{pore}}", "fixed space charge of the protein", "C m⁻³"),
    Symbol(r"F", "Faraday constant", "C mol⁻¹"),
    Symbol(r"z_i", "valence of ion $i$", "1"),
    Symbol(r"c_i", "concentration of ion $i$", "mol m⁻³"),
    Symbol(r"\langle c \rangle", "average ion concentration", "mol L⁻¹"),
    Symbol(r"d", "distance to the nearest pore wall", "nm"),
    Symbol(r"\mathbf{J}_i", "molar flux of ion $i$", "mol m⁻² s⁻¹"),
    Symbol(r"D_i", "diffusivity of ion $i$", "m² s⁻¹"),
    Symbol(r"\mu_i", "mobility of ion $i$", "m² V⁻¹ s⁻¹"),
    Symbol(r"\beta_i", "steric flux vector of ion $i$", "m⁻¹"),
    Symbol(r"a_i", "steric diameter of ion $i$", "m"),
    Symbol(r"a_0", "steric diameter of water", "m"),
    Symbol(r"N_A", "Avogadro constant", "mol⁻¹"),
    Symbol(r"\mathbf{u}", "fluid velocity", "m s⁻¹"),
    Symbol(r"p", "pressure", "Pa"),
    Symbol(r"\boldsymbol{\sigma}", "stress tensor", "Pa"),
    Symbol(r"\eta", "viscosity", "Pa s"),
    Symbol(r"\varrho", "mass density", "kg m⁻³"),
    Symbol(r"\mathbf{f}", "body force density", "N m⁻³"),
    Symbol(r"\mu_i^{\mathrm{ex}}", "excess chemical potential of ion $i$", "J mol⁻¹"),
    Symbol(r"R", "gas constant", "J mol⁻¹ K⁻¹"),
    Symbol(r"T", "temperature", "K"),
    Symbol(
        r"X", r"a corrected property: $D_i$, $\mu_i$, $\varepsilon_{r,f}$, $\eta$ or $\varrho$", "—"
    ),
    Symbol(
        r"X^0",
        r"the value of $X$ at infinite dilution and far from a wall; a superscript 0 has this "
        "meaning on each symbol",
        "—",
    ),
    Symbol(r"f^c", "concentration correction factor", "1"),
    Symbol(r"f^w", "wall correction factor", "1"),
    Symbol(r"\bar{c}", r"$\langle c \rangle$ in M", "1"),
    Symbol(r"\bar{d}", "$d$ in nm", "1"),
    Symbol(r"\tilde{\phi}", r"potential in thermal voltages, $\phi / V_T$", "1"),
    Symbol(r"V_T", "thermal voltage, $RT/F$", "V"),
    Symbol(r"\lambda_D", "Debye length", "m"),
    Symbol(r"\mathbf{I}", "identity tensor", "1"),
    Symbol(r"\mathbf{n}", "unit normal of a boundary", "1"),
    Symbol(
        r"\mathbf{D}",
        r"electric displacement as PHY-09 writes it, $\varepsilon_0 \varepsilon_r \nabla \phi$",
        "C m⁻²",
    ),
    Symbol(r"\mathbf{D}_s", r"$\mathbf{D}$ on the side of the solid", "C m⁻²"),
    Symbol(r"\mathbf{D}_f", r"$\mathbf{D}$ on the side of the electrolyte", "C m⁻²"),
    Symbol(r"\mathbf{x}", "position, $(r, z)$", "nm"),
    Symbol(r"\Omega", "the whole domain: the electrolyte, the protein and the membrane", "—"),
    Symbol(r"u_r", "radial velocity", "m s⁻¹"),
    Symbol(r"u_z", "axial velocity", "m s⁻¹"),
    Symbol(r"c_0", "concentration of the salt in the bulk", "mol m⁻³"),
    Symbol(r"\sigma_s", "surface charge density on a wall", "C m⁻²"),
    Symbol(r"\zeta", "zeta potential on a wall", "V"),
    Symbol(r"V_{\mathrm{bias}}", "bias on the electrode that is not grounded", "V"),
    Symbol(r"c_{\mathrm{bulk}}", "concentration of each ion in the reservoirs", "mol m⁻³"),
    Symbol(r"c_{\max}", "upper end of the parameter set's fitted concentration range", "mol L⁻¹"),
)


def symbols_in(texts: Iterable[str]) -> tuple[Symbol, ...]:
    """Return the symbols of :data:`SYMBOLS` that LaTeX texts use, in the table's order."""
    joined = " ".join(texts)
    # A symbol is used where its text stands alone: not followed by a letter, so ``\phi`` is
    # not found in ``\phi_x``'s name, and a bare letter only between non-letters.
    return tuple(
        symbol
        for symbol in SYMBOLS
        if re.search(rf"(?<![A-Za-z\\_^]){re.escape(symbol.tex)}(?![A-Za-z])", joined)
    )


_STERIC_MODEL = "electrolyte.corrections.steric.model"
_FLUX = (
    r"\begin{aligned} \nabla \cdot \mathbf{J}_i &= 0, \\ "
    r"\mathbf{J}_i &= -\bigl[{bracket}<parts>\bigr] \end{aligned}"
)
_CORRECTED_BRACKET = (
    r"D_i(\langle c \rangle, d)\, \nabla c_i + z_i\, \mu_i(\langle c \rangle, d)\, c_i \nabla \phi"
)
_SPACE_CHARGE = r"\rho_{\mathrm{pore}}(\mathbf{x}) + F \sum_i z_i c_i"

# Each equation is the one its clause states, in its symbols, as the model assembles it.
_POISSON = Term(
    "Poisson",
    "PHY-03",
    r"-\nabla \cdot \left( \varepsilon_0\, \varepsilon_r(\langle c \rangle, \mathbf{x})\, "
    rf"\nabla \phi \right) = {_SPACE_CHARGE}",
)
# The bracket's coefficients carry their arguments, so a part does not fit beside them.
_NERNST_PLANCK = Term(
    "Nernst–Planck",
    "PHY-04",
    _FLUX.replace("{bracket}", _CORRECTED_BRACKET).replace(PARTS, PARTS_BELOW),
)
_STERIC = Term(
    "Steric flux",
    "PHY-05",
    r"+ D_i(\langle c \rangle, d)\, \beta_i\, c_i",
    correction=_STERIC_MODEL,
    joins="Nernst–Planck",
    defines=(
        r"\beta_i = \frac{a_i^3}{a_0^3}\, \frac{\sum_j N_A a_j^3\, \nabla c_j}"
        r"{1 - \sum_j N_A a_j^3\, c_j}",
    ),
)
_ADVECTION = Term("Advection", "PHY-04", r"- \mathbf{u}\, c_i", ("flow",), joins="Nernst–Planck")
_BODY_FORCE = Term(
    "Body force",
    "PHY-08",
    r"\mathbf{f} = -\left( F \sum_i z_i c_i \right) \nabla \phi<parts>",
    ("flow",),
)
_DIELECTRIC_FORCE = Term(
    "Dielectric-gradient force",
    "PHY-23",
    r"- \tfrac{1}{2}\, \varepsilon_0\, |\nabla \phi|^2\, \nabla \varepsilon_r",
    ("flow", "dielectric_gradient_forces"),
    joins="Body force",
    defines=(
        r"\nabla \varepsilon_r = (1 - \chi)\, \nabla \varepsilon_{r,f} + "
        r"(\varepsilon_p - \varepsilon_{r,f})\, \nabla \chi",
    ),
    note=r"In the electrolyte, $\chi = 0$ unless a solid fraction is supplied.",
)
_DECREMENT = Term(
    "Dielectric decrement",
    "PHY-23",
    r"+ \frac{D_i(\langle c \rangle, d)\, c_i}{R T}\, \nabla \mu_i^{\mathrm{ex}}",
    ("flow", "dielectric_gradient_forces"),
    joins="Nernst–Planck",
    defines=(
        r"\mu_i^{\mathrm{ex}} = -\tfrac{1}{2}\, \varepsilon_0\, |\nabla \phi|^2\, "
        r"(1 - \chi)\, \frac{\partial \varepsilon_{r,f}}{\partial c_i}",
    ),
)
_DEBYE = r"\lambda_D^2 = \frac{\varepsilon_0\, \varepsilon_{r,f}^0\, R T}{2 F^2 c_0}"
_CORRECTIONS_LAW = (
    r"\begin{aligned} X(\langle c \rangle, d) &= X^0\, f^c(\bar{c})\, f^w(\bar{d}), \\ "
    r"\bar{c} &= \frac{\langle c \rangle}{1\,\mathrm{M}}, \qquad "
    r"\bar{d} = \max\!\left(\frac{d}{1\,\mathrm{nm}}, 0\right) \end{aligned}"
)
_EXPONENT = math.floor(math.log10(CONCENTRATION_FLOOR_M))
_MANTISSA = f"{CONCENTRATION_FLOOR_M / 10.0**_EXPONENT:.3g}"
_FLOOR = ("" if _MANTISSA == "1" else rf"{_MANTISSA} \times ") + f"10^{{{_EXPONENT}}}"
_CLAMPS = (
    rf" Each $c_i$ is clamped to $[{_FLOOR}\,\mathrm{{M}}, c_{{\max}}]$ before "
    r"$\langle c \rangle$ is formed. "
    r"$f^w = 1$ for $\varepsilon_{r,f}$ and $\varrho$. A correction with its bulk part off has "
    r"$f^c = 1$, and with its wall part off, $f^w = 1$. A property whose correction is none "
    r"keeps $X = X^0$."
)


def _momentum(viscosity: str) -> Term:
    return Term(
        "Momentum",
        "PHY-07",
        r"<left>\nabla \cdot \boldsymbol{\sigma} = \mathbf{f}",
        ("flow",),
        defines=(
            rf"\boldsymbol{{\sigma}} = p\, \mathbf{{I}} - {viscosity} \left[ \nabla \mathbf{{u}} + "
            r"(\nabla \mathbf{u})^{\top} \right]",
        ),
    )


def _inertia(density: str) -> Term:
    return Term(
        "Inertia",
        "NUM-04",
        rf"{density}\, (\mathbf{{u}} \cdot \nabla) \mathbf{{u}} +",
        ("flow", "inertia"),
        joins="Momentum",
        left=True,
        # With the density held constant the two inertias are one, and nothing is said.
        note=""
        if density == r"\varrho^0"
        else rf"The inertia ${density} (\mathbf{{u}} \cdot \nabla) \mathbf{{u}}$ equals PHY-07's "
        rf"$(\mathbf{{u}} \cdot \nabla)({density} \mathbf{{u}})$ only where "
        rf"$\mathbf{{u}} \cdot \nabla {density} = 0$.",
    )


EPNP_NS_TERMS: tuple[Term, ...] = (
    _POISSON,
    _NERNST_PLANCK,
    _STERIC,
    _ADVECTION,
    _DECREMENT,
    _momentum(r"\eta(\langle c \rangle, d)"),
    _inertia(r"\varrho"),
    Term(
        "Velocity continuity",
        "NUM-04",
        r"\varrho\, \nabla \cdot \mathbf{u} = 0",
        ("flow",),
        note=r"The model does not assemble the density continuity of PHY-07, "
        r"$\mathbf{u} \cdot \nabla \varrho = 0$.",
    ),
    Term(
        "Variable density",
        "NUM-04",
        r"\varrho = \varrho(\langle c \rangle)",
        ("flow", "variable_density"),
        note="The inertia and the continuity use it.",
        absent=(r"\varrho", r"\varrho^0"),
    ),
    _BODY_FORCE,
    _DIELECTRIC_FORCE,
    Term(
        "Corrections",
        "PHY-10",
        _CORRECTIONS_LAW,
        note=r"$X$ is $D_i$, $\mu_i$ and $\varepsilon_{r,f}$; $\eta$ with the flow; $\varrho$ "
        r"with the flow and the variable density." + _CLAMPS,
    ),
)

PNP_NS_TERMS: tuple[Term, ...] = (
    Term(
        "Poisson",
        "PHY-03",
        r"-\nabla \cdot \left( \varepsilon_0\, \varepsilon_r(\mathbf{x})\, \nabla \phi \right) = "
        rf"{_SPACE_CHARGE}",
        note=r"In the electrolyte, $\varepsilon_{r,f} = \varepsilon_{r,f}^0$.",
    ),
    Term(
        "Nernst–Planck",
        "PHY-04",
        _FLUX.replace("{bracket}", r"D_i^0\, \nabla c_i + z_i\, \mu_i^0\, c_i \nabla \phi"),
    ),
    _ADVECTION,
    _momentum(r"\eta^0"),
    _inertia(r"\varrho^0"),
    Term("Velocity continuity", "NUM-04", r"\varrho^0\, \nabla \cdot \mathbf{u} = 0", ("flow",)),
    _BODY_FORCE,
    Term(
        "No corrections",
        "PHY-21",
        r"\beta_i = 0, \qquad f^c = f^w = 1",
        note="The model reads no correction and no steric flux.",
    ),
)

PNP_TERMS: tuple[Term, ...] = (
    _POISSON,
    Term(
        "Nernst–Planck",
        "PHY-04",
        _NERNST_PLANCK.equation,
        note=r"The model solves no flow: $\mathbf{u} \equiv \mathbf{0}$.",
    ),
    _STERIC,
    Term(
        "Corrections",
        "PHY-10",
        _CORRECTIONS_LAW,
        note=r"$X$ is $D_i$, $\mu_i$ and $\varepsilon_{r,f}$." + _CLAMPS,
    ),
)

PB_TERMS: tuple[Term, ...] = (
    Term(
        "Poisson–Boltzmann",
        "PHY-21",
        r"\nabla^2 \tilde{\phi} = \frac{\sinh \tilde{\phi}}{\lambda_D^2}, \qquad "
        r"\tilde{\phi} = \frac{\phi}{V_T}",
        defines=(_DEBYE,),
        note=r"It is solved on all of $\Omega$, for a symmetric salt of unit valence.",
    ),
)

PB_LINEAR_TERMS: tuple[Term, ...] = (
    Term(
        "Linearised Poisson–Boltzmann",
        "PHY-21",
        r"\nabla^2 \tilde{\phi} = \frac{\tilde{\phi}}{\lambda_D^2}, \qquad "
        r"\tilde{\phi} = \frac{\phi}{V_T}",
        defines=(_DEBYE,),
        note=r"It is solved on all of $\Omega$, for a symmetric salt of unit valence.",
    ),
)

POISSON_TERMS: tuple[Term, ...] = (
    Term(
        "Poisson",
        "PHY-21",
        r"-\nabla \cdot \left( \varepsilon_0\, \varepsilon_r(\mathbf{x})\, \nabla \phi \right) = "
        r"\rho_{\mathrm{pore}}(\mathbf{x})",
        note=r"The electrolyte is water with no ions, at $\varepsilon_{r,f}^0$.",
    ),
)

CONDITIONS: dict[str, tuple[str, str]] = {
    "phi = 0": (r"\phi = 0", "ground"),
    "phi = V_bias": (r"\phi = V_{\mathrm{bias}}", "the bias"),
    "n.D = 0, zero charge": (r"\mathbf{n} \cdot \mathbf{D} = 0", "zero charge"),
    "continuity of n.D; n.(D_s - D_f) = sigma_s where a wall charge is set": (
        r"\mathbf{n} \cdot (\mathbf{D}_s - \mathbf{D}_f) = \sigma_s",
        "continuity; $\\sigma_s$ only where a wall charge is set; $\\mathbf{n}$ points from "
        "the solid into the electrolyte",
    ),
    "n.grad phi = 0, natural, unless a ladder rung imposes zeta or sigma_s": (
        r"\mathbf{n} \cdot \nabla \phi = 0",
        "natural, unless a continuation rung sets $\\zeta$ or $\\sigma_s$",
    ),
    "c_i = c_bulk": (r"c_i = c_{\mathrm{bulk}}", "the bulk concentration"),
    "n.J_i = 0, natural": (r"\mathbf{n} \cdot \mathbf{J}_i = 0", "no flux, natural"),
    "u = 0": (r"\mathbf{u} = \mathbf{0}", "no slip"),
    "sigma.n = 0, natural": (
        r"\boldsymbol{\sigma} \cdot \mathbf{n} = \mathbf{0}",
        "no stress, natural",
    ),
    "u_r = 0 essential, u_z natural": (r"u_r = 0", "$u_z$ natural"),
    "natural": ("", "natural"),
}
"""Each boundary condition a registered model states (PHY-09), as LaTeX and its name in words."""
