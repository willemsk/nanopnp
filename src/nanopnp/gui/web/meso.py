"""A continuum model in the Meso suite: its pore drawn from a molecular model, and that charge."""

from __future__ import annotations

import dataclasses
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, TypeVar

from nanopnp.api.project import own_outline
from nanopnp.charge.protonation import PAYLOAD_NAME, ProtonationTable
from nanopnp.charge.stage import stored_lattice
from nanopnp.gui.charge import ChargeMap, ConservationView, charge_image
from nanopnp.gui.render import CHARGE_ELEMENTS_FILENAME, VIEWER_DIRNAME
from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.study import STAGES, StudyModel, charge_record
from nanopnp.io.project import STORE_FOLDER
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import RUN_RECORD_FILENAME
from nanopnp.plot.data import (
    ChargeVolumes,
    DensityAtoms,
    ResidueAtoms,
    ResidueCharges,
    charge_volumes,
)
from nanopnp.validation.apbs import dx_text

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.api.case import Case
    from nanopnp.gui.solver import RunRequest
    from nanopnp.io.resolved import ResolvedCase

__all__ = ["DX_DIGITS", "VOLUMES", "MesoModel", "kept"]

_T = TypeVar("_T")

# What a stored charge draws, by the hashes of the artefacts it is read from: reading them parses
# the lattice and the protonation table, which a window's every redraw would repeat.
_HELD = 12
_READ: dict[tuple[str, ...], object] = {}
_READ_LOCK = threading.Lock()
# One overlay is computed at a time: its second read, as the other volume's, waits for the first.
_VOLUMES_LOCK = threading.Lock()

VOLUMES: tuple[str, ...] = ("full", "revolved")
"""The overlay's two volumes: the charge in 3D, and its mean about the axis."""
DX_DIGITS = 4
"""The places each overlay value is written to: enough for an isosurface, a third of the text."""

DRAWS_OWN_PORE = ("geometry.pore", "inputs.mesh")
"""The values with which a continuum model draws a pore of its own, which no molecule charges."""


def kept(key: tuple[str, ...], read: Callable[[], _T]) -> _T:
    """Return what ``read`` gives, kept by ``key`` for the next reads of the same artefacts."""
    with _READ_LOCK:
        if key in _READ:
            return _READ[key]  # type: ignore[return-value]
    found = read()
    with _READ_LOCK:
        _READ[key] = found
        while len(_READ) > _HELD:
            _READ.pop(next(iter(_READ)))
    return found


