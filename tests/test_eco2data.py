from pathlib import Path

import pytest
from lxml.etree import _Element  # pylint: disable=no-name-in-module  # noqa: PLC2701

from eco.eco2 import Eco2
from eco.eco2data import Eco2Data
from tests.data import data_dir, files


@pytest.mark.parametrize('file', files)
def test_eco2data(file: Path):
    path = data_dir / file
    if not (xml := path.with_suffix(Eco2.VEXT)).exists():
        Eco2.decrypt(path, write_header=False)

    data = Eco2Data(xml)

    assert isinstance(data.xml, Path)
    assert isinstance(data.ds, _Element)
    assert data.dsr is None or isinstance(data.dsr, _Element)

    # TODO eco2data typing, test cover
