"""The ``nanopnp/golden/v1`` archive: a COMSOL export turned into evidence (VAL-03).

Section 7.4 requires the reference solutions to be "stored as compressed arrays
with the generating model archived alongside", and this module is the single
place where a delivered export becomes one. Two formats, deliberately:
``%Grid``/``%Data`` text tables are the **transport** format, which is what the
author's COMSOL already produces and what
:func:`~nanopnp.density.grid.read_grid` already reads — verified against the
delivered 77 MB ``prod5_clya_charge`` table to 4.7e-12 (VAL-15) — and ``.npz``
plus a typed manifest is the **archival** one. The conversion is where the unit,
sign and hash declarations are checked, once, rather than on every nightly run.

**Five refusals, and each of them is a wrong answer we would otherwise print.**

``case_hash`` and ``probe_hash``. A golden compared against a different case, or
against a probe grid edited since the export, is the most expensive kind of wrong
answer: everything runs, every number looks plausible, and nothing else detects
it. Both are asked twice — at ingest, against the delivered tables, and again on
every comparison (:meth:`Golden.check_case`, :meth:`Golden.check_probe`), because
nothing stops a later run being pointed at another probe document or another
case.

``golden_hash``. The digest written with the archive is checked when it is read
back, not only recorded: a ``.npz`` replaced under a manifest that still names
the generating model would carry that model's provenance onto other numbers.

The unit. The expected set is ``V`` [V], ``cpos``/``cneg`` [mol/m^3], ``u``/``w``
[m/s] and ``p`` [Pa] (``.knowledge/09-comsol-reference-settings.md`` sections C.2
and C.10). A ``mol/L`` export is a factor 1000; scaled silently it reads as a
99.9 % discrepancy, which presents as a physics failure and is a units failure.
It is refused rather than converted, because a golden whose unit we had to guess
at is not a golden.

The sign. ``.knowledge/09`` section F records that the **evaluation boundary is
NOT IN REPORT**, so it can only come from the author, and section 6.7's NOTE
fixes our convention: positive current flows trans to cis, referenced to the
grounded cis electrode. A ``trans``-referenced golden is flipped on load and the
flip is *printed in the report*, because a silent sign convention is how a
rectification ratio comes out reciprocal.

The archive is never vendored: it lives under ``$NANOPNP_REFERENCE_DATA`` and a
Tier-3 test whose golden is absent skips (section 7.1 NOTE). Five cases by six
fields by five patches by two refinements is not a repository file.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nanopnp.core.hashing import canonical, content_hash, decode_floats
from nanopnp.density.grid import (
    COMSOL_DATA_HEADER,
    COMSOL_GRID_HEADER,
    COMSOL_LENGTH_SCALE_NM,
    RadialGrid,
    read_grid,
)
from nanopnp.io.case import CaseValidationError, render_problems
from nanopnp.validation.probe import ProbeDocument, ProbePatch, load_probe

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.io.case import ResolvedCase

__all__ = [
    "ARCHIVE_MANIFEST_NAME",
    "ARCHIVE_NAME",
    "CASE_IDENTITY_SCHEMA",
    "DISCRETISATION_KEYS",
    "GOLDEN_SCHEMA",
    "MANIFEST_NAME",
    "MODEL_OPTION_DISCRETISATION_KEYS",
    "PROBE_FIELDS",
    "Golden",
    "GoldenError",
    "GoldenManifest",
    "GoldenQuantities",
    "case_identity",
    "export_golden",
    "field_unit",
    "ingest_golden",
    "load_golden",
    "loads_manifest",
    "table_name",
    "write_comsol_table",
]

GOLDEN_SCHEMA = "nanopnp/golden/v1"
"""Schema identifier every golden manifest declares, and the hash's separator."""

MANIFEST_NAME = "manifest.yaml"
"""The author's declaration, read by :func:`ingest_golden` from the export directory."""

ARCHIVE_NAME = "golden.npz"
"""The archived arrays, written by :func:`ingest_golden` beside the tables."""

ARCHIVE_MANIFEST_NAME = "golden.manifest.json"
"""The validated manifest, canonical JSON, written beside :data:`ARCHIVE_NAME`."""

Refinement = Literal["published", "refined_1"]
"""VAL-04's two levels: the published mesh, and one uniform refinement of it.

Mixing them into one ``Delta_ref`` inverts its meaning, so the level is declared
rather than inferred from a directory name.
"""

