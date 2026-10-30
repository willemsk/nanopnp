"""The Session: the one object that runs a case, for the command line, the shells and Python."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable
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
    from nanopnp.api.sweep import SweepResult
    from nanopnp.io.case import CaseDocument, FieldValue
    from nanopnp.pipeline.extension import FunctionStage
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
        self._own: dict[str, FunctionStage] = {}

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
            case_text=case._text if case._text is not None else case.dumps(),
            case_path=case._path,
            base=case._base,
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
        document: CaseDocument,
        *,
        case_text: str,
        case_path: Path | None = None,
        base: Path | None = None,
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
            document,
            case_text=case_text,
            case_path=case_path,
            base=base,
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
            stages=self._own,
        )

    def open(self, directory: str | Path) -> RunResult:
        """Open a run directory written by an earlier run, reading its artefacts from the store."""
        from nanopnp.pipeline.run import open_run

        return open_run(directory, store=self.store)

    @property
    def stages(self) -> tuple[StageInfo, ...]:
        """Every stage, in pipeline order, then the stages of one's own in registration order."""
        built_in = [
            (description, figure_target(description.artefact_schema) is not None)
            for description in registered_stages()
        ]
        own = [(stage.describe(), False) for stage in self._own.values()]
        return tuple(
            StageInfo(
                name=description.name,
                number=description.number,
                title=description.title,
                inputs=description.inputs,
                outputs=description.outputs,
                schema=description.artefact_schema,
                figure=figure,
            )
            for description, figure in (*built_in, *own)
        )

    def register_stage(
        self, function: Callable[..., Mapping[str, Canonicalisable]], *, name: str | None = None
    ) -> str:
        """Add a stage of one's own to this session's walk and return its name.

        The function is called with one artefact for each parameter, each named for the stage it
        reads, and returns a mapping that becomes the stage's artefact. It walks after every
        stage of the pipeline and is keyed by its code and the artefacts it reads, so an edited
        body is another artefact. Registering a name again on this session replaces the stage.

        Raises
        ------
        ValueError
            If the name is a stage of the pipeline, or a parameter names no stage registered
            before it.
        """
        from nanopnp.core.stages import walk_order
        from nanopnp.pipeline.extension import FunctionStage

        label = name if name is not None else function.__name__
        if label in walk_order():
            raise ValueError(
                f"{label!r} is a stage of the pipeline; name the stage of your own differently"
            )
        earlier = list(self._own)
        if label in self._own:
            earlier = earlier[: earlier.index(label)]
        known = {*walk_order(), *earlier}
        number = (
            self._own[label].number
            if label in self._own
            else 1 + max(d.number for d in registered_stages()) + len(self._own)
        )
        stage = FunctionStage(function, name=label, number=number)
        unknown = [parameter for parameter in stage.parameters if parameter not in known]
        if unknown:
            raise ValueError(
                f"stage {label!r} reads {', '.join(map(repr, unknown))}, which is no stage "
                f"registered before it; its parameters are named for the stages it reads: "
                f"{', '.join(sorted(known))}"
            )
        self._own[label] = stage
        return label

    def sweep(
        self,
        case: Case,
        *,
        axis: str,
        values: Sequence[FieldValue],
        origin: int = 0,
        workers: int = 1,
        check_meshes: bool = True,
    ) -> SweepResult:
        """Plan, run and collect a sweep of ``case`` over one field, into this session's store.

        Parameters
        ----------
        axis
            The field swept: a dotted case path, or the leaf name one field ends in.
        values
            The values the field takes, one point each.
        origin
            Index into ``values`` of the point every other point warm-starts towards.
        workers
            Processes the points of a wave are spread over; 1 runs them in this one.
        check_meshes
            Whether to run the mesh gate once per distinct mesh with a wall correction.
        """
        from nanopnp.api.sweep import sweep

        if workers > 1 and self._own:
            raise ValueError(
                f"workers={workers} runs the members in other processes, which do not hold this "
                f"session's stages of its own ({', '.join(self._own)}); run the sweep with "
                "workers=1"
            )
        return sweep(
            case,
            session=self,
            axis=axis,
            values=values,
            origin=origin,
            workers=workers,
            check_meshes=check_meshes,
        )

    def _member(self) -> Session:
        # A sweep member writes its run directory and takes no workspace of this session's, but
        # walks the stages of one's own.
        member = Session(self.store)
        member._own = dict(self._own)
        return member