@dataclass
class MesoModel(ContinuumModel):
    """A continuum model walked over its molecular model to the charge, as Meso shows it.

    Its case is :meth:`Project.charge_case`'s; a build to the charge writes its run record under
    the store's ``runs/``, from which the deployed charge is drawn.
    """

    slot: ClassVar[str] = "meso"
    stages: ClassVar[tuple[str, ...]] = STAGES
    upto: ClassVar[str] = "charge"
    paths: ClassVar[re.Pattern[str]] = StudyModel.paths

    def _built_case(self) -> Case | str:
        try:
            return self.project.charge_case(self.name)
        except REFUSED as error:
            return str(error).replace(f"{self.project.root}/", "")

    def molecular(self) -> str | None:
        """Return the molecular model the pore is drawn from, or None where it draws its own."""
        if own_outline(self.body()) in DRAWS_OWN_PORE:
            return None
        return self.project.molecular_for(self.name)

    def request(self, case: Path, upto: str) -> RunRequest:
        """Return the walk to a stage: to the charge, its run record written under the store."""
        asked = super().request(case, upto)
        return dataclasses.replace(asked, write=True) if upto == "charge" else asked

    def resolved(self) -> ResolvedCase | None:
        """Return the model's case resolved, or None where it does not resolve."""
        return self._once("resolved", self._resolved)

    def _resolved(self) -> ResolvedCase | None:
        case = self.case()
        if case is None:
            return None
        try:
            return resolve(case, base=case.source.base)
        except REFUSED:
            return None

    # -- the charge's record ------------------------------------------------------------------

    def charge_record(self) -> Path | None:
        """Return the newest run record of the model's charge as it is now, or None."""
        charge = self.artefacts().get("charge")
        if charge is None:
            return None
        runs = self.project.root / STORE_FOLDER / "runs"
        found = [
            directory
            for directory in runs.glob(f"{self.name}-upto-charge-*")
            if (directory / RUN_RECORD_FILENAME).is_file()
        ]
        found.sort(key=lambda d: (d / RUN_RECORD_FILENAME).stat().st_mtime, reverse=True)
        return next((d for d in found if charge_record(d) == charge.hash), None)

    def elements(self) -> Path | None:
        """Return the deployed charge's file of the record :meth:`charge_record` names, if drawn."""
        record = self.charge_record()
        if record is None:
            return None
        path = record / VIEWER_DIRNAME / CHARGE_ELEMENTS_FILENAME
        return path if path.is_file() else None

    # -- the charge map -----------------------------------------------------------------------

    def charge_map(self) -> ChargeMap | None:
        """Return stage 7's lattice as a picture, or None where none is stored."""
        charge = self.artefacts().get("charge")
        if charge is None:
            return None

        def read() -> ChargeMap | None:
            lattice = stored_lattice(charge)
            return None if lattice is None else charge_image(lattice)

        return kept(("map", charge.hash), read)

    def conservation(self) -> ConservationView | None:
        """Return stage 7's conservation record, or None where no charge is stored."""
        charge = self.artefacts().get("charge")
        record = None if charge is None else charge.summary.get("charge")
        if not isinstance(record, dict):
            return None
        try:
            return ConservationView.from_record(record)
        except KeyError:
            return None

    def charges(self) -> ResidueCharges | None:
        """Return the residues' charges on the map, or None where no structure deposits them."""
        stored = self.artefacts()
        protonation, charge = stored.get("protonation"), stored.get("charge")
        resolved = self.resolved()
        if protonation is None or charge is None or resolved is None:
            return None
        structure = stored.get("structure")
        return kept(
            ("residues", protonation.hash, charge.hash),
            lambda: ResidueCharges.of(protonation, charge, resolved, structure),
        )

    # -- the atoms ----------------------------------------------------------------------------

    def residue_atoms(self) -> ResidueAtoms | None:
        """Return the protonated atoms in (r, z), by residue, or None where none is built."""
        stored = self.artefacts()
        protonation = stored.get("protonation")
        if protonation is None:
            return None
        structure = stored.get("structure")
        return kept(
            ("atoms", protonation.hash, "" if structure is None else structure.hash),
            lambda: ResidueAtoms.of(protonation, structure),
        )

    def density_atoms(self) -> DensityAtoms | None:
        """Return the atoms stage 2 smears, with its widths, or None where it reads none."""
        stored = self.artefacts()
        structure, resolved = stored.get("structure"), self.resolved()
        if structure is None or resolved is None or "density" not in self.walked():
            return None
        protonation, spec = stored.get("protonation"), resolved.density
        if spec is None or (spec.atoms == "protonated" and protonation is None):
            return None
        return kept(
            (
                "density-atoms",
                structure.hash,
                "" if protonation is None else protonation.hash,
                spec.atoms,
                repr(spec.kernel),
                repr(spec.sharpness),
            ),
            lambda: DensityAtoms.of(resolved, structure, protonation),
        )

    # -- the overlay --------------------------------------------------------------------------

    def volumes(self) -> ChargeVolumes | None:
        """Return the charge in 3D and its mean about the axis, or None where none is deposited.

        A first read takes seconds for a pore of tens of thousands of charged atoms: it is kept by
        the protonation's and the charge's hashes, and a read meanwhile waits for it.
        """
        stored = self.artefacts()
        protonation, charge = stored.get("protonation"), stored.get("charge")
        resolved, table = self.resolved(), self.table()
        if protonation is None or charge is None or resolved is None or table is None:
            return None

        def read() -> ChargeVolumes | None:
            try:
                return charge_volumes(table, resolved)
            except ValueError:
                # A table that carries no charge deposits none to draw.
                return None

        with _VOLUMES_LOCK:
            return kept(("volumes", protonation.hash, charge.hash), read)

    def volume_text(self, which: str) -> str | None:
        """Return one overlay volume as OpenDX text in angstroms, or None where none is drawn."""
        if which not in VOLUMES:
            raise ValueError(f"which: {which!r} is not one of {', '.join(VOLUMES)}")
        shown = self.volumes()
        if shown is None:
            return None
        stored = self.artefacts()
        hashes = tuple(stored[stage].hash for stage in ("protonation", "charge"))
        values = shown.full if which == "full" else shown.revolved
        return kept(
            ("dx", which, *hashes),
            lambda: dx_text(values, shown.origin_nm, shown.spacing_nm, digits=DX_DIGITS),
        )

    def pqr(self) -> Path | None:
        """Return the PQR file the model's charge reads its atoms from, or None."""
        case = self.case()
        if case is None or case.inputs.pqr is None or case.inputs.pqr.path is None:
            return None
        return Path(case.inputs.pqr.path)

    def table(self) -> ProtonationTable | None:
        """Return the stored protonation table the structure is drawn from, or None."""
        protonation = self.artefacts().get("protonation")
        if protonation is None:
            return None
        return kept(
            ("table", protonation.hash),
            lambda: ProtonationTable.read(Path(protonation.payload[PAYLOAD_NAME])),
        )
