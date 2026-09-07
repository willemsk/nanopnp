"""Stages 11 and 12: what a run reports, and what it refuses to report.

Two claims are under test here and neither of them is about the physics — the
numbers themselves are WP5's Tier-2 business (VER-11, VER-12). What this module
asserts is that the *selection* is honest.

**The band is the existing convention, read off a different object.**
:func:`~nanopnp.post.indicator.lumen_band` takes a
:class:`~nanopnp.mesh.primitives.CylindricalPoreGeometry` and an ingested mesh
has none, so stage 11 derives the NUM-24 band from the ``membrane`` material's
own axial extent. That derivation has to be *identically* the geometry one, not
merely close: a band that differed by a few percent would move no number enough
to fail anything and would quietly make two routes into the same quantity.

**A word in ``outputs:`` is answered or refused, never dropped.** A run that
returns five of the six quantities asked for is a run whose output list means
nothing, so ``rectification`` at one operating point and ``analyte_force``
without a body each abort naming what is missing (section 5.3.1 NOTE, QR-12).

Corrections are ``none`` throughout and the mesh is the coarsest that carries
all four domains. That pairing is deliberate and it is the opposite of what
:mod:`tests.tier1.test_solution_state` needs: the NUM-26 route agreement on this
mesh is 3.3e-10 with the corrections off and 4.0e-01 with them on, because the
6.2 nm^-1 ion wall function of PHY-08 varies over a tenth of the pore radius and
124 elements do not resolve it. Switching the physics off rather than refining
the mesh is what lets the route check act as an oracle here at a cost of
seconds, and it is legitimate precisely because nothing in this module is a
claim about the corrections. Stabilisation is ``none`` (NUM-11).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.io import manifest as manifest_io
from nanopnp.io.artefact import QOI_SCHEMA, REPORT_SCHEMA, CaseArtefact, StageInputs
from nanopnp.io.case import CaseDocument, loads_case, resolve
from nanopnp.io.fields import OMEGA_STEM, OMEGA_W_STEM
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.post.indicator import lumen_band
from nanopnp.post.stage import (
    BAND_FRACTION,
    EXTENSION_INNER,
    EXTENSION_OUTER,
    QoIStage,
    ReportStage,
    SelectionError,
    extension_shell,
    membrane_band,
)
from nanopnp.solve.stage import SolveStage

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.artefact import Artefact

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0
"""The cheapest mesh that carries all four domains; see the module docstring."""

ROUTE_TOLERANCE = 1e-3
"""NUM-26's relative agreement between the NUM-24 and NUM-25 routes."""

BAND_TOLERANCE = 1e-12
"""Absolute agreement in nm between the mesh-derived band and the geometry one.

The derivation is exact — :func:`test_fr23_the_mesh_derived_band_reproduces_the
_lumen_band_exactly` shows it returning ``lumen_band`` bit for bit — but the
*mesh* is not: the OCC revolve puts the membrane's upper face at
``3.000000000000001`` nm rather than ``3.0``, one unit in the last place, and
mesh-independently so [tested]. 1e-12 nm is twelve orders below the 0.5 nm
finest element and eight below the smallest Debye length in the FR-17 envelope,
so it separates round-off from any band a reader could have meant.
"""

BAND_INDEPENDENCE = 1e-8
"""Relative change in the current a legitimate move of the band may produce.

NUM-24's claim is that the answer does not depend on where the band sits, and
the measured spread over bands of half-width 0.6, 1.5, 2.4 and 2.9 nm on this
mesh is 6.7e-10 [tested]. The tolerance is set an order and a half above that so
that the assertion fails on a band-dependent current rather than on quadrature
noise; VER-11's Tier-2 study is the converged version of the same claim.
"""

CONCENTRATION_M = 0.1
BIAS_V = 0.02

CASE = """
schema: nanopnp/case/v1
name: qoi-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: {concentration_M}
  temperature_K: 298.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
boundary_conditions:
  bias_V: {bias_V}
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [{outputs}]
"""


