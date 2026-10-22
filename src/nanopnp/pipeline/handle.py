"""A case held for repeated runs with edited values."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from nanopnp.io.case import CaseDocument, FieldValue, dumps_case
from nanopnp.io.case_paths import UnknownCasePathError, case_fields, substitute, value_at
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, loads_case
from nanopnp.pipeline.run import RunResult, run_document


def _path_of(name: str) -> str:
    """Return the dotted case path ``name`` stands for: itself, or the one field it ends."""
    if "." in name:
        return name
    matches = sorted(
        reference.path for reference in case_fields() if reference.path.rsplit(".", 1)[-1] == name
    )
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise UnknownCasePathError(
            f"{name!r} names more than one field: {', '.join(matches)}. Write the dotted path"
        )
    leaves = sorted({reference.path.rsplit(".", 1)[-1] for reference in case_fields()})
    close = difflib.get_close_matches(name, leaves, n=3)
    hint = f" Did you mean {', '.join(map(repr, close))}?" if close else ""
    raise UnknownCasePathError(f"{name!r} is not a field of the case schema.{hint}")


@dataclass(frozen=True)
class Case:
    """A validated case, a store, and the edits to run it with.

    A ``Case`` is immutable: ``with_`` returns an edited copy, and ``run`` runs the case with
    edits that apply to that one run. A field is named by its dotted case-file path
    (``boundary_conditions.bias_V``) or, where one field ends in the name, by that name alone
    (``bias_V``).

    Parameters
    ----------
    document
        The validated case document.
    store
        Where artefacts are cached; the default store when ``None``.
    source
        Where the case was read from, if it was.
    write
        Whether a run writes its run directory.
    """

    document: CaseDocument
    store: Store | None = None
    source: Path | None = None
    write: bool = True

    @classmethod
    def load(
        cls, path: str | Path, *, store: Store | str | Path | None = None, write: bool = True
    ) -> Case:
        """Read a case file; ``store`` may be a directory."""
        return cls(load_case(path), _store(store), Path(path), write)

    @classmethod
    def loads(
        cls, text: str, *, store: Store | str | Path | None = None, write: bool = True
    ) -> Case:
        """Read a case from its text."""
        return cls(loads_case(text), _store(store), None, write)

    def __getitem__(self, name: str) -> FieldValue:
        """Return the value of one field of the case."""
        return value_at(self.document, _path_of(name))

    def with_(self, **edits: FieldValue) -> Case:
        """Return a copy with these fields set; CaseValidationError if one is refused."""
        assignments = {_path_of(name): value for name, value in edits.items()}
        return Case(substitute(self.document, assignments), self.store, self.source, self.write)

    def run(self, *, upto: str | None = None, only: bool = False, **edits: FieldValue) -> RunResult:
        """Run the case with ``edits`` applied; ``upto`` and ``only`` are ``run_document``'s."""
        edited = self.with_(**edits) if edits else self
        return run_document(
            edited.document,
            case_text=dumps_case(edited.document),
            case_path=self.source,
            store=self.store,
            upto=upto,
            only=only,
            write=self.write,
        )


def _store(store: Store | str | Path | None) -> Store | None:
    if store is None or isinstance(store, Store):
        return store
    return Store(store)
