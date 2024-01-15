# pylint: disable=protected-access
# ruff: noqa: SLF001

from pathlib import Path
from shutil import copy2

import pytest

from ECO2.eco2 import Eco2
from tests.data import data_dir, files


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

    suffix = data_path.suffix.lower()
    is_eco = suffix == Eco2.EEXT

    Eco2.decrypt(path=data_path)

    header, value = Eco2._decrypt(data_path.read_bytes(), decrypt=is_eco)
    saved_header = header_path.read_bytes()
    saved_value = Eco2._read_value(value_path)

    if not suffix.endswith('x'):
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
