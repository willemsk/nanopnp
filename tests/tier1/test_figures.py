"""Figures: the registry's classification and the data layer's unit conversions (FR-30)."""

from __future__ import annotations

import importlib

from nanopnp.core.stages import FIGURE_FREE, _catalogue, figure_target, walk_order


def test_figure_classification_both_ways() -> None:
    entries = _catalogue()
    for name in walk_order():
        declared = entries[name].figure is not None
        assert declared != (name in FIGURE_FREE), name
    targets = [entry.figure for entry in entries.values() if entry.figure is not None]
    targets.append(figure_target("nanopnp/sweep/v0.5"))
    assert all(target is not None for target in targets)
    for target in targets:
        module_name, _, attribute = str(target).partition(":")
        assert callable(getattr(importlib.import_module(module_name), attribute)), target
