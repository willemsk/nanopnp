from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.api.reproduce import check_inputs
from nanopnp.io.manifest import CASE_FILENAME, Manifest, input_group, read
from nanopnp.pipeline.run import _run_key

CASE_HASH = "0" * 64


def _manifest(source: Path, case_hash: str = CASE_HASH, **files: Path) -> Manifest:
    return Manifest(
        case_text=source.read_bytes().decode("utf-8"),
        case_hash=case_hash,
        inputs=input_group(case_hash=case_hash, files={"case": source, **files}),
        environment={},
        geometry_and_mesh={},
        charge={},
        materials={},
        solver={},
        stabilisation={},
    )


@pytest.mark.parametrize("newline", [b"\r\n", b"\n"], ids=["crlf", "lf"])
def test_qr08_case_file_bytes_survive_the_manifest_round_trip(
    tmp_path: Path, newline: bytes
) -> None:
    # Catches a case file rewritten with platform line endings, so that its recorded sha256
    # no longer matches the run directory's copy and reproduce refuses the run as moved.
    source = tmp_path / "source.yaml"
    source.write_bytes(b"schema: x" + newline + b"name: y" + newline)
    run = tmp_path / "run"

    _manifest(source).write(run)

    assert (run / CASE_FILENAME).read_bytes() == source.read_bytes()
    check_inputs(read(run / "manifest.json"), where=run)


def test_qr08_the_run_key_moves_with_the_contents_of_an_input_file(tmp_path: Path) -> None:
    # Catches a regenerated mesh at the same path overwriting the earlier run's directory.
    source = tmp_path / "source.yaml"
    source.write_bytes(b"schema: x\n")
    mesh = tmp_path / "pore.msh"

    mesh.write_bytes(b"first")
    first = _run_key(_manifest(source, mesh=mesh))
    assert first == _run_key(_manifest(source, mesh=mesh))
    mesh.write_bytes(b"second")
    assert _run_key(_manifest(source, mesh=mesh)) != first
