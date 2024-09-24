from pathlib import Path

import pytest

from eco.cli import app
from eco.eco2 import Eco2
from tests.data import DATA_DIR, FILES


@pytest.mark.parametrize('file', FILES)
def test_cli_input_file(file: str, tmp_path: Path):
    header = tmp_path.joinpath(file).with_suffix(Eco2.HEXT)
    xml = tmp_path.joinpath(file).with_suffix(Eco2.XEXT)

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)

    # decrypt
    args = ['--debug', 'decrypt', DATA_DIR / file, '--output', xml.parent, '--header']
    app.meta(list(map(str, args)))

    assert header.exists(), header
    assert xml.exists(), xml

    encrypted = (tmp_path / file).with_suffix(Eco2.EEXT)
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
        '-d',
        'decrypt',
        DATA_DIR,
        '-o',
        tmp_path,
        '-H',
    ]
    app.meta(list(map(str, args)))

    for file in FILES:
        header = (tmp_path / file).with_suffix(Eco2.HEXT)
        xml = (tmp_path / file).with_suffix(Eco2.XEXT)
        assert header.exists(), header
        assert xml.exists(), xml

    args = ['-d', 'encrypt', tmp_path, '-o', tmp_path, '-s', '10', '--no-dsr']
    app.meta(list(map(str, args)))
    for file in FILES:
        f = (tmp_path / file).with_suffix(Eco2.EEXT)
        assert f.exists(), f
