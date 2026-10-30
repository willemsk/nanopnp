"""The Session: the one object that runs a case, for the command line, the shells and Python."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.stages import (
    ArtefactHook,
    CancelToken,
    Progress,
    SolveHook,
    StageHook,
    StageOption,
    figure_target,
    registered_stages,
)
from nanopnp.io.store import Store

if TYPE_CHECKING:  # pragma: no cover - annotations only; the run imports them when it needs them
    from nanopnp.api.case import Case
    from nanopnp.api.sweep import Sweep
    from nanopnp.io.case import FieldValue
    from nanopnp.pipeline.run import RunResult

__all__ = ["Session", "StageInfo"]


@dataclass(frozen=True)
class StageInfo:
    """What a stage takes and produces, read without importing the stage."""

    name: str
    number: int
    title: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    schema: str
    figure: bool


class Session:
    """Runs cases into one store.

    Parameters
    ----------
    store
        The artefact store, or the directory of one; the default store when ``None``.
    write
        Whether a run writes its run directory.
    workspace
        Where the file-writing stages put their files; a fresh directory in the store when
        ``None``.
    overwrite_workspace
        Let the stages replace files an earlier run left in ``workspace``.
    """

    def __init__(
        self,
        store: Store | str | Path | None = None,
        *,
        write: bool = True,
        workspace: str | Path | None = None,
        overwrite_workspace: bool = False,
    ) -> None:
        self.store = store if isinstance(store, Store) else Store(store) if store else Store()
        self.write = write
        self.workspace = Path(workspace) if workspace is not None else None
        self.overwrite_workspace = overwrite_workspace

    def run(
        self,
        case: Case,
        *,
        upto: str | None = None,
        only: bool = False,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
        on_stage: StageHook | None = None,
        on_solve: SolveHook | None = None,
        on_artefact: ArtefactHook | None = None,
    ) -> RunResult:
        """Walk the pipeline for ``case`` and return what it produced.

        Parameters
        ----------
        upto
            Stop after this stage; ``None`` walks the whole pipeline.
        only
            Take every upstream payload-writing stage from the store, aborting naming it if
            absent.
        progress
            Called with a monotone fraction in [0, 1] and a message.
        cancel
            Checked before every stage and threaded into each of them.
        on_stage
            Called before each stage with its name and its position in the walk.
        on_solve
            Called with each continuation rung and accepted Newton step of the solve.
        on_artefact
            Called after each stage with its artefact's schema, hash and whether the store held it.

        Raises
        ------
        MissingUpstreamError
            If ``only`` is set and an upstream artefact is not in the store.
        nanopnp.core.stages.Cancelled
            If ``cancel`` turns true; no run directory is written.
        """
        return self._walk(
            case,
            upto=upto,
            only=only,
            progress=progress,
            cancel=cancel,
            on_stage=on_stage,
            on_solve=on_solve,
            on_artefact=on_artefact,
        )

    def _walk(
        self,
        case: Case,
        *,
        upto: str | None = None,
        only: bool = False,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
        on_stage: StageHook | None = None,
        on_solve: SolveHook | None = None,
        on_artefact: ArtefactHook | None = None,
        arguments: Mapping[str, Mapping[str, StageOption]] | None = None,
    ) -> RunResult:
        from nanopnp.pipeline.run import run_document

        return run_document(
            case,
            case_text=case._text if case._text is not None else case.dumps(),
            case_path=case._path,
            base=case._base,
            store=self.store,
            upto=upto,
            only=only,
            arguments=arguments,
            workspace=self.workspace,
            overwrite_workspace=self.overwrite_workspace,
            write=self.write,
            progress=progress,
            cancel=cancel,
            on_stage=on_stage,
            on_solve=on_solve,
            on_artefact=on_artefact,
        )

    def open(self, directory: str | Path) -> RunResult:
        """Open a run directory written by an earlier run, reading its artefacts from the store."""
        from nanopnp.pipeline.run import open_run

        return open_run(directory, store=self.store)

    @property
    def stages(self) -> tuple[StageInfo, ...]:
        """Every stage, in pipeline order."""
        return tuple(
            StageInfo(
                name=description.name,
                number=description.number,
                title=description.title,
                inputs=description.inputs,
                outputs=description.outputs,
                schema=description.artefact_schema,
                figure=figure_target(description.artefact_schema) is not None,
            )
            for description in registered_stages()
        )

    def sweep(
        self,
        case: Case,
        *,
        axis: str,
        values: Sequence[FieldValue],
        origin: int = 0,
        check_meshes: bool = True,
    ) -> Sweep:
        """Plan a sweep of ``case`` over one field into this session's store."""
        from nanopnp.api.sweep import sweep

        return sweep(
            case, session=self, axis=axis, values=values, origin=origin, check_meshes=check_meshes
        )