@dataclass
class Solved:
    """One converged solve of the reference case, and what it was solved from."""

    document: CaseDocument
    text: str
    solution: Artefact
    mesh_path: Path
    work: Path

    def case(self, outputs: str) -> CaseDocument:
        """Return the same case asking for ``outputs`` instead.

        Nothing in ``outputs:`` reaches the solve — it selects what is
        *extracted* — so every variant shares the one converged state, which is
        what makes an exhaustive selection test cost milliseconds.
        """
        return loads_case(
            CASE.format(
                mesh_path=self.mesh_path,
                concentration_M=CONCENTRATION_M,
                bias_V=BIAS_V,
                outputs=outputs,
            )
        )

    def inputs(
        self,
        outputs: str = "current, transport_numbers, eof_rate",
        **options: Canonicalisable,
    ) -> StageInputs:
        """Return stage inputs carrying the converged solve and ``options``."""
        return StageInputs(
            case=self.case(outputs), upstream={"solve": self.solution}, options=dict(options)
        )


@pytest.fixture(scope="module")
def solved(tmp_path_factory: pytest.TempPathFactory) -> Solved:
    """Solve the reference case once, through stage 10 as a run would."""
    work = tmp_path_factory.mktemp("qoi")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    text = CASE.format(
        mesh_path=mesh_path,
        concentration_M=CONCENTRATION_M,
        bias_V=BIAS_V,
        outputs="current, transport_numbers, eof_rate",
    )
    document = loads_case(text)
    solution = SolveStage(workspace=work / "solve").run(StageInputs(case=document))
    return Solved(document=document, text=text, solution=solution, mesh_path=mesh_path, work=work)


def _slab(bands: tuple[tuple[str, float, float], ...], *, r_max_nm: float) -> MeshData:
    """Return a hand-built mesh: stacked rectangles in ``z``, each one material.

    Built rather than meshed because the two things it is used for — that the
    band derivation is exact, and that the extension shell scales to the body —
    are claims about arithmetic on a material's extent, and a meshed extent
    carries the OCC round-off that :data:`BAND_TOLERANCE` exists to describe.
    Here the extents are exactly the numbers written above.
    """
    import numpy as np

    levels = [bands[0][1], *[upper for _, _, upper in bands]]
    vertices = np.array([[r, z] for z in levels for r in (0.0, r_max_nm)], dtype=np.float64)
    names: list[str] = []
    for name, _, _ in bands:
        if name not in names:
            names.append(name)
    triangles = []
    material = []
    for index, (name, _, _) in enumerate(bands):
        base = 2 * index
        triangles += [[base, base + 1, base + 3], [base, base + 3, base + 2]]
        material += [names.index(name)] * 2
    edges = [[2 * i, 2 * i + 2] for i in range(len(bands))]
    edges += [[2 * i + 1, 2 * i + 3] for i in range(len(bands))]
    group = [0] * len(bands) + [1] * len(bands)
    return MeshData(
        vertices=vertices,
        triangles=np.array(triangles, dtype=np.int64),
        triangle_material=np.array(material, dtype=np.int64),
        materials=tuple(names),
        edges=np.array(edges, dtype=np.int64),
        edge_group=np.array(group, dtype=np.int64),
        boundaries=("axis", "wall"),
    )


# -- the NUM-24 band ----------------------------------------------------------


def test_fr23_the_mesh_derived_band_reproduces_the_lumen_band_exactly() -> None:
    """On an exactly symmetric membrane the two derivations agree bit for bit.

    Exactly, not to a tolerance, because the claim is about the arithmetic and
    not about the mesh: ``lumen_band`` halves the thickness and scales, and
    :func:`~nanopnp.post.stage.membrane_band` centres and half-scales the extent.
    Two formulas that agreed only to a few ulp would be two conventions, and a
    later edit could widen the gap without failing anything.
    """
    data = _slab(
        (
            ("trans", -5.0, -PORE.half_thickness_nm),
            ("membrane", -PORE.half_thickness_nm, PORE.half_thickness_nm),
            ("cis", PORE.half_thickness_nm, 5.0),
        ),
        r_max_nm=PORE.pore_radius_nm,
    )
    assert membrane_band(data) == lumen_band(PORE, fraction=BAND_FRACTION)


