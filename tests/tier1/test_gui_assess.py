"""VER-55 — measuring an edit and seeding after a refusal, against the case's own stored stages.

The editor shows the §5.2.1 criteria without enforcing them (WP24 D8), and may
start from a loop stage 4's gate refused (§8.2.2 B9, D10). Both go through
:func:`nanopnp.geometry.contour.measure`, stage 4's gate without its raise, on
stage 4's own inputs: the stored stage-3 map's mid-planes and the stored stage-1
structure's probe radius. So two oracles are exact:

- a loop stage 4 accepted measures to the ``gate`` record its summary carries;
- a loop stage 4 refused is recomputed as :func:`~nanopnp.geometry.contour.condition`
  computes it, and fails first on the criterion, the value and the ``(r, z)`` the
  refusal named.

The refusal is a real one: the synthetic tube at isolevel 0.1, whose contour
lies 0.085 nm inside the probe radius against a 0.05 nm allowance. The plan
proposed a feature-size refusal; stage 4's closing of radius 2h removes every
feature the gate's 2h criterion measures (the §5.2.1 NOTE's margin), so no map
yields one after conditioning, and the band is the criterion a structure fails.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from nanopnp.geometry.contour import ContourGateError, condition
from nanopnp.geometry.profile import load_profile
from nanopnp.gui.assess import (
    AssessFailed,
    AssessProcess,
    AssessRequest,
    Seeded,
    assess,
    seed,
)
from nanopnp.gui.geometry import ProfileEditor
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import run_case
from nanopnp.symmetry.reduce import ReducedMap

CASE = """\
schema: nanopnp/case/v2
name: {name}
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
geometry: {{contour: {{isolevel: {isolevel}}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
"""

TIMEOUT_S = 300.0


@pytest.fixture(scope="module")
def tube_store(tube_pdb: Path, tmp_path_factory: pytest.TempPathFactory):
    """Return a directory, a store, and the two tube cases: one stage 4 accepts, one it refuses."""
    root = tmp_path_factory.mktemp("assess")
    store = Store(root / "store")
    cases = {}
    for name, isolevel in (("accepted", 0.25), ("refused", 0.1)):
        path = root / f"{name}.case.yaml"
        path.write_text(CASE.format(name=name, pdb=tube_pdb, isolevel=isolevel), encoding="utf-8")
        cases[name] = path
    return root, store, cases


def test_ver55_an_accepted_loop_measures_to_its_gate_record(tube_store) -> None:
    """``measure`` on stage 4's own loop equals the ``gate`` record of its summary (D9)."""
    _root, store, cases = tube_store
    result = run_case(cases["accepted"], store=store, upto="contour", write=False)
    artefact = result.artefacts["contour"]
    loop = load_profile(artefact.payload["profile"]).vertices

    measured = assess(
        AssessRequest(case=str(cases["accepted"]), store=str(store.root), vertices=tuple(loop))
    )
    assert measured.passed
    assert measured.record == artefact.summary["gate"]


def test_ver55_a_refused_contour_seeds_the_editor(tube_store, tmp_path: Path) -> None:
    """The seed is ``condition()``'s loop; it fails first where stage 4 refused it (B9, D10)."""
    _root, store, cases = tube_store
    path = cases["refused"]
    with pytest.raises(ContourGateError) as refused:
        run_case(path, store=store, upto="contour", write=False)
    stored = run_case(path, store=store, upto="symmetry", write=False)
    reduced = ReducedMap.read(stored.artefacts["symmetry"].payload["reduced"])
    resolved = resolve(load_case(path))
    assert resolved.contour is not None and resolved.density is not None

    seeded = seed(AssessRequest(case=str(path), store=str(store.root)))

    expected = condition(
        reduced.mean,
        reduced.r_nm,
        reduced.z_nm,
        spacing_nm=resolved.density.grid_spacing_nm,
        isolevel=resolved.contour.isolevel,
        smoothing=resolved.contour.smoothing,
        simplify_tol_nm=resolved.contour.simplify_tol_nm,
    ).loop
    np.testing.assert_array_equal(np.asarray(seeded.vertices), expected)
    first = seeded.assessment.failures[0]
    assert first.criterion == refused.value.criterion == "radius profile"
    assert first.message == str(refused.value)
    assert first.location_nm == refused.value.location_nm
    assert first.location_nm is not None
    assert seeded.digest == stored.artefacts["symmetry"].summary["payload_digest"]
    assert seeded.name.startswith("contour-")

    # The saved edit records that map's payload digest, as stage 4 would have (D5).
    editor = ProfileEditor.from_seed(seeded.vertices, digest=seeded.digest, name=seeded.name)
    saved = load_profile(editor.save(tmp_path))
    assert saved.provenance.sha256 == seeded.digest
    assert saved.provenance.citation == seeded.name


def test_ver55_the_assess_child_seeds_across_the_boundary(tube_store) -> None:
    """The spawned child posts the seed as plain data, and a case with no stages is refused."""
    _root, store, cases = tube_store
    run_case(cases["refused"], store=store, upto="symmetry", write=False)

    process = AssessProcess(AssessRequest(case=str(cases["refused"]), store=str(store.root)))
    process.start()
    events = _settle(process)
    assert len(events) == 1 and isinstance(events[0], Seeded), events
    assert events[0].seed.assessment.failures[0].criterion == "radius profile"

    empty = AssessProcess(
        AssessRequest(case=str(cases["refused"]), store=str(_root / "empty-store"))
    )
    empty.start()
    events = _settle(empty)
    assert len(events) == 1 and isinstance(events[0], AssessFailed), events
    assert events[0].error == "MissingUpstreamError"
    assert "not in the store" in events[0].message


def test_ver55_an_assess_child_killed_before_it_answers_is_not_called_answered(
    tmp_path: Path,
) -> None:
    """A child that dies by signal posts nothing, and the parent must be able to say so.

    ``answered`` is what the tab reads once the child has exited: still false means the
    measurement died and the status line must not go on saying it is measuring
    (CODE_REVIEW_003 CR-7).
    """
    process = AssessProcess(AssessRequest(case=str(tmp_path / "x.yaml"), store=str(tmp_path)))
    process.start()
    assert not process.answered
    process._process.kill()  # type: ignore[union-attr]
    process.join(TIMEOUT_S)
    assert not process.running
    assert process.drain() == ()
    assert not process.answered


def test_ver55_a_child_that_answers_marks_the_process_answered(tmp_path: Path) -> None:
    """A refusal is an answer: the tab reports its message, not a silent death."""
    process = AssessProcess(
        AssessRequest(case=str(tmp_path / "missing.yaml"), store=str(tmp_path / "store"))
    )
    process.start()
    events = _settle(process)
    assert len(events) == 1 and isinstance(events[0], AssessFailed), events
    assert process.answered


def _settle(process: AssessProcess) -> tuple[object, ...]:
    """Drain until the child posts its one event, or time out."""
    deadline = time.monotonic() + TIMEOUT_S
    found: list[object] = []
    while time.monotonic() < deadline and not found:
        found.extend(process.drain())
        if not found and not process.running:
            time.sleep(0.1)
            found.extend(process.drain())
            break
        time.sleep(0.05)
    process.join(5.0)
    return tuple(found)


REFUSED_WITHOUT_THE_EXTRA = """
import sys
sys.modules["skimage"] = None
sys.modules["skimage.measure"] = None
from nanopnp.core.stages import MissingExtraError
from nanopnp.gui.assess import _contour
try:
    _contour()
except MissingExtraError as error:
    print(error)
"""


def test_ver55_assessing_without_the_structure_extra_names_it() -> None:
    """Without scikit-image the child refuses naming the ``structure`` extra, not the import."""
    completed = subprocess.run(
        [sys.executable, "-c", REFUSED_WITHOUT_THE_EXTRA], capture_output=True, text=True
    )
    assert "needs the 'structure' extra" in completed.stdout, completed.stderr
