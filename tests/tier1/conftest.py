"""Apply the tier-1 marker to every test in this directory."""

from pathlib import Path

import pytest

_TIER_DIR = Path(__file__).parent


# A session hook: it sees every collected item, so the path check keeps the tiers apart.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if Path(item.path).is_relative_to(_TIER_DIR):
            item.add_marker(pytest.mark.tier1)