def test_fr23_the_generated_mesh_gives_the_same_band_to_mesh_round_off(solved: Solved) -> None:
    """A meshed pore reproduces the geometry band to the mesh's own round-off.

    The residue is the OCC revolve, not the derivation: the membrane's upper
    face lands at ``3.000000000000001`` nm on every element size tried. See
    :data:`BAND_TOLERANCE` for why that is separable from a band anyone meant.
    """
    resolved = resolve(solved.document)
    data = ingest(resolved.mesh, resolved).data
    expected = lumen_band(PORE, fraction=BAND_FRACTION)
    derived = membrane_band(data)
    assert derived != expected, "the mesh no longer carries the round-off this tolerance describes"
    for got, want in zip(derived, expected, strict=True):
        assert abs(got - want) < BAND_TOLERANCE


def test_fr23_a_mesh_without_a_membrane_refuses_the_band_naming_it(solved: Solved) -> None:
    """No ``membrane`` material aborts, naming it and listing what the mesh has (QR-12).

    Not a fallback to the whole domain: a band spanning the reservoirs puts
    ``grad(psi)`` on the caps, where NUM-24's identity with the cap flux no
    longer holds, and the run would then fail somewhere else entirely.
    """
    resolved = resolve(solved.document)
    data = ingest(resolved.mesh, resolved).data
    renamed = tuple("insulator" if name == "membrane" else name for name in data.materials)
    with pytest.raises(SelectionError) as raised:
        membrane_band(replace(data, materials=renamed))
    message = str(raised.value)
    assert "'membrane'" in message
    for name in renamed:
        assert name in message


def test_fr23_the_current_does_not_depend_on_where_the_band_sits(solved: Solved) -> None:
    """Moving and widening the band leaves the current alone (NUM-24, VER-11).

    The band is a discretisation choice, and a quantity that is a function of it
    is not the current. Asserted here as well as in Tier 2 because stage 11 is
    where the band stops being an argument a caller chose and becomes one the
    mesh implied.
    """
    reference = QoIStage().run(solved.inputs()).summary["current_A"]
    assert isinstance(reference, float)
    for half in (0.6, 1.5, 2.9):
        artefact = QoIStage().run(solved.inputs(indicator_band_nm=[-half, half]))
        current = artefact.summary["current_A"]
        assert isinstance(current, float)
        assert abs(current - reference) / abs(reference) < BAND_INDEPENDENCE, half


def test_fr23_an_inverted_band_is_refused_rather_than_sign_flipped(solved: Solved) -> None:
    """A band decreasing in ``z`` aborts; it would negate every current silently."""
    with pytest.raises(SelectionError, match="increasing in z"):
        QoIStage().run(solved.inputs(indicator_band_nm=[2.4, -2.4]))


# -- what ``outputs:`` selects, and what it cannot buy -------------------------


@pytest.mark.parametrize(
    ("outputs", "expected"),
    [
        ("current", {"current_A", "currents_A", "conductance_S"}),
        ("transport_numbers", {"transport_number", "currents_A"}),
        ("eof_rate", {"eof_m3_s"}),
        (
            "current, eof_rate",
            {"current_A", "currents_A", "conductance_S", "eof_m3_s"},
        ),
    ],
)
def test_fr23_outputs_selects_exactly_the_quantities_asked_for(
    solved: Solved, outputs: str, expected: set[str]
) -> None:
    """The summary carries the selected quantities and no unselected one.

    The extraction is one calculation for all of them — NUM-27 requires that, so
    a current and a transport number reported together cannot come from two —
    but reporting is what ``outputs:`` governs. A stage that returned everything
    regardless would make the list decorative, and a reader would have no way to
    tell which quantities the run was actually asked to stand behind.
    """
    quantities = {
        "current_A",
        "currents_A",
        "conductance_S",
        "transport_number",
        "eof_m3_s",
    }
    summary = QoIStage().run(solved.inputs(outputs)).summary
    assert quantities & set(summary) == expected
    assert set(summary) - quantities == {
        "indicator_band_nm",
        "bias_V",
        "two_pi_included",
        "routes_checked",
        "route_agreement",
    }


