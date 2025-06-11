from __future__ import annotations

import io

import pytest
from lxml.etree import _Element  # noqa: PLC2701

from eco2 import Eco2, Eco2Xml
from tests.data import ECO2, ECO2OD, ROOT


@pytest.mark.parametrize('file', ECO2)
def test_eco2(file: str):
    src = ROOT / file
    eco = Eco2.read(src=src)

    if src.suffix == '.eco':
        eco.xml = eco.xml.replace('\n', '\r\n')
        assert src.read_bytes() == eco.encrypt()


@pytest.mark.parametrize('file', ECO2)
def test_eco2xml(file: str):
    eco = Eco2.read(ROOT / file)
    xml = Eco2Xml(io.StringIO(eco.xml))

    assert isinstance(xml.ds, _Element)
    assert xml.dsr is None or isinstance(xml.dsr, _Element)

    assert xml.tostring() == eco.xml.replace(' />', '/>').removesuffix(
        '\n<DSR xmlns="http://tempuri.org/DSR.xsd"/>'
    )

    assert next(xml.iterfind('weather_cha')) is not None


@pytest.mark.parametrize('file', ECO2OD)
def test_eco2xml_eco2od(file: str):
    eco = Eco2Xml(ROOT / file)
    assert next(eco.iterfind('tbl_profile_od')) is not None
