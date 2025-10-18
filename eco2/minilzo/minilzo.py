# ruff: noqa: D101 D103 PLC0415
import sys
from pathlib import Path

import pythonnet

pythonnet.load('coreclr')

import clr  # noqa: E402


class MiniLzoDllNotFoundError(FileNotFoundError):
    pass


class MiniLzoImportError(RuntimeError):
    def __init__(self, *args: object) -> None:
        super().__init__('Cannot import MiniLZO.dll', *args)


def find_dll() -> Path:
    is_frozen = hasattr(sys, 'frozen')
    root = Path(sys.executable).parent if is_frozen else Path()
    p = '**/bin/Release/**/MiniLZO.dll'

    try:
        return next(root.glob(p)).absolute()
    except StopIteration:
        raise MiniLzoDllNotFoundError(p) from None


def load_dll(path: str | Path | None = None) -> None:
    path = path or find_dll()
    clr.AddReference(str(path))


def compress(data: bytes) -> bytes:
    try:
        from MiniLZO import MiniLZO
    except ImportError:
        raise MiniLzoImportError from None

    return bytes(MiniLZO.CompressBytes(data))


def decompress(data: bytes) -> bytes:
    try:
        from MiniLZO import MiniLZO
    except ImportError:
        raise MiniLzoImportError from None

    return bytes(MiniLZO.DecompressBytes(data))


if __name__ == '__main__':
    import subprocess as sp  # noqa: S404

    import rich
    from cyclopts import App

    app = App()
    cnsl = rich.get_console()

    @app.default
    def test() -> None:
        load_dll()
        b = b'forty two'
        c = compress(b)
        cnsl.print(f'original    ={b!r}')
        cnsl.print(f'compressed  ={c!r}')
        cnsl.print(f'decompressed={decompress(c)!r}')

    @app.command
    def dotnet_new() -> None:
        """Dotnet new (다시 실행할 필요 없음)."""
        args = 'dotnet new console --framework net7.0 --name MiniLZO --output . --force'
        sp.check_output(args)  # noqa: S603

    @app.command
    def dotnet_build() -> None:
        """Build minilzo."""
        args = ['dotnet', 'build', '--configuration', 'Release']
        p = sp.Popen(args, stdin=sp.PIPE, stderr=sp.STDOUT)  # noqa: S603

        while p.poll() is None:
            if p.stdout is not None:
                cnsl.print(p.stdout.readline(), end='')

    app()
