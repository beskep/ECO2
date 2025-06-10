# pylint: disable=protected-access
# ruff: noqa: SLF001
from __future__ import annotations

from pathlib import Path
from shutil import copy2

import pytest
from lxml.etree import _Element  # noqa: PLC2701

from eco.eco2 import Eco2
from eco.eco2xml import Eco2Xml
from tests import data


@pytest.mark.parametrize('file', data.ECO2)
def test_eco2(file: str, tmp_path: Path):
    src = tmp_path / file
    suffix = src.suffix.lower()
    is_eco = suffix.startswith(Eco2.ECO_EXT)
    is_x = suffix.endswith('x')

    copy2(src=data.ROOT / file, dst=src)

    header = src.with_suffix(Eco2.HEADER_EXT)
    xml = src.with_suffix(Eco2.XML_EXT)
    encrypted = tmp_path / f'{src.stem}-encrypted{Eco2.ECO_EXT}'

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)

    Eco2.decrypt_and_write(src=src)

    header_data, xml_data = Eco2.decrypt(
        src.read_bytes(),
        decrypt=is_eco,
        decompress=is_x,
    )

    if not suffix.endswith('x'):
        assert header_data == header.read_bytes()

    # 추출한 XML 중 DS 부분만 비교
    assert Eco2._split_xml(xml_data)[0] == Eco2._read_xml(xml, dsr=False)

    Eco2.encrypt_and_write(header=header, xml=xml, dst=encrypted)

    if is_eco and not is_x:
        assert src.read_bytes() == encrypted.read_bytes()

    header.unlink(missing_ok=True)
    xml.unlink(missing_ok=True)
    encrypted.unlink(missing_ok=True)


@pytest.mark.parametrize('file', data.ECO2)
def test_eco2xml(file: str, tmp_path: Path):
    path = data.ROOT / file
    if not (xml := path.with_suffix(Eco2.XML_EXT)).exists():
        Eco2.decrypt_and_write(path, write_header=False)

    eco = Eco2Xml(xml)

    assert isinstance(eco.source, Path)
    assert isinstance(eco.ds, _Element)
    assert eco.dsr is None or isinstance(eco.dsr, _Element)

    assert (
        xml.read_text('UTF-8')
        .replace(' />', '/>')
        .removesuffix('\n<DSR xmlns="http://tempuri.org/DSR.xsd"/>')
        == eco.tostring()
    )

    assert next(eco.iterfind('weather_cha')) is not None

    eco.write(tmp_path / 'tmp')


@pytest.mark.parametrize('file', data.ECO2OD)
def test_eco2xml_eco2od(file: str):
    eco = Eco2Xml(data.ROOT / file)
    assert next(eco.iterfind('tbl_profile_od')) is not None