GoldenSource = Literal["comsol", "self"]
"""Where a golden came from.

``self`` is one of *our* solutions written in the archive format, which is how
the harness is exercisable before the exports land. Every consumer prints it:
an attribution ladder run against a self-golden tests the machinery and nothing
else, and a report that did not say so would read as a validation result.
"""

SignReference = Literal["cis", "trans"]
"""Which electrode the exported current is referenced to (section 6.7 NOTE)."""

POTENTIAL_UNIT = "V"
CONCENTRATION_UNIT = "mol/m^3"
VELOCITY_UNIT = "m/s"
PRESSURE_UNIT = "Pa"

PROBE_FIELDS: tuple[str, ...] = (
    "potential",
    "concentration",
    "velocity_r",
    "velocity_z",
    "pressure",
)
"""The field kinds a golden may carry.

``concentration`` stands for the per-species fields, whose names are
``c_<species>`` and are known only once the case names its species; the other
four are literal field names. :func:`field_unit` maps either spelling onto its
unit.
"""

CONCENTRATION_PREFIX = "c_"
"""Prefix of a per-species concentration field, as the model names it."""

CASE_IDENTITY_SCHEMA = "nanopnp/golden/case/v1"
"""Domain separator of :func:`case_identity`."""

DISCRETISATION_KEYS: frozenset[str] = frozenset(
    {"stabilisation", "continuation", "newton", "linear_solver"}
)
"""Keys of the solve provenance a golden's ``case_hash`` deliberately leaves out.

A golden answers a **physical case** — a salt, a bias, an electrolyte model, a
set of corrections — and the four rungs of the attribution ladder answer that
same case at four discretisations. Keying ``case_hash`` on the discretisation
would give the ladder four case hashes and one golden, and the gate that exists
to catch a golden compared against the wrong case would instead refuse three
rungs of the right one.

The mesh is absent for the same reason, one level up:
:attr:`~nanopnp.io.case.ResolvedCase.solve_provenance` does not carry it, and
which mesh either implementation used is precisely what section 7.4 is measuring
(VAL-04, RSK-09) rather than something to gate on. ``name`` and ``outputs`` are
already outside the solve provenance, so a sweep member and the frozen case file
it reproduces hash the same.

``model_options`` is **not** here, and must not be: it carries ``flow``,
``variable_density``, ``inertia``, ``dielectric_gradient_forces`` and
``solid_permittivities`` beside the element orders, and those are the physics.
Dropping the whole mapping would let a run with the flow switched off, or with
the dielectric-gradient body force switched on, declare the identity of the
validated case and be compared against its golden — exactly the wrong answer this
hash exists to refuse. Only the discretisation entries *within* it are removed;
see :data:`MODEL_OPTION_DISCRETISATION_KEYS`.
"""

MODEL_OPTION_DISCRETISATION_KEYS: frozenset[str] = frozenset(
    {"order", "velocity_order", "pressure_order", "stabilisation"}
)
"""Entries of ``model_options`` that :func:`case_identity` leaves out.

The four the attribution ladder moves — ``numerics.elements.{phi,c}`` reach
``order``, ``numerics.elements.{u,p}`` reach ``velocity_order`` and
``pressure_order``, and ``numerics.stabilisation`` is restated here beside the
top-level key. Everything else in the mapping is a physics switch and stays in
the hash.
"""

AXIS_TOL_NM = 1e-6
"""Agreement required between an exported table's axes and the patch's own, in nm.

Loose against the 0.005 nm finest spacing and tight against any real mistake: a
hand-entered extent, a patch confused with its neighbour, or an export made
before the probe document was last edited all miss by orders more than this.
The ``probe_hash`` catches the last of those directly; this catches the export
that was made from the right document and pasted into the wrong dialogue.
"""


class GoldenError(ValueError):
    """A golden cannot be ingested, or cannot be trusted once read.

    A ``ValueError`` and IF-02's case class: every message names the file, the
    field and what was missing or wrong, and the fix is a corrected export or a
    corrected manifest, never a retry (QR-12).
    """


class _Strict(BaseModel):
    """Base for every block: unknown keys are rejected, and named in the error."""

    model_config = ConfigDict(extra="forbid")


