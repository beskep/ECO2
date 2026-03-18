import pytest

from eco2 import minilzo


@pytest.mark.parametrize(
    'data',
    [
        b'',
        b'3.14159265358979323846',
        b"I thought what I'd do was, I'd pretend I was one of those deaf-mutes.",
    ],
)
def test_compress(data):
    compressed = minilzo.compress(data)
    decompressed = minilzo.decompress(compressed)
    assert data == decompressed