def test_fr23_analyte_force_without_an_analyte_material_is_refused_naming_it(
    solved: Solved,
) -> None:
    """A force on a body a domain does not contain aborts (section 5.3.1 NOTE)."""
    with pytest.raises(SelectionError) as raised:
        QoIStage().run(solved.inputs("current, analyte_force"))
    message = str(raised.value)
    assert "analyte_force" in message
    assert "'analyte'" in message
    assert "electrolyte" in message, "the diagnostic must list the materials the mesh does carry"


def test_fr23_rectification_at_one_operating_point_is_refused_as_two_point(
    solved: Solved,
) -> None:
    """``I(+V)/I(-V)`` needs two biases and a run has one (section 5.3.1 NOTE).

    Refused rather than dropped, and refused rather than answered from one
    point: a ratio invented from a single solve would be a number nobody
    measured, reported beside numbers somebody did.
    """
    with pytest.raises(SelectionError) as raised:
        QoIStage().run(solved.inputs("current, rectification"))
    message = str(raised.value)
    assert "rectification" in message
    assert "I(+V)/I(-V)" in message


def test_num28_the_extension_shell_scales_to_the_body_in_the_mesh() -> None:
    """The NUM-28 shell is ``(1.2, 3.0)`` times the body's largest semi-axis."""
    semi = 1.5
    data = _slab(
        (
            ("electrolyte", -4.0, -semi),
            ("analyte", -semi, semi),
            ("electrolyte", semi, 4.0),
        ),
        r_max_nm=semi,
    )
    inner, outer = extension_shell(data)
    assert inner == pytest.approx(EXTENSION_INNER * semi, rel=1e-15)
    assert outer == pytest.approx(EXTENSION_OUTER * semi, rel=1e-15)


# -- the QR-04 cross-check, and saying when it did not run --------------------


def test_qr04_the_route_agreement_figure_appears_in_the_artefact_summary(
    solved: Solved,
) -> None:
    """Both routes and their relative difference are reported, not just a verdict.

    RSK-03 is a plausible, stable, wrong current, and the defence against it is
    NUM-26's second route. A recorded pass says the check ran; the recorded
    *figure* is what lets a reader see it passing by three orders rather than by
    a hair, which is the difference between an oracle and a rubber stamp.
    """
    summary = QoIStage().run(solved.inputs()).summary
    assert summary["routes_checked"] is True
    agreement = summary["route_agreement"]
    assert isinstance(agreement, dict)
    assert set(agreement) == {"indicator_A", "reaction_A", "relative_difference"}
    difference = agreement["relative_difference"]
    assert isinstance(difference, float)
    assert difference < ROUTE_TOLERANCE


def test_fr25_check_routes_off_reaches_the_manifest_as_a_contributed_deviation(
    solved: Solved,
) -> None:
    """Switching NUM-26 off is a departure the case file cannot show (§5.3.3).

    No key selects it, so the diff of :mod:`nanopnp.io.defaults` cannot see it
    and the stage has to contribute it. A run whose current has one route and no
    oracle must say so in its own manifest, because that is the only place a
    reader of an archived result will look.
    """
    stage = QoIStage()
    assert stage.deviations(solved.inputs()) == ()
    contributed = stage.deviations(solved.inputs(check_routes=False))
    assert len(contributed) == 1
    assert "check_routes" in contributed[0].source
    assert "NUM-26" in contributed[0].description

    record = manifest_io.build(
        solved.document,
        case_text=solved.text,
        case_hash="0" * 64,
        contributed_deviations=contributed,
    ).groups()["deviations"]
    assert isinstance(record, dict)
    assert record["count"] == len(record["switches"]) + 1
    assert record["contributed"] == [contributed[0].summary()]

    summary = QoIStage().run(solved.inputs(check_routes=False)).summary
    assert summary["routes_checked"] is False
    assert "route_agreement" not in summary


# -- the artefact keys --------------------------------------------------------


