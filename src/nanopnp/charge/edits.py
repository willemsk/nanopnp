"""Titratable residue groups and their anchor atoms, read from the PROPKA data file (FR-38)."""

from __future__ import annotations

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nanopnp.core.paths import charge_data_file


class TitratableGroups(BaseModel):
    """The titratable groups PROPKA 3.5.1 defines, by parent residue name."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    schema_id: str = Field(alias="schema")
    source: dict[str, object]
    anchors: dict[str, str]
    groups: dict[str, tuple[str, ...]]

    @classmethod
    def load(cls) -> TitratableGroups:
        """Read the shipped titratable-groups data file."""
        raw = yaml.safe_load(charge_data_file("titratable_groups.yaml").read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    def has_group(self, residue: str) -> bool:
        """Return whether a parent residue name, such as ``ASP``, carries a titratable group."""
        return residue in self.groups
