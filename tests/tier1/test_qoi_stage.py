"""Stages 11 and 12: what a run reports, and what it refuses to report."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.io import manifest as manifest_io
from nanopnp.io.artefact import QOI_SCHEMA, REPORT_SCHEMA, CaseArtefact, StageInputs
from nanopnp.io.case import CaseDocument
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.ingest import ingest
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.post.export import (
    OMEGA_STEM,
    OMEGA_W_STEM,
)
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

# NUM-26 relative agreement between the NUM-24 and NUM-25 routes: SPECIFICATION.md NUM-26.
ROUTE_TOLERANCE = 1e-3

BAND_TOLERANCE = 1e-12

# Band-independence claim: SPECIFICATION.md NUM-24; measured spread 6.7e-10 on this mesh.
BAND_INDEPENDENCE = 1e-8

CONCENTRATION_M = 0.1
BIAS_V = 0.02

CASE = """
schema: nanopnp/case/v0.5
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
    document: CaseDocument
    text: str
    solution: Artefact
    mesh_path: Path
    work: Path

    def case(self, outputs: str) -> CaseDocument:
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
        return StageInputs(
            resolved=resolve(self.case(outputs)),
            upstream={"solve": self.solution},
            options=dict(options),
        )


@pytest.fixture(scope="module")
def solved(tmp_path_factory: pytest.TempPathFactory) -> Solved:
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
    solution = SolveStage(workspace=work / "solve").run(StageInputs(resolved=resolve(document)))
    return Solved(document=document, text=text, solution=solution, mesh_path=mesh_path, work=work)


def _slab(bands: tuple[tuple[str, float, float], ...], *, r_max_nm: float) -> MeshData:
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


# -- the lumen band ----------------------------------------------------------


def test_fr23_the_mesh_derived_band_reproduces_the_lumen_band_exactly() -> None:
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
    resolved = resolve(solved.document)
    data = ingest(resolved.mesh, resolved).data
    expected = lumen_band(PORE, fraction=BAND_FRACTION)
    derived = membrane_band(data)
    assert derived != expected, "the mesh no longer carries the round-off this tolerance describes"
    for got, want in zip(derived, expected, strict=True):
        assert abs(got - want) < BAND_TOLERANCE


# QR-12
def test_fr23_a_mesh_without_a_membrane_refuses_the_band_naming_it(solved: Solved) -> None:
    resolved = resolve(solved.document)
    data = ingest(resolved.mesh, resolved).data
    renamed = tuple("insulator" if name == "membrane" else name for name in data.materials)
    with pytest.raises(SelectionError) as raised:
        membrane_band(replace(data, materials=renamed))
    message = str(raised.value)
    assert "'membrane'" in message
    for name in renamed:
        assert name in message


# VER-11
def test_fr23_the_current_does_not_depend_on_where_the_band_sits(solved: Solved) -> None:
    reference = QoIStage().run(solved.inputs()).summary["current_A"]
    assert isinstance(reference, float)
    for half in (0.6, 1.5, 2.9):
        artefact = QoIStage().run(solved.inputs(indicator_band_nm=[-half, half]))
        current = artefact.summary["current_A"]
        assert isinstance(current, float)
        assert abs(current - reference) / abs(reference) < BAND_INDEPENDENCE, half


def test_fr23_an_inverted_band_is_refused_rather_than_sign_flipped(solved: Solved) -> None:
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
        "clamp_activations",
        # Provenance, not a quantity: the manifest's stabilisation group reads it from here.
        "stabilisation_currents_A",
        "two_pi_included",
        "routes_checked",
        "route_agreement",
    }


def test_num27_grounding_trans_reports_the_quantities_of_the_same_state_grounded_at_cis(
    solved: Solved,
) -> None:
    text = CASE.format(
        mesh_path=solved.mesh_path,
        concentration_M=CONCENTRATION_M,
        bias_V=-BIAS_V,
        outputs="current, transport_numbers, eof_rate",
    ).replace("ground: cis", "ground: trans")
    document = loads_case(text)
    solution = SolveStage(workspace=solved.work / "solve-trans").run(
        StageInputs(resolved=resolve(document))
    )
    trans = (
        QoIStage()
        .run(StageInputs(resolved=resolve(document), upstream={"solve": solution}))
        .summary
    )
    cis = QoIStage().run(solved.inputs()).summary
    assert trans["bias_V"] == pytest.approx(BIAS_V, rel=1e-15)
    assert isinstance(trans["conductance_S"], float)
    assert trans["conductance_S"] > 0.0
    for key in ("current_A", "conductance_S", "transport_number"):
        assert trans[key] == pytest.approx(cis[key], rel=1e-8), key