def field_unit(field: str) -> str:
    """Return the SI unit a golden must declare for one probe field.

    Parameters
    ----------
    field
        ``"potential"``, ``"pressure"``, ``"velocity_r"``, ``"velocity_z"`` or a
        per-species ``"c_<species>"``.

    Returns
    -------
    str
        The one unit this build accepts for that field.

    Raises
    ------
    GoldenError
        If the name is not one the comparison knows. A manifest that declares a
        field nothing samples would export a table nobody reads, which is a
        silent hole in a comparison rather than an extra.
    """
    if field == "potential":
        return POTENTIAL_UNIT
    if field == "pressure":
        return PRESSURE_UNIT
    if field in ("velocity_r", "velocity_z"):
        return VELOCITY_UNIT
    if field.startswith(CONCENTRATION_PREFIX) and len(field) > len(CONCENTRATION_PREFIX):
        return CONCENTRATION_UNIT
    raise GoldenError(
        f"{field!r} is not a field the probe comparison knows. It reads 'potential', 'pressure', "
        "'velocity_r', 'velocity_z' and one 'c_<species>' per species of the case"
    )


def case_identity(resolved: ResolvedCase) -> str:
    """Return the ``case_hash`` a golden for this case must declare.

    Parameters
    ----------
    resolved
        The resolved frozen case, or any run of it at any discretisation.

    Returns
    -------
    str
        Content hash over
        :attr:`~nanopnp.io.case.ResolvedCase.solve_provenance` with
        :data:`DISCRETISATION_KEYS` removed, and with
        :data:`MODEL_OPTION_DISCRETISATION_KEYS` removed from within
        ``model_options`` — see those constants for why each one is left out, and
        for why the rest of ``model_options`` is kept.
    """
    record: dict[str, object] = {
        key: value
        for key, value in resolved.solve_provenance.items()
        if key not in DISCRETISATION_KEYS
    }
    options = record.get("model_options")
    if isinstance(options, Mapping):
        record["model_options"] = {
            key: value
            for key, value in sorted(options.items())
            if key not in MODEL_OPTION_DISCRETISATION_KEYS
        }
    return content_hash(CASE_IDENTITY_SCHEMA, record)


def table_name(field: str, patch: str) -> str:
    """Return the export contract's file name for one field on one patch.

    A COMSOL Grid evaluation takes one tensor-product grid, and the probe grid is
    a union of patches, so there is one table per patch per field — and
    :func:`~nanopnp.density.grid.read_grid` reads exactly one table per file. The
    naming is mechanical so that neither the author nor the ingest has to keep a
    list.
    """
    return f"{field}__{patch}.txt"


class FieldDeclaration(_Strict):
    """What the author declares about one exported field.

    Parameters
    ----------
    expression
        The COMSOL expression evaluated, verbatim — ``V``, ``cpos``, ``u``, ``p``.
        Recorded because it is the only statement of *what* was exported that
        survives the loss of licence access (VAL-03).
    unit
        The unit the export was written in. Checked against
        :func:`field_unit` and refused, never converted.
    """

    expression: str
    unit: str


class GoldenQuantities(_Strict):
    """The scalar QoIs the reference reported for this case (VAL-02, NUM-27).

    Parameters
    ----------
    bias_V
        The applied bias this golden was solved at.
    current_A
        Total ionic current, in the reference's own sign convention;
        :func:`load_golden` converts it to section 6.7's.
    currents_A
        Per species, keyed as the case names them. Needed for the transport
        number; ``None`` where the export did not carry them.
    transport_number, conductance_S, eof_m3_s
        The remaining NUM-27 quantities, or ``None`` where not exported. ``None``
        is reported as *unavailable* rather than skipped, so a comparison that
        covered three quantities cannot read as one that covered four.
    """

    bias_V: float
    current_A: float
    currents_A: dict[str, float] | None = None
    transport_number: float | None = None
    conductance_S: float | None = None
    eof_m3_s: float | None = None

    def summary(self) -> dict[str, object]:
        """Return these quantities as the manifest and the report record them."""
        return {
            "bias_V": self.bias_V,
            "current_A": self.current_A,
            "currents_A": None if self.currents_A is None else dict(self.currents_A),
            "transport_number": self.transport_number,
            "conductance_S": self.conductance_S,
            "eof_m3_s": self.eof_m3_s,
        }


