from pathlib import Path

import pytest

from eco.cli import app
from eco.eco2 import Eco2
from tests.data import data_dir, files


@pytest.mark.parametrize('file', files)
def test_cli_input_file(file, tmp_path: Path):
    header = tmp_path.joinpath(file).with_suffix(Eco2.HEXT)
    xml = tmp_path.joinpath(file).with_suffix(Eco2.XEXT)

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)

    # decrypt
    args = ['-d', 'decrypt', data_dir / file, '--dst', xml.parent]
    app.meta(list(map(str, args)))

    assert header.exists(), header
    assert xml.exists(), xml

    encrypted = (tmp_path / file).with_suffix(Eco2.EEXT)
    encrypted.unlink(missing_ok=True)

    # encrypt
    args = ['-d', 'encrypt', xml, '--header', header, '--dst', tmp_path]
    app.meta(list(map(str, args)))

    assert encrypted.exists(), encrypted

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)


def test_cli_input_dir(tmp_path: Path):
    args = ['--debug', 'decrypt', data_dir, '--dst', tmp_path, '--header']
    app.meta(list(map(str, args)))

    for file in files:
        header = (tmp_path / file).with_suffix(Eco2.HEXT)
        xml = (tmp_path / file).with_suffix(Eco2.XEXT)
        assert header.exists(), header
        assert xml.exists(), xml

    args = ['--debug', 'encrypt', tmp_path]
    app.meta(list(map(str, args)))
    for file in files:
        f = (tmp_path / file).with_suffix(Eco2.EEXT)
        assert f.exists(), f
