# ruff: noqa: E402 PGH003 PLC0415

import sys
from pathlib import Path

import pythonnet

pythonnet.load('coreclr')

import clr


class MiniLzoImportError(RuntimeError):
    pass


def load_dll():
    is_frozen = hasattr(sys, 'frozen')
    root = Path(sys.executable).parent if is_frozen else Path(__file__).parents[1]
    p = 'bin/Release/**/MiniLZO.dll'

    try:
        dll = next(root.glob(p))
    except StopIteration:
        raise FileNotFoundError(p) from None

    clr.AddReference(str(dll))  # pylint: disable=no-member # type: ignore


def compress(data: bytes):
    try:
        from MiniLZO import MiniLZO  # type: ignore
    except ImportError:
        raise MiniLzoImportError from None

    return bytes(MiniLZO.CompressBytes(data))


def decompress(data: bytes):
    try:
        from MiniLZO import MiniLZO  # type: ignore
    except ImportError:
        raise MiniLzoImportError from None

    return bytes(MiniLZO.DecompressBytes(data))


if __name__ == '__main__':
    compress(b'42')
