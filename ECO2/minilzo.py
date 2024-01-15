# pylint: disable=no-member, wrong-import-position
# ruff: noqa: E402

import sys
from pathlib import Path

import clr

IS_FROZEN = hasattr(sys, 'frozen')
root = Path(sys.executable).parent if IS_FROZEN else Path(__file__).parents[1]
dll = root / 'bin/MiniLZO.dll'
assert dll.exists()

clr.AddReference(str(dll))

from MiniLZO import MiniLZO


def compress(data: bytes):
    return bytes(MiniLZO.CompressBytes(data))


def decompress(data: bytes):
    return bytes(MiniLZO.DecompressBytes(data))
