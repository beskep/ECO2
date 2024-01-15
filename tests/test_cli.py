from pathlib import Path

import pytest
from typer.testing import CliRunner

from ECO2.cli import app
from ECO2.eco2 import Eco2
from tests.data import data_dir, files

runner = CliRunner()


@pytest.mark.parametrize('file', files)
def test_cli_input_file(file, tmp_path: Path):
    header = tmp_path.joinpath(file).with_suffix(Eco2.HEXT)
    value = tmp_path.joinpath(file).with_suffix(Eco2.VEXT)

    header.unlink(missing_ok=True)
    value.unlink(missing_ok=True)

    # decrypt
    args = ['-d', 'decrypt', '--output', value.parent, data_dir / file]
    runner.invoke(app, list(map(str, args)))

    assert header.exists(), header
    assert value.exists(), value

    encrypted = tmp_path.joinpath(file).with_suffix(Eco2.EEXT)
    encrypted.unlink(missing_ok=True)

    # encrypt
    args = ['-d', 'encrypt', '--header', header, '--output', tmp_path, value]
    runner.invoke(app, list(map(str, args)))

    assert encrypted.exists(), encrypted

    header.unlink(missing_ok=True)
    value.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)


def test_cli_input_dir(tmp_path: Path):
    args = ['--debug', 'decrypt', '--output', tmp_path, data_dir]
    runner.invoke(app, list(map(str, args)))

    for file in files:
        header = tmp_path.joinpath(file).with_suffix(Eco2.HEXT)
        value = tmp_path.joinpath(file).with_suffix(Eco2.VEXT)
        assert header.exists(), header
        assert value.exists(), value

    args = ['--debug', 'encrypt', tmp_path]
    runner.invoke(app, list(map(str, args)))
    for file in files:
        f = tmp_path.joinpath(file).with_suffix(Eco2.EEXT)
        assert f.exists(), f
