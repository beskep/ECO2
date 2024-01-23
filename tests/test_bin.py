import pytest

from ECO2 import minilzo


def test_load():
    assert minilzo.MiniLZO.TheAnswer() == 42  # noqa: PLR2004


@pytest.mark.parametrize(
    'data',
    [
        b'',
        b'42' * 42,
        b'Life, the Universe and Everything',
    ],
)
def test_compress(data):
    compressed = minilzo.compress(data)
    decompressed = minilzo.decompress(compressed)
    assert data == decompressed
