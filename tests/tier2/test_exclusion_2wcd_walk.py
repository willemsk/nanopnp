"""VER-59 on a real structure: 2WCD's charged walk with the shell and a derived ``chi``.

With ``a`` = 0.25 nm and ``delta`` = 0.15 nm, WP28's charged walk at ``size_scale``
4 runs to stage 12 with every gate passing, and its manifest names both switches
and the mesh's ``exclusion`` material. Split from ``test_exclusion_2wcd.py`` (WP33
D7): only this walk needs the session's protonation, so only this file waits on
it. Stages 1 to 4, the registration and the protonation come from the session's
seeds; the shell gives stage 5 a key of its own.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from nanopnp.io.run import PIPELINE, run_case
from nanopnp.io.store import Store

pytestmark = pytest.mark.extended

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from conftest import Prepared2WCD, Seed2WCD

logger = logging.getLogger(__name__)

OFFSET_NM = 0.25
"""``a``: ``a_Na/2`` of ``willems2020_nacl`` (WP30 D15)."""

DELTA_NM = 0.15
"""``delta``: the middle of PHY-20's 1-2 Angstrom (WP30 D15)."""

STRUCTURE = """\
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
"""

SOLVE_CASE = """\
schema: nanopnp/case/v2
name: 2wcd-shell-solve
{structure}{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
    steric:       {{model: none}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics:
  model: pnp
  flow: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics:
  continuation: none
  mesh: {{size_scale: 4.0}}
{charge}outputs: [current]
"""


@pytest.fixture(scope="module")
def registered(
    prepared_2wcd: Prepared2WCD,
    seeded_2wcd: Seed2WCD,
    seeded_protonated_2wcd: Callable[[Path], Path],
    tmp_path_factory: pytest.TempPathFactory,
):  # type: ignore[no-untyped-def]
    """Return the store, the structure block and the membrane block registering 2WCD."""
    root = tmp_path_factory.mktemp("2wcd-shell-walk")
    store = Store(seeded_protonated_2wcd(root / "store"))
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    return root, store, structure, seeded_2wcd.geometry


def test_ver59_2wcd_with_the_shell_and_a_derived_chi_walks_to_the_report(registered) -> None:  # type: ignore[no-untyped-def]
    """WP28's charged walk with both switches on: every gate, both switches and the material."""
    root, store, structure, geometry = registered
    case = root / "solve.case.yaml"
    charge = f"charge: {{exclusion_offset_nm: {OFFSET_NM}, dielectric_transition_nm: {DELTA_NM}}}\n"
    case.write_text(
        SOLVE_CASE.format(structure=structure, geometry=geometry, charge=charge),
        encoding="utf-8",
    )
    result = run_case(case, store=store, workspace=root / "work")
    assert [record.name for record in result.stages] == list(PIPELINE)
    stage7 = result.artefacts["charge"]
    assert stage7.inputs["region"] == result.artefacts["region"].hash
    assert stage7.parameters["fields"]["eps_r"]["source"] == "derived"  # type: ignore[index]
    record = stage7.summary["eps_r"]
    means = {mean["material"]: mean for mean in record["material_means"]}  # type: ignore[index]
    assert means["exclusion"]["mean"] < 0.5
    assert means["protein"]["mean"] >= 0.9
    assert means["electrolyte"]["mean"] <= 0.1
    manifest = result.manifest
    paths = {deviation.path for deviation in manifest.deviations}
    assert {"charge.exclusion_offset_nm", "charge.dielectric_transition_nm"} <= paths
    sources = {deviation.source for deviation in manifest.contributed_deviations}
    assert "mesh material 'exclusion'" in sources
    assert "inputs.eps_r" not in sources
    assert manifest.charge["eps_r"]["source"] == "derived"  # type: ignore[index]
    logger.info(
        "VER-59 2WCD charged walk with a = %g nm and delta = %g nm at size_scale 4 (%d "
        "elements): chi means %s; currents %s A; stage times %s s",
        OFFSET_NM,
        DELTA_NM,
        result.artefacts["mesh"].summary["elements"],
        {name: round(mean["mean"], 5) for name, mean in means.items()},
        result.quantities["currents_A"],
        {record.name: round(record.seconds, 2) for record in result.stages},
    )
