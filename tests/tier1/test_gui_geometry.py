"""VER-55: the geometry tab's view-model: where a pixel sits and what a hand edit writes."""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest
import yaml

from nanopnp.geometry.profile import (
    HAND_EDIT_SOURCE,
    load_profile,
    profile_digest,
)
from nanopnp.gui.geometry import (
    STAGE_1_FRAME,
    ProfileEditor,
    StageList,
    ViewTransform,
    density_section,
    membrane_slab,
    nearest_edge,
    nearest_vertex,
    planned_stages,
    reduced_image,
)
from nanopnp.gui.run_model import RunModel
from nanopnp.gui.solver import Failed, Finished, Produced, Stage, Started
from nanopnp.io.case_paths import (
    UnknownCasePathError,
    case_fields,
    value_at,
    with_profile,
)
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import run_case

H = 0.05


def test_ver55_a_planted_gaussian_lands_in_the_pixel_centred_on_it() -> None:
    r = np.arange(60) * H
    z = -1.0 + np.arange(80) * H
    r0, z0 = r[23], z[51]
    mean = np.exp(-((r[None, :] - r0) ** 2 + (z[:, None] - z0) ** 2) / (2 * 0.08**2))
    image = reduced_image(r, z, mean, quantity="mean")

    shown = image.display()
    row, column = np.unravel_index(int(np.argmax(shown)), shown.shape)
    assert image.pixel_centre(int(column), int(row)) == (r0, z0)
    assert image.pixel_of(r0, z0) == (int(column), int(row))
    assert image.pixel_centre(0, 0) == (r[0], z[-1])
    assert image.pixel_centre(image.width - 1, image.height - 1) == (r[-1], z[0])
    assert image.extent_nm == pytest.approx((-H / 2, r[-1] + H / 2, z[0] - H / 2, z[-1] + H / 2))
    assert image.frame == STAGE_1_FRAME
    assert image.scale == (0.0, 1.0)

    pixels = np.frombuffer(image.rgba(), dtype=np.uint8).reshape(image.height, image.width, 4)
    brightness = pixels[..., :3].astype(np.int64).sum(axis=2)
    assert np.unravel_index(int(np.argmax(brightness)), brightness.shape) == (row, column)

    transform = ViewTransform(
        x_range=image.extent_nm[:2], z_range=image.extent_nm[2:], width=640.0, height=480.0
    )
    left, top, width, height = transform.rectangle(*image.extent_nm)
    assert width / image.width == pytest.approx(height / image.height)
    px, py = transform.to_screen(r0, z0)
    assert left + column * width / image.width < px < left + (column + 1) * width / image.width
    assert top + row * height / image.height < py < top + (row + 1) * height / image.height
    assert transform.to_data(px, py) == pytest.approx((r0, z0))

    variance = reduced_image(r, z, 3e-4 * mean, quantity="cn_variance")
    assert variance.scale[1] == pytest.approx(3e-4)
    assert "cn variance" in variance.title


def test_ver55_the_density_section_is_symmetric_about_the_axis() -> None:
    half = 30
    x = np.arange(-half, half + 1) * H
    z = np.arange(40) * H
    radius = np.hypot(x[None, :, None], x[None, None, :])
    values = np.exp(-((radius - 1.0) ** 2) / 0.02) * np.ones((z.size, 1, 1))
    image = density_section(values.astype(np.float32), x, z, y_index=half)

    assert image.width == 2 * half + 1
    assert image.x_label.startswith("x")
    np.testing.assert_array_equal(image.values, image.values[:, ::-1])
    assert image.pixel_centre(half, 0)[0] == 0.0


def test_ver55_the_stage_list_is_a_projection_of_the_event_stream() -> None:
    rows = StageList(planned=("structure", "density", "symmetry", "contour", "region", "mesh"))
    model = RunModel()
    store = "/store"
    model.consume(
        [
            Started(case="case.yaml", store=None),
            Stage(name="case", index=0, total=7),
            Produced(
                name="case", schema="nanopnp/case/v0.5", hash="c" * 64, cached=True, store=store
            ),
            Stage(name="structure", index=1, total=7),
            Produced(
                name="structure",
                schema="nanopnp/structure/v0.5",
                hash="a" * 64,
                cached=True,
                store=store,
            ),
            Stage(name="density", index=2, total=7),
            Produced(
                name="density",
                schema="nanopnp/density/v0.5",
                hash="b" * 64,
                cached=False,
                store=store,
            ),
            Stage(name="symmetry", index=3, total=7),
        ]
    )
    listed = rows.rows(model)
    assert [row.status for row in listed] == [
        "cached",
        "stored",
        "running",
        "waiting",
        "waiting",
        "waiting",
    ]
    assert listed[0].hash == "a" * 64
    assert [row.number for row in listed] == [1, 2, 3, 4, 5, 6]
    assert listed[3].title == "Contour extraction and conditioning"

    model.consume([Failed(exit_code=4, error="ContourGateError", message="stage 4 ...")])
    assert [row.status for row in rows.rows(model)][2] == "failed"

    done = RunModel()
    done.consume(
        [
            Started(case="c", store=None),
            Stage(name="mesh", index=0, total=1),
            Finished(directory="d"),
        ]
    )
    assert [row.status for row in StageList(planned=("mesh",)).rows(done)] == ["waiting"]


