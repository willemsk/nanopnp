"""A stage of one's own: a Python function keyed by its code and the artefacts it reads."""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Callable, Mapping
from types import CodeType

from nanopnp.core.hashing import Canonicalisable, canonical
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    report,
)
from nanopnp.io.artefact import Artefact, StageInputs

__all__ = ["FunctionStage", "code_digest"]


def _code_bytes(code: CodeType) -> bytes:
    parts = [code.co_code, repr(code.co_names).encode(), repr(code.co_varnames).encode()]
    for constant in code.co_consts:
        parts.append(
            _code_bytes(constant) if isinstance(constant, CodeType) else repr(constant).encode()
        )
    return b"\x00".join(parts)


def code_digest(function: Callable[..., object]) -> str:
    """Return the digest of a function's code and defaults; an edited body is another digest."""
    code = getattr(function, "__code__", None)
    if not isinstance(code, CodeType):
        raise TypeError(f"{function!r} has no code to key a stage by; give a Python function")
    digest = hashlib.sha256(_code_bytes(code))
    digest.update(repr(getattr(function, "__defaults__", None)).encode())
    return digest.hexdigest()


class FunctionStage:
    """A stage that calls a function on the artefacts named by its parameters.

    Parameters
    ----------
    function
        Called with one artefact per parameter, each parameter named for the stage it reads;
        returns a mapping that becomes the artefact's summary.
    name
        The stage's name; the function's name when ``None``.
    number
        The stage's place after the pipeline's own.
    """

    def __init__(
        self,
        function: Callable[..., Mapping[str, Canonicalisable]],
        *,
        name: str | None = None,
        number: int,
    ) -> None:
        self.function = function
        self.name = name if name is not None else function.__name__
        self.number = number
        self.parameters = tuple(inspect.signature(function).parameters)
        self.digest = code_digest(function)

    @property
    def schema(self) -> str:
        """The schema of the artefacts this stage emits."""
        return f"nanopnp/stage/{self.name}/v1"

    def describe(self) -> StageDescription:
        """Return this stage's description."""
        return StageDescription(
            name=self.name,
            number=self.number,
            title=self.name,
            inputs=self.parameters,
            outputs=("the function's mapping",),
            artefact_schema=self.schema,
            takes_workspace=False,
            takes_store=False,
            key_is_artefact=False,
            weight=0.01,
            needs_section=None,
            optional_inputs=(),
        )

    def key(self, inputs: StageInputs) -> Artefact:
        """Return the artefact ``run`` will produce, without its summary."""
        return Artefact(
            schema=self.schema,
            parameters={"code": self.digest},
            inputs={parameter: inputs.require(parameter).hash for parameter in self.parameters},
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> Artefact:
        """Call the function and return its mapping as the artefact's summary."""
        check_cancelled(cancel, self.name)
        report(progress, 0.0, f"calling {self.name}")
        found = self.function(
            **{parameter: inputs.require(parameter) for parameter in self.parameters}
        )
        if not isinstance(found, Mapping):
            raise TypeError(
                f"stage {self.name!r} returned a {type(found).__name__}; a stage returns a "
                "mapping of names to numbers, text, lists and mappings"
            )
        try:
            canonical(dict(found))
        except (TypeError, ValueError) as error:
            raise TypeError(
                f"stage {self.name!r} returned a value that cannot be kept: {error}"
            ) from None
        report(progress, 1.0, f"{self.name} done")
        key = self.key(inputs)
        return Artefact(
            schema=key.schema, parameters=key.parameters, inputs=key.inputs, summary=dict(found)
        )
