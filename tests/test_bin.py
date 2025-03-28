from __future__ import annotations

import pytest

from eco import minilzo

minilzo.load_dll()


def test_load():
    from MiniLZO import MiniLZO  # type: ignore # noqa: PGH003 PLC0415

    assert MiniLZO.TheAnswer() == 42  # noqa: PLR2004


@pytest.mark.parametrize('data', [b'', b'42' * 2])
def test_compress(data):
    compressed = minilzo.compress(data)
    decompressed = minilzo.decompress(compressed)
    assert data == decompressed