SQUARE = [(2.0, 0.0), (2.0, 1.0), (3.0, 1.0), (3.0, 0.0)]


def _editor() -> ProfileEditor:
    return ProfileEditor(vertices=list(SQUARE), parent_digest="0" * 64, parent_name="square")


def test_ver55_edit_operations_undo_exactly() -> None:
    editor = _editor()
    before = list(editor.vertices)

    index = editor.insert(1)
    assert editor.vertices[index] == (2.5, 1.0)
    editor.move(index, 2.5, 1.2)
    editor.delete(0)
    assert len(editor.vertices) == 4
    after = list(editor.vertices)

    assert editor.undo() and editor.undo() and editor.undo()
    assert editor.vertices == before
    assert not editor.undo()
    assert editor.redo() and editor.redo() and editor.redo()
    assert editor.vertices == after
    assert not editor.redo()

    editor.undo()
    editor.move(0, 2.1, 0.1)
    assert not editor.can_redo, "an edit after an undo forgets what was undone"

    small = ProfileEditor(vertices=SQUARE[:3], parent_digest="0" * 64, parent_name="triangle")
    with pytest.raises(ValueError, match="at least three vertices"):
        small.delete(0)

    transform = ViewTransform(x_range=(1.5, 3.5), z_range=(-0.5, 1.5), width=400.0, height=400.0)
    px, py = transform.to_screen(3.0, 1.0)
    assert nearest_vertex(SQUARE, transform, px + 3.0, py - 2.0) == 2
    assert nearest_vertex(SQUARE, transform, px + 40.0, py) is None
    mx, my = transform.to_screen(2.5, 1.0)
    assert nearest_edge(SQUARE, transform, mx, my + 2.0) == 1


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda editor: editor.move(1, 3.0, -0.5), r"edge \d+ .* crosses edge \d+"),
        (lambda editor: editor.move(2, -0.1, 1.0), r"non-negative .* at vertex 2"),
        (lambda editor: editor.move(2, 2.0, 1.0), r"coincide .* vertices 1 and 2"),
    ],
    ids=["self-crossing", "negative radius", "repeated vertex"],
)
def test_ver55_an_invalid_edit_cannot_be_saved(edit, message: str, tmp_path: Path) -> None:
    editor = _editor()
    edit(editor)
    problem = editor.problem
    assert problem is not None
    assert re.search(message, problem), problem
    with pytest.raises(ValueError, match=message):
        editor.save(tmp_path)
    assert not list(tmp_path.iterdir())

    document = {
        "schema": "nanopnp/profile/v0.5",
        "name": "edited",
        "provenance": {
            "source": HAND_EDIT_SOURCE,
            "citation": "square",
            "sha256": "0" * 64,
            "vertex_count": 4,
            "min_vertex_spacing_nm": 0.0,
            "min_feature_size_nm": 0.0,
            "signed_area_nm2": 0.0,
        },
        "vertices": [list(vertex) for vertex in editor.vertices],
    }
    path = tmp_path / "edited.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError) as refused:
        load_profile(path)
    assert problem in str(refused.value)


def test_ver55_the_null_edit_is_its_parent_recorded_as_a_hand_edit(tmp_path: Path) -> None:
    parent = load_profile("clya_reference_profile")
    editor = ProfileEditor.from_profile(parent)
    saved = load_profile(editor.save(tmp_path))

    assert saved.vertices == parent.vertices
    assert saved.provenance.source == HAND_EDIT_SOURCE
    assert saved.provenance.sha256 == profile_digest(parent)
    assert saved.provenance.citation == parent.name
    assert saved.provenance.min_vertex_spacing_nm == parent.provenance.min_vertex_spacing_nm
    assert saved.provenance.min_feature_size_nm == parent.provenance.min_feature_size_nm
    assert saved.provenance.signed_area_nm2 == parent.provenance.signed_area_nm2
    assert profile_digest(saved)[:16] in editor.save(tmp_path).name

    assert parent.is_reference
    with pytest.raises(ValueError, match=r"needs the reference geometry.*'hand-edit'"):
        saved.require_reference("a Tier-3 comparison")


