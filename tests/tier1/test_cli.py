"""The console-script entry point resolves and reports the environment."""

from nanopnp import __version__
from nanopnp.cli import main
from nanopnp.core.paths import correction_file


def test_cli_env_reports_data_location(capsys):
    assert main(["--env"]) == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "corrections" in out


def test_packaged_correction_file_is_installed():
    assert correction_file("willems2020_nacl").is_file()
