"""Apply the tier-3 marker to every test in this directory, and share the ensemble's store.

The marker is structural rather than something an author must remember to add:
placement of the file decides its tier, and the CI gate selects on tiers
(SPECIFICATION.md section 7.1). Note that ``pytest_collection_modifyitems`` is a
session hook — it receives every collected item, not only this directory's — so
the path check below is what keeps the tiers apart.

The author's ClyA-AS ensemble costs about 16 minutes to deposit (WP20 plan,
Design §6), and both ``test_density_ensemble.py`` and ``test_val05_ensemble.py``
need stages 1 to 3 of it. ``ensemble_store`` is therefore session-scoped, so the
nightly session deposits it once (WP22 D12); Tier 3 runs serially, so
``--dist loadfile`` does not split the two files across workers.
"""

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
"""The ClyA-AS case: the paper's 50 frames, C12 and the default geometry blocks.

``frames: {count: 50}`` takes the stride floor(98/50) = 1 ending on the last
frame, so DCD frames 48 to 97 (``.knowledge/04`` §1.1).
"""


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if Path(item.path).is_relative_to(_TIER_DIR):
            item.add_marker(pytest.mark.tier3)


@pytest.fixture(scope="session")
def ensemble_store(tmp_path_factory: pytest.TempPathFactory) -> Store:
    """Return one store for the session, so the ensemble's stages 1 to 3 are deposited once."""
    return Store(tmp_path_factory.mktemp("clya-as-store"))


@pytest.fixture(scope="session")
def ensemble_case() -> Callable[..., Path]:
    """Return a writer of the ClyA-AS case into a directory, with an optional ``geometry:`` block.

    Skips, naming the variable, when the archive is not configured.
    """
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
