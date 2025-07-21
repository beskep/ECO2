import pytest
from lxml.etree import _Element  # noqa: PLC2701

from eco2 import Eco2, Eco2Xml
from tests.data import ECO2, ECO2OD, ROOT


@pytest.mark.parametrize('file', ECO2)
def test_eco2(file: str):
    src = ROOT / file
    eco = Eco2.read(src=src)

    if src.suffix.lower() == '.tpl':
        assert src.read_bytes() == eco.encrypt(xor=False, compress=False)


@pytest.mark.parametrize('file', ECO2)
def test_eco2xml(file: str):
    eco = Eco2.read(ROOT / file)

    if not (p := (ROOT / file).with_suffix('.xml')).exists():
        p.write_text(eco.xml)

    for xml in [
        Eco2Xml.create(eco),
        Eco2Xml.create(eco.xml),
        Eco2Xml.create(eco.xml.encode()),
        Eco2Xml.read(ROOT / file),
        Eco2Xml.read(p),
    ]:
        assert isinstance(xml.ds, _Element)
        assert xml.dsr is None or isinstance(xml.dsr, _Element)
        assert next(xml.iterfind('weather_cha')) is not None
        assert '<DS xmlns="http://tempuri.org/DS.xsd">' in xml.tostring()


@pytest.mark.parametrize('file', ECO2OD)
def test_eco2xml_eco2od(file: str):
    eco = Eco2Xml.read(ROOT / file)
    assert next(eco.iterfind('tbl_profile_od')) is not None
