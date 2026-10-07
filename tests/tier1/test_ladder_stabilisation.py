"""NUM-13 (WP41 D9) — every solve names its stabilisation mode, and nothing defaults it.

Before WP41 :class:`~nanopnp.solve.continuation.LadderResult` returned ``"none"`` and
``{}`` for a model whose provenance carried no mode, the electrostatic models among
them, so "this model has no stabilisable term" and "this record lost its mode" read
the same (REV-26). A model now names its mode, ``none`` where it assembles no
transport term, and the ladder reads the record without a default.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace

import pytest

STABILISATION_KEYS = ("stabilisation", "stabilisation_parameters", "stabilisation_provenance")


@pytest.mark.xfail(strict=True, reason="planned: WP41 D9")
def test_num13_every_registered_model_names_its_stabilisation_mode() -> None:
    """Each model's provenance carries a registered mode, its parameters and their sources."""
    from nanopnp.physics import models
    from nanopnp.physics.stabilisation import create, registered_stabilisations

    for name in models.registered_models():
        provenance = models.create(name).provenance
        assert provenance["stabilisation"] in registered_stabilisations(), name
        assert isinstance(provenance["stabilisation_parameters"], Mapping), name
        assert isinstance(provenance["stabilisation_provenance"], Mapping), name
        if not models.declaration(name).transport:
            # No transport term to stabilise: the mode is ``none``, recorded as such.
            assert provenance["stabilisation"] == "none", name
            assert dict(provenance["stabilisation_parameters"]) == {}, name
            assert dict(provenance["stabilisation_provenance"]) == dict(
                create("none").provenance
            ), name


@pytest.mark.xfail(strict=True, reason="planned: WP41 D9")
@pytest.mark.parametrize("key", STABILISATION_KEYS)
def test_num13_a_ladder_result_refuses_a_model_that_records_no_mode(key: str) -> None:
    """A missing entry is refused naming the model and the key, never defaulted."""
    from nanopnp.solve.continuation import LadderResult

    recorded = {
        "stabilisation": "none",
        "stabilisation_parameters": {},
        "stabilisation_provenance": {"mode": "none", "terms": ""},
    }
    del recorded[key]
    model = SimpleNamespace(name="probe", provenance=recorded)
    result = LadderResult(solution=SimpleNamespace(model=model), rungs=(), mesh={})
    with pytest.raises(ValueError) as raised:
        getattr(result, key)
    assert str(raised.value) == (
        f"model 'probe' records no {key} in its provenance; every model names its "
        "stabilisation mode, that mode's parameters and their provenance, 'none' where it "
        "assembles no transport term (NUM-13, section 5.3.3)"
    )


@pytest.mark.xfail(strict=True, reason="planned: WP41 D9")
@pytest.mark.parametrize("key", STABILISATION_KEYS[1:])
def test_num13_a_ladder_result_refuses_a_mapping_recorded_as_something_else(key: str) -> None:
    """An entry that is not a mapping is refused, not read as empty."""
    from nanopnp.solve.continuation import LadderResult

    recorded: dict[str, object] = {
        "stabilisation": "none",
        "stabilisation_parameters": {},
        "stabilisation_provenance": {"mode": "none", "terms": ""},
    }
    recorded[key] = "C_cw = 1"
    model = SimpleNamespace(name="probe", provenance=recorded)
    result = LadderResult(solution=SimpleNamespace(model=model), rungs=(), mesh={})
    with pytest.raises(ValueError) as raised:
        getattr(result, key)
    assert str(raised.value) == (
        f"model 'probe' records {key} as str, not a mapping (NUM-13, section 5.3.3)"
    )
