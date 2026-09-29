"""VER-55 — the artefact hook reports what each stage left in the store, and keys nothing.

The desktop shell's geometry views read each stage's payload as it lands
(WP24 D1). The hook that tells them where it landed fires *after* the artefact
is in the store, carries its schema and hash as the run record will, and says
whether the store already held it. What makes it safe is the same property the
solve hook has (VER-44): it is bound after every key is taken and is handed none,
so a watched walk and an unwatched one produce one run record and one set of
store entries (WP24 D2, section 5.3.2).

On the coarse synthetic profile of ``test_mesh_generate.py``, so a walk through
stage 6 takes a fraction of a second.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest

from nanopnp.core.stages import ArtefactHook
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.mesh.profile import (
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
    write_profile,
)

CASE = """\
schema: nanopnp/case/v2
name: hooked
inputs:
  profile: {{path: {path}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: 20.0}}}}
"""


def _write_parallelogram(path: Path) -> Path:
    """Write a slanted body 1 nm wide across the slab as a profile document."""
    points = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
    array = np.asarray(points, dtype=np.float64)
    profile = PoreProfile(
        schema=PROFILE_SCHEMA,
        name="parallelogram",
        provenance=ProfileProvenance(
            source="test",
            citation="tests/tier1/test_artefact_hook.py",
            sha256="0" * 64,
            vertex_count=len(points),
            min_vertex_spacing_nm=min_vertex_spacing(array),
            min_feature_size_nm=min_feature_size(array),
            signed_area_nm2=signed_area(array),
        ),
        vertices=points,
    )
    return write_profile(profile, path)


@pytest.fixture(scope="module")
def case_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the synthetic profile and the case naming it."""
    root = tmp_path_factory.mktemp("hook")
    profile = _write_parallelogram(root / "profile.yaml")
    path = root / "case.yaml"
    path.write_text(CASE.format(path=profile), encoding="utf-8")
    return path


@dataclass
class Recorder:
    """An :class:`ArtefactHook` that notes each call and checks the store at that moment."""

    store: Store
    calls: list[tuple[str, str, str, bool]] = field(default_factory=list)
    present: list[bool] = field(default_factory=list)

    def __call__(self, name: str, schema: str, hash: str, cached: bool) -> None:
        """Record the call, and whether the entry it names can be read yet."""
        self.calls.append((name, schema, hash, cached))
        # A fresh reader, as the shell's is: nothing of the walk's own Store object.
        self.present.append(Store(self.store.root).get(schema, hash) is not None)


def _entries(store: Store) -> set[str]:
    """Return every artefact directory the store holds, relative to its root."""
    root = store.root / "artefacts"
    return {str(path.relative_to(root)) for path in root.glob("*/*/*") if path.is_dir()}


def test_ver55_the_hook_fires_after_each_stage_is_stored(case_file: Path, tmp_path: Path) -> None:
    """Once per walked stage, with the run record's schema and hash, after the entry exists."""
    store = Store(tmp_path / "store")
    recorder = Recorder(store)
    hook: ArtefactHook = recorder
    result = run_case(case_file, store=store, upto="mesh", write=False, on_artefact=hook)

    assert [call[0] for call in recorder.calls] == ["case", "region", "mesh"]
    assert recorder.calls == [
        (record.name, record.schema, record.hash, record.cached) for record in result.stages
    ]
    assert all(recorder.present), recorder.calls
    assert not any(call[3] for call in recorder.calls)


def test_ver55_a_rerun_reports_every_stage_cached(case_file: Path, tmp_path: Path) -> None:
    """A cached stage still has an artefact to show, so it is reported, as cached (D1)."""
    store = Store(tmp_path / "store")
    first = run_case(case_file, store=store, upto="mesh", write=False)
    recorder = Recorder(store)
    second = run_case(
        case_file, store=Store(store.root), upto="mesh", write=False, on_artefact=recorder
    )

    assert [call[3] for call in recorder.calls] == [True, True, True]
    assert [call[2] for call in recorder.calls] == [record.hash for record in first.stages]
    assert [record.hash for record in second.stages] == [record.hash for record in first.stages]


def test_ver55_a_watched_walk_keys_what_an_unwatched_one_keys(
    case_file: Path, tmp_path: Path
) -> None:
    """One run record and one set of store entries, watched or not (D2, section 5.3.2)."""
    quiet = Store(tmp_path / "quiet")
    watched = Store(tmp_path / "watched")
    unwatched_result = run_case(case_file, store=quiet, upto="mesh")
    watched_result = run_case(case_file, store=watched, upto="mesh", on_artefact=Recorder(watched))

    def stripped(record: dict[str, object]) -> dict[str, object]:
        # Wall time and the two stores' own roots are the only things allowed to differ.
        stages = [
            {key: value for key, value in stage.items() if key != "seconds"}
            for stage in record["stages"]  # type: ignore[attr-defined]
        ]
        return {
            **{key: value for key, value in record.items() if key not in ("directory", "store")},
            "stages": stages,
        }

    assert stripped(watched_result.record()) == stripped(unwatched_result.record())
    assert _entries(watched) == _entries(quiet)
    assert watched_result.manifest.hash == unwatched_result.manifest.hash
