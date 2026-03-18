import shutil
from pathlib import Path

import pytest

from eco2.cli import app
from tests.data import ECO2, ROOT

EXTENSIONS = ('eco', 'ecox', 'tpl', 'tplx')


@pytest.mark.parametrize('src', ECO2)
@pytest.mark.parametrize('x', [False, True])
def test_convert(tmp_path: Path, src, x):
    shutil.copy2(ROOT / src, tmp_path)

    with pytest.raises(SystemExit):
        app(['convert', str(tmp_path), '--x' if x else '--no-x'])

    ext = {'.eco': '.tpl', '.tpl': '.eco'}[Path(src).suffix.lower().rstrip('x')]
    if x:
        ext = f'{ext}x'

    dst = (tmp_path / src).with_suffix(ext)
    assert dst.exists(), dst


@pytest.mark.parametrize('file', ECO2)
@pytest.mark.parametrize('ext', EXTENSIONS)
def test_cli_input_file(file: str, ext: str, tmp_path: Path):
    header = (tmp_path / file).with_suffix('.json')
    xml = (tmp_path / file).with_suffix('.xml')

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)

    # decrypt
    args = ['--debug', 'decrypt', ROOT / file, '--output', xml.parent, '--header']
    with pytest.raises(SystemExit):
        app.meta(list(map(str, args)))

    assert header.exists(), header
    assert xml.exists(), xml

    encrypted = (tmp_path / file).with_suffix(f'.{ext}')
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
        '--extension',
        ext,
        '--dsr',
    ]
    with pytest.raises(SystemExit):
        app.meta(list(map(str, args)))

    assert encrypted.exists(), encrypted

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)


def test_cli_input_dir(tmp_path: Path):
    args = ['--debug', 'decrypt', ROOT, '--output', tmp_path, '--header']
    with pytest.raises(SystemExit):
        app.meta(list(map(str, args)))

    for file in ECO2:
        header = (tmp_path / file).with_suffix('.json')
        xml = (tmp_path / file).with_suffix('.xml')
        assert header.exists(), header
        assert xml.exists(), xml

    args = ['--debug', 'encrypt', tmp_path, '--output', tmp_path, '--no-dsr']
    with pytest.raises(SystemExit):
        app.meta(list(map(str, args)))
    for file in ECO2:
        f = (tmp_path / file).with_suffix('.ecox')
        assert f.exists(), f
