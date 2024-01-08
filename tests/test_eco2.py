# pylint: disable=protected-access
# ruff: noqa: SLF001

from pathlib import Path
from shutil import copy2

import pytest
from lxml.etree import _Element  # pylint: disable=no-name-in-module
from typer.testing import CliRunner

from ECO2.cli import app
from ECO2.eco2 import Eco2
from ECO2.eco2data import Eco2Data

data_dir = Path(__file__).parent / 'data'
files = ['test_eco.eco', 'test_tpl.tpl']


runner = CliRunner()


@pytest.mark.parametrize('file', files)
def test_eco2(file, tmp_path: Path):
    data_path = tmp_path / file
    copy2(src=data_dir / file, dst=data_path)

    header_path = data_path.with_suffix(Eco2.HEXT)
    value_path = data_path.with_suffix(Eco2.VEXT)
    encrypted_path = tmp_path / f'{data_path.stem}-encrypted{Eco2.EEXT}'

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)

    is_eco = data_path.suffix == Eco2.EEXT

    Eco2.decrypt(path=data_path)

    header, value = Eco2._decrypt(data_path.read_bytes(), decrypt=is_eco)
    saved_header = header_path.read_bytes()
    saved_value = Eco2._read_value(value_path)

    assert header == saved_header

    if is_eco:
        # tpl 파일의 경우 결과부 (<DSR>)이 제거되어 value가 달라질 수 있음
        assert hash(value) == hash(saved_value)

    Eco2.encrypt(header=header_path, value=value_path, path=encrypted_path)

    eco2 = data_path.read_bytes()
    encrypted = encrypted_path.read_bytes()

    if is_eco:
        assert hash(eco2) == hash(encrypted)

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)


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


@pytest.mark.parametrize('file', files)
def test_eco2data(file: Path):
    path = data_dir / file
    if not (xml := path.with_suffix(Eco2.VEXT)).exists():
        Eco2.decrypt(path, write_header=False)

    data = Eco2Data(xml)

    assert isinstance(data.xml, Path)
    assert isinstance(data.ds, _Element)
    assert data.dsr is None or isinstance(data.dsr, _Element)

    # TODO eco2data typing, test cover
