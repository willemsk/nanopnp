"""The registry of steric models: the form of the flux ``beta~_i`` (PHY-05, PHY-22)."""

from __future__ import annotations

from nanopnp.physics.nernst_planck import StericForm, borukhov_flux

__all__ = ["register_steric_model", "registered_steric_models", "steric_form"]

OFF = "none"

_REGISTRY: dict[str, StericForm] = {}


def register_steric_model(name: str, form: StericForm) -> None:
    """Register a steric form under a name; a duplicate and the off name ``none`` are refused."""
    if name == OFF:
        raise ValueError(f"{OFF!r} is the off value of the steric correction, not a model")
    if name in _REGISTRY:
        raise ValueError(f"a steric model named {name!r} is already registered")
    _REGISTRY[name] = form


def registered_steric_models() -> tuple[str, ...]:
    """Return the registered steric model names, sorted."""
    return tuple(sorted(_REGISTRY))


def steric_form(name: str) -> StericForm:
    """Return the form registered under a name."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"no steric model {name!r}; the registered models are "
            f"{', '.join(registered_steric_models())}"
        ) from None


register_steric_model("borukhov", borukhov_flux)
