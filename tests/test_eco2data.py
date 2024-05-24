from pathlib import Path

import pytest
from lxml.etree import _Element  # noqa: PLC2701

from eco.eco2 import Eco2
from eco.eco2data import Eco2Xml
from tests.data import data_dir, files


@pytest.mark.parametrize('file', files)
def test_eco2data(file: Path):
    path = data_dir / file
    if not (xml := path.with_suffix(Eco2.VEXT)).exists():
        Eco2.decrypt(path, write_header=False)

    data = Eco2Xml(xml)

    assert isinstance(data.path, Path)
    assert isinstance(data.ds, _Element)
    assert data.dsr is None or isinstance(data.dsr, _Element)

    assert (
        xml.read_text('UTF-8')
        .replace(' />', '/>')
        .removesuffix('\n<DSR xmlns="http://tempuri.org/DSR.xsd"/>')
        == data.tostring()
    )
