"""Apply the tier-3 marker and share the ClyA-AS ensemble's store across the session."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, reference_file
from nanopnp.io.store import Store

_TIER_DIR = Path(__file__).parent

ENSEMBLE_TOPOLOGY = reference_file("prod5_clya_as.pdb")
ENSEMBLE_TRAJECTORY = reference_file("prod5_clya_as.dcd")

ENSEMBLE_CASE = """\
schema: nanopnp/case/v0.5
name: {name}
structure:
  source: {{path: {topology}, variant: ClyA-AS}}
  ensemble: {{trajectory: {trajectory}, frames: {{count: 50}}}}
  symmetry: {{point_group: C12}}
{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if Path(item.path).is_relative_to(_TIER_DIR):
            item.add_marker(pytest.mark.tier3)


@pytest.fixture(scope="session")
def ensemble_store(tmp_path_factory: pytest.TempPathFactory) -> Store:
    return Store(tmp_path_factory.mktemp("clya-as-store"))


@pytest.fixture(scope="session")
def ensemble_case() -> Callable[..., Path]:
    if ENSEMBLE_TOPOLOGY is None or ENSEMBLE_TRAJECTORY is None:
        pytest.skip(f"prod5_clya_as.pdb and .dcd are not in ${REFERENCE_DATA_VARIABLE}")

    def write(directory: Path, *, name: str = "clya-as-density", geometry: str = "") -> Path:
        case = directory / f"{name}.case.yaml"
        case.write_text(
            ENSEMBLE_CASE.format(
                name=name,
                topology=ENSEMBLE_TOPOLOGY,
                trajectory=ENSEMBLE_TRAJECTORY,
                geometry=geometry,
            ),
            encoding="utf-8",
        )
        return case

    return write
