"""The keyed walk: every stage's identity for a case, without running a stage."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import NamedTuple

from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.core.stages import Forecastable, NotBuilt, Stage, create, describe
from nanopnp.io.artefact import Artefact, CaseArtefact, StageInputs
from nanopnp.io.resolved import ResolvedCase
from nanopnp.io.store import Store
from nanopnp.pipeline.extension import FunctionStage
from nanopnp.pipeline.run import offered, selected_stages

__all__ = ["FORECAST_SCHEMA", "Identity", "keyed_walk"]

FORECAST_SCHEMA = "nanopnp/forecast/v0.6"


class Identity(NamedTuple):
    """What a forecast knows of one stage: the hash it keys by, and whether a walk builds it."""

    hash: str
    built: bool


class _NotBuiltPayload(Mapping[str, Path]):
    # The payload of an artefact no stage has built: any read of it is a forecast's question.

    def __init__(self, stage: str) -> None:
        self._stage = stage

    def _refuse(self) -> NotBuilt:
        return NotBuilt(self._stage)

    def __getitem__(self, key: str) -> Path:
        raise self._refuse()

    def __contains__(self, key: object) -> bool:
        raise self._refuse()

    def __iter__(self) -> Iterator[str]:
        raise self._refuse()

    def __len__(self) -> int:
        raise self._refuse()


def keyed_walk(
    resolved: ResolvedCase,
    *,
    store: Store,
    stages: Mapping[str, FunctionStage] | None = None,
    planned: set[str],
) -> dict[str, Identity]:
    """Return each stage's identity for ``resolved``, running none of them.

    A stage is built unless the store or an earlier point of the same forecast holds its
    hash. ``planned`` collects the hashes the forecast builds, across points.
    """
    own = stages or {}
    artefacts: dict[str, Artefact] = {}
    identities: dict[str, Identity] = {}
    for name in selected_stages(resolved, None, stages=own):
        description = own[name].describe() if name in own else describe(name)
        stage = own[name] if name in own else _built(name, store)
        inputs = StageInputs(
            resolved=resolved, upstream=offered(name, artefacts, description=description)
        )
        try:
            key = stage.key(inputs)
        except NotBuilt:
            # A stage that forecasts itself names everything its key reads; any other is
            # taken to read its case and every input it declares.
            if isinstance(stage, Forecastable):
                parameters: Mapping[str, Canonicalisable] = stage.forecast_parameters(inputs)
                read: dict[str, str] = {}
            else:
                case = identities.get("case")
                parameters = {"case": case.hash if case else CaseArtefact(resolved.document).hash}
                read = {
                    needed: identities[needed].hash
                    for needed in description.inputs
                    if needed in identities
                }
            digest = content_hash(
                FORECAST_SCHEMA, {"stage": name, "parameters": dict(parameters)}, read
            )
            built = digest not in planned
            planned.add(digest)
            identities[name] = Identity(digest, built)
            artefacts[name] = Artefact(
                schema=description.artefact_schema,
                parameters={"forecast": digest},
                payload=_NotBuiltPayload(name),
            )
            continue
        if description.key_is_artefact:
            held = store.contains(key)
            artefacts[name] = key
        else:
            stored = store.get(key.schema, key.hash)
            held = stored is not None
            artefacts[name] = stored if stored is not None else _standing_in(key, name)
        built = not held and key.hash not in planned
        if not held:
            planned.add(key.hash)
        identities[name] = Identity(key.hash, built)
    return identities


def _built(name: str, store: Store) -> Stage:
    return create(name, store=store) if describe(name).takes_store else create(name)


def _standing_in(key: Artefact, name: str) -> Artefact:
    return Artefact(
        schema=key.schema,
        parameters=key.parameters,
        inputs=key.inputs,
        payload=_NotBuiltPayload(name),
    )
