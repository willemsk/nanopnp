"""Apply the tier-2 marker to every test in this directory.

The marker is structural rather than something an author must remember to add:
placement of the file decides its tier, and the CI gate selects on tiers
(SPECIFICATION.md section 7.1). Note that ``pytest_collection_modifyitems`` is a
session hook — it receives every collected item, not only this directory's — so
the path check below is what keeps the tiers apart.
"""

from pathlib import Path

import pytest

_TIER_DIR = Path(__file__).parent


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if Path(item.path).is_relative_to(_TIER_DIR):
            item.add_marker(pytest.mark.tier2)
