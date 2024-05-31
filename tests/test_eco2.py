# pylint: disable=protected-access
# ruff: noqa: SLF001

from pathlib import Path
from shutil import copy2

import pytest
from lxml.etree import _Element  # noqa: PLC2701

from eco.eco2 import Eco2
from eco.eco2xml import Eco2Xml
from tests.data import data_dir, files


@pytest.mark.parametrize('file', files)
def test_eco2(file, tmp_path: Path):
    path = tmp_path / file
    suffix = path.suffix.lower()
    is_eco = suffix == Eco2.EEXT

    copy2(src=data_dir / file, dst=path)

    header = path.with_suffix(Eco2.HEXT)
    xml = path.with_suffix(Eco2.XEXT)
    encrypted = tmp_path / f'{path.stem}-encrypted{Eco2.EEXT}'

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)

    Eco2.decrypt(src=path)

    header_data, xml_data = Eco2._decrypt(path.read_bytes(), decrypt=is_eco)

    if not suffix.endswith('x'):
        assert header_data == header.read_bytes()

    if is_eco:
        # tpl 파일의 경우 결과부 (<DSR>)이 제거되어 xml가 달라질 수 있음
        assert hash(xml_data) == hash(Eco2._read_xml(xml))

    Eco2.encrypt(header=header, xml=xml, dst=encrypted)

    if is_eco:
        data = path.read_bytes()
        assert hash(data) == hash(encrypted.read_bytes())

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)


@pytest.mark.parametrize('file', files)
def test_eco2xml(file: Path):
    path = data_dir / file
    if not (xml := path.with_suffix(Eco2.XEXT)).exists():
        Eco2.decrypt(path, write_header=False)

    eco = Eco2Xml(xml)

    assert isinstance(eco.path, Path)
    assert isinstance(eco.ds, _Element)
    assert eco.dsr is None or isinstance(eco.dsr, _Element)

    assert (
        xml.read_text('UTF-8')
        .replace(' />', '/>')
        .removesuffix('\n<DSR xmlns="http://tempuri.org/DSR.xsd"/>')
        == eco.tostring()
    )