class GoldenManifest(_Strict):
    """The declaration without which an export is not evidence (section 7.4).

    Every field below is required, and the module docstring says what each
    absence would cost. ``extra="forbid"``, so a manifest that misspells one is
    refused naming the key rather than silently defaulting it.
    """

    schema_id: str = Field(alias="schema")
    case: str
    case_hash: str
    probe: str
    probe_hash: str
    refinement: Refinement
    source: GoldenSource = "comsol"
    comsol_version: str
    model_file: str
    export_date: str
    fields: dict[str, FieldDeclaration]
    current_boundary: str
    current_sign_reference: SignReference
    quantities: GoldenQuantities

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _declared_and_not_blank(self) -> GoldenManifest:
        """Reject a blank provenance string, an unknown field or a wrong unit.

        Blank is checked because ``str`` accepts ``""`` and an empty
        ``model_file`` is exactly as useless as an absent one: section 7.4 wants
        the generating model *named*, and a manifest that names nothing cannot
        reconstruct the run (FR-25).
        """
        why = {
            "case_hash": "the WP7 content hash of the frozen case this golden answers; without "
            "it a golden compared against a different case is undetectable",
            "probe_hash": "the content hash of the probe document the export was interpolated "
            "onto; without it an edited probe grid silently moves the sample points",
            "comsol_version": "the version that produced the export (section 7.4 archives the "
            "generating model)",
            "model_file": "the .mph archived beside this golden",
            "export_date": "when the export was taken",
            "current_boundary": "the boundary tds.ntflux_i was evaluated on. It is NOT IN REPORT "
            "(.knowledge/09 section F), so only the author can supply it",
        }
        missing = [name for name in why if not str(getattr(self, name)).strip()]
        if missing:
            listed = "; ".join(f"{name}: {why[name]}" for name in missing)
            raise ValueError(
                f"golden manifest for case {self.case!r} leaves {len(missing)} required "
                f"declaration(s) blank — {listed}"
            )
        if not self.fields:
            raise ValueError(
                f"golden manifest for case {self.case!r} declares no fields, so it archives "
                "nothing VAL-01 can compare"
            )
        if "potential" not in self.fields:
            raise ValueError(
                f"golden manifest for case {self.case!r} declares no 'potential' field. The "
                "potential is solved over the whole of Omega and is the one field every "
                "configuration of the model carries, so a golden without it cannot discharge "
                "VAL-01 at all"
            )
        for name, declaration in sorted(self.fields.items()):
            try:
                expected = field_unit(name)
            except GoldenError as error:
                raise ValueError(str(error)) from None
            if not declaration.expression.strip():
                raise ValueError(
                    f"field {name!r} declares no COMSOL expression; the expression is the only "
                    "record of what was exported that survives the loss of licence access"
                )
            if declaration.unit != expected:
                raise ValueError(
                    f"field {name!r} declares unit {declaration.unit!r} and this build reads "
                    f"{expected!r}. The unit is refused rather than converted: a mol/L export is "
                    "a factor 1000, and scaled silently it reads as a 99.9 % discrepancy — a "
                    "physics failure that is a units failure. Re-export in SI, or correct the "
                    "declaration if the export was already SI"
                )
        return self

    def summary(self) -> dict[str, object]:
        """Return the manifest's record, for the golden's hash and the report."""
        return {
            "schema": self.schema_id,
            "case": self.case,
            "case_hash": self.case_hash,
            "probe": self.probe,
            "probe_hash": self.probe_hash,
            "refinement": self.refinement,
            "source": self.source,
            "comsol_version": self.comsol_version,
            "model_file": self.model_file,
            "export_date": self.export_date,
            "fields": {
                name: {"expression": entry.expression, "unit": entry.unit}
                for name, entry in sorted(self.fields.items())
            },
            "current_boundary": self.current_boundary,
            "current_sign_reference": self.current_sign_reference,
            "quantities": self.quantities.summary(),
        }


def loads_manifest(text: str, *, source: str = "<string>") -> GoldenManifest:
    """Validate a golden manifest from YAML text.

    Raises
    ------
    CaseValidationError
        If the schema string is wrong or the document does not validate, as for
        every other IF-03 configuration document. The schema is checked first so
        a manifest written to a future schema fails naming the schema it claims.
    """
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise CaseValidationError(f"{source} is not valid YAML: {error}") from None
    if not isinstance(parsed, dict):
        found = type(parsed).__name__
        raise CaseValidationError(
            f"{source} holds a {found} at the top level, not a golden manifest"
        )
    declared = parsed.get("schema")
    if declared != GOLDEN_SCHEMA:
        raise CaseValidationError(
            f"{source} declares schema {declared!r}; this build reads {GOLDEN_SCHEMA!r}"
        )
    try:
        return GoldenManifest.model_validate(parsed)
    except ValidationError as error:
        raise CaseValidationError(render_problems(source, error), error) from None


