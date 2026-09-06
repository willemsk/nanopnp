"""The console-script entry point resolves and reports the environment."""

from nanopnp import __version__
from nanopnp.cli import main
from nanopnp.core.paths import (
    REFERENCE_DATA_VARIABLE,
    correction_file,
    reference_data_root,
    reference_file,
)


def test_cli_env_reports_data_location(capsys):
    assert main(["--env"]) == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "corrections" in out


def test_packaged_correction_file_is_installed():
    assert correction_file("willems2020_nacl").is_file()


def test_val15_the_reference_archive_is_absent_rather_than_broken(monkeypatch, tmp_path):
    """An unset, misdirected or incomplete archive all read as "not available".

    Tier 3 compares against reference files far too large to vendor, and the
    skip condition that keeps that tier runnable elsewhere is exactly this
    ``None``. An exception here would turn "you do not have the archive" into a
    failing test run for everyone who does not (section 7.1).
    """
    monkeypatch.delenv(REFERENCE_DATA_VARIABLE, raising=False)
    assert reference_data_root() is None
    assert reference_file("prod5_clya_charge") is None

    monkeypatch.setenv(REFERENCE_DATA_VARIABLE, str(tmp_path / "absent"))
    assert reference_data_root() is None

    monkeypatch.setenv(REFERENCE_DATA_VARIABLE, str(tmp_path))
    assert reference_data_root() == tmp_path.resolve()
    assert reference_file("prod5_clya_charge") is None

    (tmp_path / "prod5_clya_charge").write_text("%Grid\n", encoding="utf-8")
    assert reference_file("prod5_clya_charge") == tmp_path.resolve() / "prod5_clya_charge"
