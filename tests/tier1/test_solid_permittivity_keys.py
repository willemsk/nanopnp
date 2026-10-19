from __future__ import annotations

import pytest

from nanopnp.io.case import CaseValidationError
from nanopnp.pipeline.case import loads_case
from nanopnp.pipeline.checks import require_runnable

CASE = """\
schema: nanopnp/case/v0.5
name: keys
inputs:
  profile: {{path: profile.yaml}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{{solids}}}}}
"""


def test_ver03_solid_permittivity_on_a_fluid_domain_is_refused_naming_it() -> None:
    with pytest.raises(CaseValidationError, match="fluid domain 'electrolyte'"):
        require_runnable(loads_case(CASE.format(solids="electrolyte: 80.0")))


def test_ver03_misspelt_solid_permittivity_key_is_refused_with_a_suggestion() -> None:
    with pytest.raises(CaseValidationError, match=r"'protien'.*did you mean 'protein'"):
        require_runnable(loads_case(CASE.format(solids="protien: 20.0")))


def test_ver03_vocabulary_solid_absent_from_the_mesh_stays_allowed() -> None:
    require_runnable(loads_case(CASE.format(solids="protein: 20.0, analyte: 4.0")))


@pytest.mark.parametrize("value", ["-1.0", "0.0", ".nan"])
def test_ver03_non_positive_or_nan_solid_permittivity_fails_load(value: str) -> None:
    with pytest.raises(CaseValidationError):
        loads_case(CASE.format(solids=f"membrane: {value}"))