@dataclass(frozen=True)
class Golden:
    """One archived reference solution, on the probe grid, in our own conventions.

    Parameters
    ----------
    manifest
        The validated declaration, as archived.
    values
        Field name to a ``(n,)`` array in the probe document's flattening order.
        ``NaN`` where the reference had no value, which is the statement the mask
        agreement of :mod:`nanopnp.validation.compare` is checked against.
    quantities
        The QoIs, converted to section 6.7's sign convention.
    current_sign_flipped
        Whether that conversion negated anything. Carried, not discarded: a
        silent sign convention is how a rectification ratio comes out reciprocal,
        so every report prints this.
    hash
        Content hash over the manifest and every array.
    """

    manifest: GoldenManifest
    values: Mapping[str, np.ndarray]
    quantities: GoldenQuantities
    current_sign_flipped: bool
    hash: str

    @property
    def source(self) -> GoldenSource:
        """Where this golden came from; ``"self"`` means it tests the machinery."""
        return self.manifest.source

    def defined(self, field: str) -> np.ndarray:
        """Return the boolean mask of probe points this golden carries a value at.

        Raises
        ------
        GoldenError
            If the field is not archived here; the message lists the ones that
            are, because "absent" and "everywhere NaN" are different facts.
        """
        import numpy as np

        array = self.values.get(field)
        if array is None:
            listed = ", ".join(repr(name) for name in sorted(self.values)) or "nothing"
            raise GoldenError(
                f"golden for case {self.manifest.case!r} carries no field {field!r}; it carries "
                f"{listed}"
            )
        return ~np.isnan(array)

    def unavailable(self, expected: Sequence[str]) -> tuple[str, ...]:
        """Return the expected fields this golden does not carry, sorted.

        Reported rather than skipped: the open question of whether the reference
        model exports ``p`` at all is answered at export time, and a comparison
        that quietly covered four fields instead of five would answer it wrongly.
        """
        return tuple(sorted(set(expected) - set(self.values)))

    def check_case(self, case_hash: str) -> None:
        """Refuse a golden that answers a different case.

        Raises
        ------
        GoldenError
            Naming both hashes. Nothing else detects this: every field is the
            right shape, every norm is finite, and the answer is wrong.
        """
        if self.manifest.case_hash != case_hash:
            raise GoldenError(
                f"golden for case {self.manifest.case!r} declares case_hash "
                f"{self.manifest.case_hash} and this run's case hashes to {case_hash}. The "
                "golden answers a different case; nothing downstream would notice"
            )

    def check_probe(self, document: ProbeDocument) -> None:
        """Refuse a golden exported onto a different set of sample points.

        The counterpart of :meth:`check_case`, and asked at *comparison* time
        rather than only at ingest: :func:`ingest_golden` checks the hash of the
        document the tables were read against, and nothing else stops a later
        ``compare`` or ``report`` being pointed at another probe file. Every value
        would then be attributed to a coordinate it was not taken at, while every
        array kept its shape.

        Raises
        ------
        GoldenError
            Naming both hashes and both grid names.
        """
        if self.manifest.probe_hash != document.hash:
            raise GoldenError(
                f"golden for case {self.manifest.case!r} was exported onto probe grid "
                f"{self.manifest.probe!r} ({self.manifest.probe_hash}) and this comparison is "
                f"taken on {document.name!r} ({document.hash}). The two name different sample "
                "points, so every value would be compared at a coordinate it was not taken at"
            )

    def summary(self) -> dict[str, object]:
        """Return this golden's record for the attribution report (FR-25)."""
        return {
            "hash": self.hash,
            "golden_source": self.source,
            "manifest": self.manifest.summary(),
            "current_sign_flipped": self.current_sign_flipped,
            "quantities_section_6_7": self.quantities.summary(),
            "fields": sorted(self.values),
        }


