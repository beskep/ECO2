from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from eco.cli import app
from eco.eco2 import Eco2
from tests.data import ECO2, ROOT

if TYPE_CHECKING:
    from pathlib import Path


def test_empty_path(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        app(['decrypt', str(tmp_path)])

    with pytest.raises(FileNotFoundError):
        app(['encrypt', str(tmp_path)])


@pytest.mark.parametrize('file', ECO2)
def test_cli_input_file(file: str, tmp_path: Path):
    header = tmp_path.joinpath(file).with_suffix(Eco2.HEADER_EXT)
    xml = tmp_path.joinpath(file).with_suffix(Eco2.XML_EXT)

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)

    # decrypt
    args = ['--debug', 'decrypt', ROOT / file, '--output', xml.parent, '--header']
    app.meta(list(map(str, args)))

    assert header.exists(), header
    assert xml.exists(), xml

    encrypted = (tmp_path / file).with_suffix(Eco2.ECO_EXT)
    encrypted.unlink(missing_ok=True)

    # encrypt
    args = [
        '--debug',
        'encrypt',
        xml,
        '--header',
        header,
        '--output',
        tmp_path,
        '--sftype',
        '10',
        '--dsr',
    ]
    app.meta(list(map(str, args)))

    assert encrypted.exists(), encrypted

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)


def test_cli_input_dir(tmp_path: Path):
    args = [
        '--debug',
        'decrypt',
        ROOT,
        '--output',
        tmp_path,
        '--header',
    ]
    app.meta(list(map(str, args)))

    for file in ECO2:
        header = (tmp_path / file).with_suffix(Eco2.HEADER_EXT)
        xml = (tmp_path / file).with_suffix(Eco2.XML_EXT)
        assert header.exists(), header
        assert xml.exists(), xml

    args = [
        '--debug',
        'encrypt',
        tmp_path,
        '--output',
        tmp_path,
        '--sftype',
        '10',
        '--no-dsr',
    ]
    app.meta(list(map(str, args)))
    for file in ECO2:
        f = (tmp_path / file).with_suffix(Eco2.ECO_EXT)
        assert f.exists(), f