@pytest.mark.parametrize("outputs", ["eof_rate", "current, transport_numbers, eof_rate"])
def test_num27_a_zero_bias_case_reports_its_currents_and_leaves_the_ratios_undefined(
    solved: Solved, outputs: str
) -> None:
    text = CASE.format(
        mesh_path=solved.mesh_path,
        concentration_M=CONCENTRATION_M,
        bias_V=0.0,
        outputs=outputs,
    )
    document = loads_case(text)
    solution = SolveStage(workspace=solved.work / "solve-zero").run(
        StageInputs(resolved=resolve(document))
    )
    summary = (
        QoIStage()
        .run(StageInputs(resolved=resolve(document), upstream={"solve": solution}))
        .summary
    )
    assert summary["bias_V"] == 0.0
    assert summary["routes_checked"] is False
    assert "route_agreement" not in summary
    assert isinstance(summary["eof_m3_s"], float)
    if "current" in outputs:
        assert isinstance(summary["current_A"], float)
        assert summary["conductance_S"] is None
        assert summary["transport_number"] is None


def test_fr23_analyte_force_without_an_analyte_material_is_refused_naming_it(
    solved: Solved,
) -> None:
    with pytest.raises(SelectionError) as raised:
        QoIStage().run(solved.inputs("current, analyte_force"))
    message = str(raised.value)
    assert "analyte_force" in message
    assert "'analyte'" in message
    assert "electrolyte" in message, "the diagnostic must list the materials the mesh does carry"


def test_fr23_rectification_at_one_operating_point_is_refused_as_two_point(
    solved: Solved,
) -> None:
    with pytest.raises(SelectionError) as raised:
        QoIStage().run(solved.inputs("current, rectification"))
    message = str(raised.value)
    assert "rectification" in message
    assert "I(+V)/I(-V)" in message


def test_num28_the_extension_shell_scales_to_the_body_in_the_mesh() -> None:
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


# -- the route cross-check, and saying when it did not run --------------------


def test_qr04_the_route_agreement_figure_appears_in_the_artefact_summary(
    solved: Solved,
) -> None:
    summary = QoIStage().run(solved.inputs()).summary
    assert summary["routes_checked"] is True
    agreement = summary["route_agreement"]
    assert isinstance(agreement, dict)
    assert set(agreement) == {"indicator_A", "reaction_A", "relative_difference"}
    difference = agreement["relative_difference"]
    assert isinstance(difference, float)
    assert difference < ROUTE_TOLERANCE


def test_phy13_the_clamp_count_reaches_the_manifest_as_a_number(solved: Solved) -> None:
    summary = QoIStage().run(solved.inputs()).summary
    clamps = summary["clamp_activations"]
    assert isinstance(clamps, int)

    group = manifest_io.build(
        solved.document,
        case_text=solved.text,
        case_hash="0" * 64,
        electrolyte=resolve(solved.document).electrolyte,
        clamp_activations=clamps,
    ).groups()["materials"]
    assert isinstance(group, dict)
    assert group["clamp_activations"] == clamps

    without = manifest_io.build(
        solved.document,
        case_text=solved.text,
        case_hash="0" * 64,
        electrolyte=resolve(solved.document).electrolyte,
    ).groups()["materials"]
    assert isinstance(without, dict)
    assert without["clamp_activations"] != clamps
    assert "no solution was sampled" in str(without["clamp_activations"])


def test_fr25_check_routes_off_reaches_the_manifest_as_a_contributed_deviation(
    solved: Solved,
) -> None:
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
    inputs = solved.inputs()
    key = QoIStage().key(inputs)
    assert key.schema == QOI_SCHEMA
    assert key.hash == QoIStage().run(inputs).hash


def test_fr23_the_band_is_part_of_the_key(solved: Solved) -> None:
    default = QoIStage().key(solved.inputs())
    moved = QoIStage().key(solved.inputs(indicator_band_nm=[-1.5, 1.5]))
    assert default.hash != moved.hash


# -- stage 12 -----------------------------------------------------------------


def test_if07_the_report_writes_the_field_export_when_outputs_asks_for_it(
    solved: Solved, tmp_path: Path
) -> None:
    inputs = StageInputs(
        resolved=resolve(solved.case("current, fields")),
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


# FR-24
def test_if07_a_run_that_did_not_ask_for_fields_writes_nothing(
    solved: Solved, tmp_path: Path
) -> None:
    directory = tmp_path / "fields"
    inputs = StageInputs(
        resolved=resolve(solved.case("current")),
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
    qoi = QoIStage().run(solved.inputs("current"))
    inputs = StageInputs(
        resolved=resolve(solved.case("current")),
        upstream={"solve": solved.solution, "qoi": qoi},
    )
    stage = ReportStage(workspace=tmp_path / "fields")
    key = stage.key(inputs)
    assert key.inputs == {
        "case": CaseArtefact(inputs.resolved.document).hash,
        "qoi": qoi.hash,
        "solution": solved.solution.hash,
    }
    assert key.hash == stage.run(inputs).hash


def test_fr23_a_report_without_the_extraction_it_describes_is_refused(
    solved: Solved, tmp_path: Path
) -> None:
    inputs = StageInputs(
        resolved=resolve(solved.case("current")), upstream={"solve": solved.solution}
    )
    with pytest.raises(KeyError, match="qoi"):
        ReportStage(workspace=tmp_path / "fields").run(inputs)