def write_comsol_table(grid: RadialGrid, path: str | Path) -> Path:
    """Write one ``%Grid``/``%Data`` table, the transport format's only writer.

    :func:`~nanopnp.density.grid.write_grid` refuses this format deliberately — a
    round-tripped copy of the reference model's own input would be
    indistinguishable from it — and that reasoning does not reach here, because
    everything this writes is a *self*-golden, which carries ``source: self``
    through the manifest, the archive and every report that consumes one.

    Parameters
    ----------
    grid
        The samples, in nm coordinates and SI values.
    path
        Destination; parent directories are created.

    Returns
    -------
    Path
        The file written.

    Notes
    -----
    ``%.17g`` throughout: ``float64`` round-trips exactly through 17 significant
    decimal digits, which is what makes the Tier-2 self-golden round trip assert
    ``0`` rather than a tolerance.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [COMSOL_GRID_HEADER]
    for axis in (grid.r_nm, grid.z_nm):
        lines.append(" ".join(f"{value / COMSOL_LENGTH_SCALE_NM:.17g}" for value in axis))
    lines.append(COMSOL_DATA_HEADER)
    # One row per z sample, one value per r sample: the [i_z, i_r] order the
    # container already holds and the reader already expects.
    lines.extend(" ".join(f"{value:.17g}" for value in row) for row in grid.values)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def ingest_golden(
    directory: str | Path,
    *,
    probe: ProbeDocument | str | Path,
    destination: str | Path | None = None,
) -> Path:
    """Turn a directory of exported tables into the archived ``.npz`` and manifest.

    Parameters
    ----------
    directory
        Holds :data:`MANIFEST_NAME` and one table per field per patch, named by
        :func:`table_name`.
    probe
        The probe document, or a path to it. Its hash is checked against the
        manifest's ``probe_hash``.
    destination
        Where to write :data:`ARCHIVE_NAME` and :data:`ARCHIVE_MANIFEST_NAME`;
        ``directory`` by default, so the archive sits beside the raw tables and
        the ``.mph`` as section 7.4 requires.

    Returns
    -------
    Path
        The ``.npz`` written.

    Raises
    ------
    GoldenError
        If the manifest's ``probe_hash`` is not this probe document's, if a
        declared table is absent, or if a table's axes are not the patch's. Each
        message names the field, the patch and the file.
    CaseValidationError
        If the manifest does not validate; see :func:`loads_manifest`.
    """
    import numpy as np

    source = Path(directory)
    manifest_path = source / MANIFEST_NAME
    if not manifest_path.is_file():
        raise GoldenError(
            f"{source} carries no {MANIFEST_NAME}. An export without its declaration is a pile of "
            "numbers: section 7.4 archives the generating model alongside, and the manifest is "
            "what names it"
        )
    manifest = loads_manifest(manifest_path.read_text(encoding="utf-8"), source=str(manifest_path))
    document = probe if isinstance(probe, ProbeDocument) else load_probe(probe)
    _check_probe(manifest, document, manifest_path)

    values: dict[str, np.ndarray] = {}
    for field in sorted(manifest.fields):
        blocks = [
            _read_patch(source / table_name(field, patch.name), patch, field)
            for patch in document.patches
        ]
        values[field] = np.concatenate(blocks)
    return _write_archive(manifest, values, Path(destination) if destination else source)


def export_golden(
    values: Mapping[str, np.ndarray],
    manifest: GoldenManifest,
    destination: str | Path,
    *,
    tables: ProbeDocument | None = None,
) -> Path:
    """Write a golden from arrays we already hold: the self-golden path.

    The harness has to be exercisable before the COMSOL exports land — "which
    tests the machinery and nothing else, and the report says so" — so one of our
    own converged solutions, sampled on the probe grid, is written in exactly the
    archive format a delivered export ends up in. The manifest carries
    ``source: self`` and every consumer prints it.

    Parameters
    ----------
    values
        Field name to a ``(n,)`` array in the probe document's flattening order.
    manifest
        The declaration, already validated. Its ``source`` must be ``"self"``.
    destination
        Directory to write into.
    tables
        When given, the ``%Grid`` transport tables are written beside the
        archive, one per field per patch. That is what lets the Tier-2 round trip
        exercise the *reader* rather than only the container.

    Returns
    -------
    Path
        The ``.npz`` written.

    Raises
    ------
    GoldenError
        If ``manifest.source`` is not ``"self"``. A COMSOL golden is produced by
        :func:`ingest_golden` from delivered tables and never assembled here:
        one path that writes a ``source: comsol`` archive from arrays in memory
        is one path by which a self-golden could be relabelled as evidence.

        Also if ``tables`` is not the document the manifest's ``probe_hash``
        names, or if an array is not that document's length. :func:`ingest_golden`
        gates both on the delivered side and this path must not be the looser of
        the two: an archive declaring a probe grid it was not sampled on is the
        same undetectable wrong answer whichever writer produced it.
    """
    import numpy as np

    if manifest.source != "self":
        raise GoldenError(
            f"export_golden writes self-goldens and this manifest declares source "
            f"{manifest.source!r}. A COMSOL golden comes from ingest_golden against delivered "
            "tables, so that the unit, sign and hash declarations are checked against what was "
            "actually exported"
        )
    target = Path(destination)
    if tables is not None:
        _check_probe(manifest, tables, target / ARCHIVE_MANIFEST_NAME)
        for field, array in sorted(values.items()):
            length = int(np.asarray(array).size)
            if length != tables.count:
                raise GoldenError(
                    f"field {field!r} carries {length} values and probe grid {tables.name!r} has "
                    f"{tables.count} points. The arrays are written patch by patch in the "
                    "document's flattening order, so a length that is not the document's would "
                    "split the blocks at the wrong place"
                )
        offset = 0
        for patch in tables.patches:
            block = slice(offset, offset + patch.count)
            offset += patch.count
            r_axis, z_axis = patch.axes_nm()
            for field, array in sorted(values.items()):
                grid = RadialGrid.from_axes(
                    r_axis, z_axis, np.asarray(array)[block].reshape(patch.n_z, patch.n_r)
                )
                write_comsol_table(grid, target / table_name(field, patch.name))
    return _write_archive(manifest, values, target)


def load_golden(path: str | Path) -> Golden:
    """Read an archived golden and convert its currents to section 6.7's sign.

    Parameters
    ----------
    path
        The ``.npz``, or the directory holding it.

    Returns
    -------
    Golden
        With :attr:`~Golden.current_sign_flipped` set where the archive declared
        ``trans`` and the currents were negated.

    Raises
    ------
    GoldenError
        If the archive or its manifest is absent, if the manifest and the arrays
        disagree about which fields are present, or if the pair does not hash to
        the ``golden_hash`` :func:`ingest_golden` recorded — each of which means
        one of the two files was replaced on its own.
    """
    import numpy as np

    archive, manifest_path = _archive_paths(Path(path))
    manifest, recorded = _read_archive_manifest(manifest_path)
    with np.load(archive, allow_pickle=False) as loaded:
        values = {name: np.asarray(loaded[name], dtype=np.float64) for name in loaded.files}
    if sorted(values) != sorted(manifest.fields):
        raise GoldenError(
            f"{archive} holds fields {sorted(values)} and {manifest_path.name} declares "
            f"{sorted(manifest.fields)}. The two files are written together by ingest_golden, so "
            "a disagreement means one of them was replaced on its own"
        )
    digest = _golden_hash(manifest, values)
    if recorded is not None and recorded != digest:
        raise GoldenError(
            f"{archive} and {manifest_path.name} hash to {digest} and the manifest records "
            f"{recorded}. The two are written together by ingest_golden over the same bytes, so "
            "a disagreement means the arrays or the declaration changed after the archive was "
            "made — and every number compared against it would be attributed to the provenance "
            "the manifest still states"
        )
    flipped = manifest.current_sign_reference == "trans"
    return Golden(
        manifest=manifest,
        values=values,
        quantities=_referenced_to_cis(manifest.quantities) if flipped else manifest.quantities,
        current_sign_flipped=flipped,
        hash=digest,
    )


def _referenced_to_cis(quantities: GoldenQuantities) -> GoldenQuantities:
    """Return ``quantities`` negated onto section 6.7's convention.

    Section 6.7's NOTE references the current to the grounded *cis* electrode:
    with ``psi = 1`` on cis, the indicator integral is the flux out through the
    cis cap, positive current flows trans to cis, and an uncharged ohmic pore has
    ``G > 0`` at either sign of the bias. A ``trans``-referenced export carries
    the opposite outward normal and negates every one of those, so the current,
    the per-species currents, the conductance and the electro-osmotic flow rate
    all flip — they are the same ``psi`` integral with the same normal.

    The transport number does not: ``t+ = I+/(I+ + I-)`` is a ratio of two
    quantities that flip together, so it is invariant, and negating it would be
    the bug this function exists to prevent.
    """
    return GoldenQuantities(
        bias_V=quantities.bias_V,
        current_A=-quantities.current_A,
        currents_A=(
            None
            if quantities.currents_A is None
            else {name: -value for name, value in quantities.currents_A.items()}
        ),
        transport_number=quantities.transport_number,
        conductance_S=(None if quantities.conductance_S is None else -quantities.conductance_S),
        eof_m3_s=None if quantities.eof_m3_s is None else -quantities.eof_m3_s,
    )


def _check_probe(manifest: GoldenManifest, document: ProbeDocument, source: Path) -> None:
    """Refuse a manifest whose ``probe_hash`` is not this probe document's."""
    if manifest.probe_hash != document.hash:
        raise GoldenError(
            f"{source} declares probe_hash {manifest.probe_hash} for probe {manifest.probe!r}, "
            f"and probe grid {document.name!r} hashes to {document.hash}. The export was "
            "interpolated onto a different set of points; comparing against it would put every "
            "sample in the wrong place while every array kept its shape"
        )


