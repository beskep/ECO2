import shutil
from pathlib import Path

import pytest

from eco2.cli import app
from tests.data import ECO2, ROOT


def test_convert(tmp_path: Path):
    for file in ECO2:
        shutil.copy2(ROOT / file, tmp_path)

    app(['convert', str(tmp_path)])

    for src in ECO2:
        ext = '.eco' if Path(src).suffix.lower().startswith('.tpl') else '.tpl'
        dst = (tmp_path / src).with_suffix(ext)
        assert dst.exists(), dst


def test_empty_path(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        app(['decrypt', str(tmp_path)])

    with pytest.raises(FileNotFoundError):
        app(['encrypt', str(tmp_path)])


@pytest.mark.parametrize('file', ECO2)
def test_cli_input_file(file: str, tmp_path: Path):
    header = (tmp_path / file).with_suffix('.json')
    xml = (tmp_path / file).with_suffix('.xml')

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)

    # decrypt
    args = ['--debug', 'decrypt', ROOT / file, '--output', xml.parent, '--header']
    app.meta(list(map(str, args)))

    assert header.exists(), header
    assert xml.exists(), xml

    encrypted = (tmp_path / file).with_suffix('.eco')
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
        '--dsr',
    ]
    app.meta(list(map(str, args)))

    assert encrypted.exists(), encrypted

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)


def test_cli_input_dir(tmp_path: Path):
    args = ['--debug', 'decrypt', ROOT, '--output', tmp_path, '--header']
    app.meta(list(map(str, args)))

    for file in ECO2:
        header = (tmp_path / file).with_suffix('.json')
        xml = (tmp_path / file).with_suffix('.xml')
        assert header.exists(), header
        assert xml.exists(), xml

    args = ['--debug', 'encrypt', tmp_path, '--output', tmp_path, '--no-dsr']
    app.meta(list(map(str, args)))
    for file in ECO2:
        f = (tmp_path / file).with_suffix('.eco')
        assert f.exists(), f
