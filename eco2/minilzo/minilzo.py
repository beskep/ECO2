# ruff: noqa: S404 S603
import subprocess as sp
import sys
import tempfile
from pathlib import Path


class MiniLzoNotFoundError(FileNotFoundError):
    """MiniLZO.exe not found error."""

    def __init__(self, msg: str = 'Cannot find MiniLZO.exe', *args: object) -> None:
        super().__init__(msg, *args)


def find_minilzo(pattern: str = '**/MiniLZO.exe') -> str:
    """
    Find path of MiniLZO.exe.

    Parameters
    ----------
    pattern : str, optional

    Returns
    -------
    str

    Raises
    ------
    MiniLzoNotFoundError
    """
    is_frozen = hasattr(sys, 'frozen')
    root = Path(sys.executable).parent if is_frozen else Path()

    try:
        return next(root.glob(pattern)).absolute().as_posix()
    except StopIteration:
        msg = f'Could not find MiniLZO.exe matching `{pattern}`.'
        raise MiniLzoNotFoundError(msg) from None


def compress(data: bytes) -> bytes:
    """
    Minilzo compress.

    Parameters
    ----------
    data : bytes

    Returns
    -------
    bytes
    """
    minilzo = find_minilzo()

    with (
        tempfile.NamedTemporaryFile(delete=False) as s,
        tempfile.NamedTemporaryFile(delete=False) as d,
    ):
        src = Path(s.name)
        dst = Path(d.name)
        s.write(data)

    try:
        sp.check_output([minilzo, 'compress', src.as_posix(), dst.as_posix()])
        return dst.read_bytes()
    finally:
        src.unlink()
        dst.unlink()


def decompress(data: bytes) -> bytes:
    """
    Minilzo decompress.

    Parameters
    ----------
    data : bytes

    Returns
    -------
    bytes
    """
    minilzo = find_minilzo()

    with (
        tempfile.NamedTemporaryFile(delete=False) as s,
        tempfile.NamedTemporaryFile(delete=False) as d,
    ):
        src = Path(s.name)
        dst = Path(d.name)
        s.write(data)

    try:
        sp.check_output([minilzo, 'decompress', src.as_posix(), dst.as_posix()])
        return dst.read_bytes()
    finally:
        src.unlink()
        dst.unlink()


if __name__ == '__main__':
    import rich
    from cyclopts import App

    app = App()
    cnsl = rich.get_console()

    @app.default
    def test_compress() -> None:
        """압축/해제 테스트."""
        b = (
            b"I've seen things you people wouldn't believe. "
            b'Attack ships on fire off the shoulder of Orion. '
            b'I watched C-beams glitter in the dark near the Tannhauser Gate. '
            b'All those moments will be lost in time, like tears in rain. '
            b'Time to die.'
        )
        c = compress(b)
        cnsl.print(f'raw         ={b!r}')
        cnsl.print(f'compressed  ={c!r}')
        cnsl.print(f'decompressed={decompress(c)!r}')

    @app.command
    def dotnet_build() -> None:
        """Build MiniLZO."""
        args = ['dotnet', 'build', '--configuration', 'Release']
        cnsl.print(sp.check_output(args).decode())

    app()