def _read_patch(path: Path, patch: ProbePatch, field: str) -> np.ndarray:
    """Return one patch's values, flattened, checked against the patch's axes."""
    import numpy as np

    if not path.is_file():
        raise GoldenError(
            f"field {field!r} declares an export and {path} is not there. The contract is one "
            f"{COMSOL_GRID_HEADER} table per field per patch, named "
            f"{table_name(field, patch.name)!r}"
        )
    grid = read_grid(path, format="comsolgrid")
    expected = (patch.n_z, patch.n_r)
    if grid.values.shape != expected:
        raise GoldenError(
            f"{path} holds a {grid.values.shape} table and patch {patch.name!r} is {expected} "
            "(n_z rows of n_r values). A %Data block is one row per z sample, so a transposed "
            "export lands here — which is why no patch is square"
        )
    r_axis, z_axis = patch.axes_nm()
    for name, found, wanted in (("r", grid.r_nm, r_axis), ("z", grid.z_nm, z_axis)):
        worst = float(np.max(np.abs(found - wanted)))
        if worst > AXIS_TOL_NM:
            raise GoldenError(
                f"{path}: the {name} axis differs from patch {patch.name!r}'s by up to "
                f"{worst:.6g} nm, against a tolerance of {AXIS_TOL_NM:g} nm. The export was taken "
                "on a grid this probe document does not name, so every value is at a coordinate "
                "the comparison would attribute to another"
            )
    return np.asarray(grid.values, dtype=np.float64).ravel()