TUBE_CASE = """\
schema: nanopnp/case/v0.5
name: tube-edit
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
geometry:
  membrane: {{thickness_nm: 1.0, centre_z_nm: {centre}}}
  reservoir: {{radius_nm: 30.0}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: 20.0}}}}
"""

CENTRE_NM = 1.5


@pytest.fixture(scope="module")
def built(tube_pdb: Path, tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("edit")
    case = root / "tube.case.yaml"
    case.write_text(TUBE_CASE.format(pdb=tube_pdb, centre=CENTRE_NM), encoding="utf-8")
    store = Store(root / "store")
    return case, store, run_case(case, store=store, upto="mesh", write=False)


def _read(document, path: str) -> object:
    try:
        return value_at(document, path)
    except UnknownCasePathError:
        return "<absent>"


def test_ver55_the_derived_case_changes_only_the_profile_route(built, tmp_path: Path) -> None:
    case, _store, result = built
    original = load_case(case)
    profile = load_profile(result.artefacts["contour"].payload["profile"])
    written, derived_path = ProfileEditor.from_profile(profile).save_case(original, case)

    assert derived_path.parent == case.parent.resolve()
    assert derived_path != case.resolve()
    assert case.read_text(encoding="utf-8") == TUBE_CASE.format(
        pdb=original.structure.source.path,
        centre=CENTRE_NM,  # type: ignore[union-attr]
    ), "the original case file is never modified"
    assert written.is_absolute()

    derived = load_case(derived_path)
    resolved = resolve(derived)
    assert derived.structure is None
    assert resolved.profile is not None and resolved.profile.path == written
    assert derived == with_profile(original, written)

    changed = {
        reference.path
        for reference in case_fields()
        if _read(original, reference.path) != _read(derived, reference.path)
    }
    allowed = ("structure.", "inputs.profile.")
    assert changed, "the profile route changed nothing"
    assert all(path.startswith(allowed) for path in changed), sorted(changed)
    assert membrane_slab(derived) == (CENTRE_NM - 0.5, CENTRE_NM + 0.5)
    assert planned_stages(original) == (
        "structure",
        "density",
        "symmetry",
        "contour",
        "region",
        "mesh",
    )
    assert planned_stages(derived) == ("region", "mesh")


def test_ver55_the_null_edit_meshes_to_the_same_content_under_a_new_key(built) -> None:
    case, store, result = built
    original = load_case(case)
    profile = load_profile(result.artefacts["contour"].payload["profile"])

    editor = ProfileEditor.from_profile(profile)
    _, null_case = editor.save_case(original, case)
    null = run_case(null_case, store=store, upto="mesh")

    stage5 = result.artefacts["region"]
    null5 = null.artefacts["region"]
    assert null5.hash != stage5.hash, "the null edit is a different input, so a different key"
    from nanopnp.geometry.region import read_region

    assert (
        read_region(null5.payload["region"]).profile
        == read_region(stage5.payload["region"]).profile
    )
    assert null.artefacts["mesh"].hash != result.artefacts["mesh"].hash
    assert (
        null.artefacts["mesh"].summary["content_hash"]
        == result.artefacts["mesh"].summary["content_hash"]
    )

    loop = np.asarray(profile.vertices)
    constriction = result.artefacts["contour"].summary["constriction"]
    target = (constriction["r_nm"], constriction["z_nm"])  # type: ignore[index]
    index = int(np.argmin(np.hypot(loop[:, 0] - target[0], loop[:, 1] - target[1])))
    r, z = profile.vertices[index]
    editor.move(index, r + 0.1, z)
    _, moved_case = editor.save_case(original, case)
    moved = run_case(moved_case, store=store, upto="mesh")
    assert moved.artefacts["region"].hash != null5.hash
    assert (
        moved.artefacts["mesh"].summary["content_hash"]
        != null.artefacts["mesh"].summary["content_hash"]
    )
    assert not math.isclose(
        read_region(moved.artefacts["region"].payload["region"]).profile[index][0],
        read_region(null5.payload["region"]).profile[index][0],
    )

    manifest = moved.manifest
    artefacts = manifest.inputs["artefacts"]
    assert not {"structure", "density", "symmetry", "contour"} & set(artefacts)  # type: ignore[arg-type]
    files = manifest.inputs["files"]
    assert "profile" in files and "structure" not in files  # type: ignore[operator]