def test_fr23_the_key_is_the_artefact_the_run_produces(solved: Solved) -> None:
    """``key()`` returns the hash ``run()`` will, or the cache answers wrongly.

    Section 5.3.2 has the store ask for a key before deciding whether to run the
    stage. If the two were computed differently the store would either miss on
    everything or, far worse, hit on a key the run would not have produced.
    """
    inputs = solved.inputs()
    key = QoIStage().key(inputs)
    assert key.schema == QOI_SCHEMA
    assert key.hash == QoIStage().run(inputs).hash


def test_fr23_the_band_is_part_of_the_key(solved: Solved) -> None:
    """Two extractions over different bands are two cache entries.

    The currents agree to 1e-10 and the artefacts must still differ: NUM-24's
    band independence is a *result*, tested above, and a key that assumed it
    would serve one band's answer for another band's question.
    """
    default = QoIStage().key(solved.inputs())
    moved = QoIStage().key(solved.inputs(indicator_band_nm=[-1.5, 1.5]))
    assert default.hash != moved.hash


# -- stage 12 -----------------------------------------------------------------


def test_if07_the_report_writes_the_field_export_when_outputs_asks_for_it(
    solved: Solved, tmp_path: Path
) -> None:
    """``fields`` in ``outputs:`` produces the IF-07 pair for each domain."""
    inputs = StageInputs(
        case=solved.case("current, fields"),
        upstream={
            "solve": solved.solution,
            "qoi": QoIStage().run(solved.inputs("current")),
        },
    )
    artefact = ReportStage(workspace=tmp_path / "fields").run(inputs)
    assert artefact.schema == REPORT_SCHEMA
    assert artefact.parameters["exports"] == ["fields"]
    expected = {
        f"{stem}{suffix}" for stem in (OMEGA_STEM, OMEGA_W_STEM) for suffix in (".xdmf", ".h5")
    }
    assert set(artefact.payload) == expected
    for path in artefact.payload.values():
        assert path.stat().st_size > 0
    files = artefact.summary["files"]
    assert isinstance(files, dict)
    assert set(files["attributes"]) == {OMEGA_STEM, OMEGA_W_STEM}


def test_if07_a_run_that_did_not_ask_for_fields_writes_nothing(
    solved: Solved, tmp_path: Path
) -> None:
    """The export is of order ten megabytes and is written only when requested.

    An FR-24 envelope sweep of thousands of points would otherwise write tens of
    gigabytes nobody asked for, which is why the selection is checked here and
    not left to a caller remembering to pass a flag.
    """
    directory = tmp_path / "fields"
    inputs = StageInputs(
        case=solved.case("current"),
        upstream={
            "solve": solved.solution,
            "qoi": QoIStage().run(solved.inputs("current")),
        },
    )
    artefact = ReportStage(workspace=directory).run(inputs)
    assert artefact.parameters["exports"] == []
    assert artefact.payload == {}
    assert not directory.exists()


def test_fr23_the_report_is_keyed_on_the_case_the_solve_and_the_extraction(
    solved: Solved, tmp_path: Path
) -> None:
    """All three input hashes enter the key, so no report outlives what it describes."""
    qoi = QoIStage().run(solved.inputs("current"))
    inputs = StageInputs(
        case=solved.case("current"),
        upstream={"solve": solved.solution, "qoi": qoi},
    )
    stage = ReportStage(workspace=tmp_path / "fields")
    key = stage.key(inputs)
    assert key.inputs == {
        "case": CaseArtefact(inputs.case).hash,
        "qoi": qoi.hash,
        "solution": solved.solution.hash,
    }
    assert key.hash == stage.run(inputs).hash


def test_fr23_a_report_without_the_extraction_it_describes_is_refused(
    solved: Solved, tmp_path: Path
) -> None:
    """Stage 12 names the artefact it is missing; running it alone is the case."""
    inputs = StageInputs(case=solved.case("current"), upstream={"solve": solved.solution})
    with pytest.raises(KeyError, match="qoi"):
        ReportStage(workspace=tmp_path / "fields").run(inputs)
