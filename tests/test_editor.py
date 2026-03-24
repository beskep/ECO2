from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from eco2.editor import Eco2Editor
from tests.data import ECO2, ROOT

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize('file', ECO2)
def test_editor(file: str, tmp_path: Path):
    src = ROOT / file
    dst = tmp_path / file

    editor = Eco2Editor(src)
    assert editor.xml.area.floor is not None

    (
        editor.xml
        .set_walls(uvalue=42.0)
        .set_windows(uvalue=42.0, shgc=42.0)
        .set_elements('tbl_zone/침기율', '42.0')
    )
    editor.write(dst)

    raw = src.read_bytes()
    edited = dst.read_bytes()
    assert raw != edited
