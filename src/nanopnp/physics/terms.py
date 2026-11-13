"""The terms of each registered model's equations, written out from sections 4 and 6 for display."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "EPNP_NS_TERMS",
    "PB_LINEAR_TERMS",
    "PB_TERMS",
    "PNP_NS_TERMS",
    "PNP_TERMS",
    "POISSON_TERMS",
    "Term",
]


@dataclass(frozen=True)
class Term:
    """One term of a model's equations as the specification states it and the model assembles it.

    Parameters
    ----------
    clause
        The PHY or NUM clause the term is written from.
    equation
        The term written out in Unicode.
    switches
        The ``physics:`` switches that must all be true for the term to be assembled; empty
        for a term no switch leaves out.
    correction
        The case leaf whose ``none`` model leaves the term out, or None.
    """

    name: str
    clause: str
    equation: str
    switches: tuple[str, ...] = ()
    correction: str | None = None


_STERIC_MODEL = "electrolyte.corrections.steric.model"

# Each equation is the one its clause states, in its symbols, as the model assembles it.
_POISSON = Term("Poisson", "PHY-03", "−∇·(ε₀ ε_r(⟨c⟩, x) ∇φ) = ρ_pore(x) + F Σᵢ zᵢ cᵢ")
_NERNST_PLANCK = Term(
    "Nernst–Planck",
    "PHY-04",
    "∇·Jᵢ = 0,  Jᵢ = −[Dᵢ(⟨c⟩, d) ∇cᵢ + zᵢ μᵢ(⟨c⟩, d) cᵢ ∇φ + …], the bracket gaining the "
    "terms below",
)
_STERIC = Term(
    "Steric flux",
    "PHY-05",
    "the bracket gains Dᵢ βᵢ cᵢ,  βᵢ = (aᵢ³/a₀³) Σⱼ N_A aⱼ³ ∇cⱼ / (1 − Σⱼ N_A aⱼ³ cⱼ)",
    correction=_STERIC_MODEL,
)
_ADVECTION = Term("Advection", "PHY-04", "the bracket gains −u cᵢ", ("flow",))
_BODY_FORCE = Term("Body force", "PHY-08", "f = −(F Σᵢ zᵢ cᵢ) ∇φ", ("flow",))
_DECREMENT = Term(
    "Dielectric decrement",
    "PHY-23",
    "the bracket gains Dᵢ cᵢ ∇μᵢᵉˣ/(RT),  μᵢᵉˣ = −½ ε₀ |∇φ|² ∂ε_r,f/∂cᵢ",
    ("dielectric_gradient_forces",),
)

EPNP_NS_TERMS: tuple[Term, ...] = (
    _POISSON,
    _NERNST_PLANCK,
    _STERIC,
    _ADVECTION,
    Term("Momentum", "PHY-07", "∇·σ = f,  σ = p I − η(⟨c⟩, d) [∇u + (∇u)ᵀ]", ("flow",)),
    Term("Inertia", "NUM-04", "the momentum's left side gains ϱ (u·∇)u", ("flow", "inertia")),
    Term(
        "Velocity continuity",
        "NUM-04",
        "ϱ ∇·u = 0; PHY-07's density continuity u·∇ϱ = 0 is not assembled",
        ("flow",),
    ),
    Term(
        "Variable density",
        "NUM-04",
        "ϱ = ϱ(⟨c⟩) in the inertia and the continuity; ϱ⁰ with the switch off",
        ("flow", "variable_density"),
    ),
    _BODY_FORCE,
    Term(
        "Dielectric-gradient force",
        "PHY-23",
        "f gains −½ ε₀ |∇φ|² ∇ε_r,f(⟨c⟩)",
        ("flow", "dielectric_gradient_forces"),
    ),
    _DECREMENT,
    Term(
        "Corrections",
        "PHY-10",
        "X(⟨c⟩, d) = X⁰ · f^c(c̄) · f^w(d̄) for Dᵢ, μᵢ and ε_r,f, and η and ϱ with the flow, "
        "each whose correction is not none",
    ),
)

PNP_NS_TERMS: tuple[Term, ...] = (
    Term("Poisson", "PHY-03", "−∇·(ε₀ ε_r(x) ∇φ) = ρ_pore(x) + F Σᵢ zᵢ cᵢ,  ε_r,f = ε_r,f⁰"),
    Term(
        "Nernst–Planck",
        "PHY-04",
        "∇·Jᵢ = 0,  Jᵢ = −[Dᵢ⁰ ∇cᵢ + zᵢ μᵢ⁰ cᵢ ∇φ + …], the bracket gaining the terms below",
    ),
    _ADVECTION,
    Term("Momentum", "PHY-07", "∇·σ = f,  σ = p I − η⁰ [∇u + (∇u)ᵀ]", ("flow",)),
    Term("Inertia", "NUM-04", "the momentum's left side gains ϱ⁰ (u·∇)u", ("flow", "inertia")),
    Term("Velocity continuity", "NUM-04", "ϱ⁰ ∇·u = 0", ("flow",)),
    _BODY_FORCE,
    Term("No corrections", "PHY-21", "βᵢ = 0; every factor f^c, f^w is 1"),
)

PNP_TERMS: tuple[Term, ...] = (
    _POISSON,
    Term(
        "Nernst–Planck",
        "PHY-04",
        "∇·Jᵢ = 0,  Jᵢ = −[Dᵢ(⟨c⟩, d) ∇cᵢ + zᵢ μᵢ(⟨c⟩, d) cᵢ ∇φ + …],  u ≡ 0, the bracket "
        "gaining the terms below",
    ),
    _STERIC,
    _DECREMENT,
    Term(
        "Corrections",
        "PHY-10",
        "X(⟨c⟩, d) = X⁰ · f^c(c̄) · f^w(d̄) for Dᵢ, μᵢ and ε_r,f, each whose correction is not none",
    ),
)

PB_TERMS: tuple[Term, ...] = (
    Term(
        "Poisson–Boltzmann",
        "PHY-21",
        "∇²φ̃ = sinh(φ̃) / λ_D²,  φ̃ = φ/V_T, on all of Ω, λ_D at ε_r,f⁰",
    ),
)

PB_LINEAR_TERMS: tuple[Term, ...] = (
    Term(
        "Linearised Poisson–Boltzmann",
        "PHY-21",
        "∇²φ̃ = φ̃ / λ_D²,  φ̃ = φ/V_T, on all of Ω, λ_D at ε_r,f⁰",
    ),
)

POISSON_TERMS: tuple[Term, ...] = (
    Term("Poisson", "PHY-21", "−∇·(ε₀ ε_r(x) ∇φ) = ρ_pore(x),  ion-free water at ε_r,f⁰"),
)