def _golden_hash(manifest: GoldenManifest, values: Mapping[str, np.ndarray]) -> str:
    """Return the content hash over the manifest and every archived array."""
    return content_hash(
        GOLDEN_SCHEMA,
        {"manifest": manifest.summary(), "values": {name: values[name] for name in sorted(values)}},
    )


def _write_archive(
    manifest: GoldenManifest, values: Mapping[str, np.ndarray], destination: Path
) -> Path:
    """Write the ``.npz`` and the canonical manifest, and return the ``.npz``."""
    import numpy as np

    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / ARCHIVE_NAME
    arrays = {name: np.asarray(values[name], dtype=np.float64) for name in sorted(values)}
    np.savez_compressed(archive, **arrays)  # type: ignore[arg-type]
    record = {"golden_hash": _golden_hash(manifest, values), **manifest.summary()}
    (destination / ARCHIVE_MANIFEST_NAME).write_bytes(canonical(record))
    return archive


def _archive_paths(path: Path) -> tuple[Path, Path]:
    """Return the ``(archive, manifest)`` pair a golden is read from."""
    archive = path / ARCHIVE_NAME if path.is_dir() else path
    manifest = archive.parent / ARCHIVE_MANIFEST_NAME
    for name, wanted in (("archive", archive), ("manifest", manifest)):
        if not wanted.is_file():
            raise GoldenError(
                f"no golden {name} at {wanted}. A golden is the {ARCHIVE_NAME!r} and the "
                f"{ARCHIVE_MANIFEST_NAME!r} written together by ingest_golden; one without the "
                "other cannot state what it holds"
            )
    return archive, manifest


def _read_archive_manifest(path: Path) -> tuple[GoldenManifest, str | None]:
    """Return the manifest written beside an archive, and the hash it recorded.

    The hash comes back rather than being discarded, because a recorded digest
    nothing ever compares against is a checksum that cannot fail;
    :func:`load_golden` is where it is checked. ``None`` only for a manifest
    written before the key existed.
    """
    decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(decoded, dict):
        raise GoldenError(f"{path} does not hold a golden manifest object")
    recorded = decoded.get("golden_hash")
    record = {key: value for key, value in decoded.items() if key != "golden_hash"}
    try:
        return GoldenManifest.model_validate(record), (
            str(recorded) if isinstance(recorded, str) else None
        )
    except ValidationError as error:
        raise CaseValidationError(render_problems(str(path), error), error) from None
