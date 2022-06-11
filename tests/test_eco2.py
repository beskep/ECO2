from pathlib import Path
from shutil import copy2

from click.testing import CliRunner
import pytest

from ECO2.cli import cli
from ECO2.eco2 import Eco2

data_dir = Path(__file__).parent.joinpath('data')
files = ['test_eco.eco', 'test_tpl.tpl']


@pytest.mark.parametrize('file', files)
def test_eco2(file, tmp_path: Path):
    data_path = tmp_path.joinpath(file)
    copy2(src=data_dir.joinpath(file), dst=data_path)

    header_path = data_path.with_suffix(Eco2.HEXT)
    value_path = data_path.with_suffix(Eco2.VEXT)
    encrypted_path = tmp_path.joinpath(f'{data_path.stem}-encrypted.eco')

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)

    is_eco = data_path.suffix == '.eco'

    Eco2.decrypt(path=data_path)

    header, value = Eco2._decrypt(data_path.read_bytes(), decrypt=is_eco)
    saved_header = header_path.read_bytes()
    saved_value = Eco2._read_value(value_path)

    assert header == saved_header

    if is_eco:
        # tpl 파일의 경우 결과부 (<DSR>)이 제거되어 value가 달라질 수 있음
        assert hash(value) == hash(saved_value)

    Eco2.encrypt(header=header_path, value=value_path, save=encrypted_path)

    eco2 = data_path.read_bytes()
    encrypted = encrypted_path.read_bytes()

    if is_eco:
        assert hash(eco2) == hash(encrypted)

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)


@pytest.mark.parametrize('file', files)
def test_cli_input_file(file, tmp_path: Path):
    data_path = tmp_path.joinpath(file)
    copy2(src=data_dir.joinpath(file), dst=tmp_path)

    header_path = data_path.with_suffix(Eco2.HEXT)
    value_path = data_path.with_suffix(Eco2.VEXT)
    encrypted_path = tmp_path.joinpath(f'{data_path.stem}-encrypted.eco')

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)

    runner = CliRunner()
    runner.invoke(cli, [
        '-d',
        'decrypt',
        '--output',
        value_path.as_posix(),
        data_path.as_posix(),
    ])

    assert header_path.exists(), header_path
    assert value_path.exists(), value_path

    runner.invoke(cli, [
        '-d',
        'encrypt',
        '--header',
        header_path.as_posix(),
        '--output',
        encrypted_path.as_posix(),
        value_path.as_posix(),
    ])

    assert encrypted_path.exists(), encrypted_path

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)


def test_cli_input_dir(tmp_path: Path):
    for file in files:
        copy2(src=data_dir.joinpath(file), dst=tmp_path)

    runner = CliRunner()
    runner.invoke(cli, ['--debug', 'decrypt', tmp_path.as_posix()])

    for file in files:
        data_path = tmp_path.joinpath(file)
        data_path.unlink()

        header = data_path.with_suffix(Eco2.HEXT)
        value = data_path.with_suffix(Eco2.VEXT)
        assert header.exists(), header
        assert value.exists(), value

    runner.invoke(cli, ['--debug', 'encrypt', tmp_path.as_posix()])
    for file in files:
        assert tmp_path.joinpath(file).with_suffix('.eco').exists()


if __name__ == '__main__':
    pytest.main()
