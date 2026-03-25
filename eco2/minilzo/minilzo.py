# ruff: noqa: S404 S603
import subprocess as sp
import sys
import tempfile
from pathlib import Path

MINILZO = 'bin/**/MiniLZO.exe'


class MiniLzoNotFoundError(FileNotFoundError):
    """MiniLZO.exe not found error."""

    def __init__(self, msg: str = 'Cannot find MiniLZO.exe', *args: object) -> None:
        super().__init__(msg, *args)


def find_minilzo(pattern: str = MINILZO) -> str:
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
        raise MiniLzoNotFoundError(msg, root) from None


def compress(data: bytes, minilzo: str = MINILZO) -> bytes:
    """
    Minilzo compress.

    Parameters
    ----------
    data : bytes

    Returns
    -------
    bytes
    """
    m = find_minilzo(minilzo)

    with (
        tempfile.NamedTemporaryFile(delete=False) as s,
        tempfile.NamedTemporaryFile(delete=False) as d,
    ):
        src = Path(s.name)
        dst = Path(d.name)
        s.write(data)

    try:
        sp.check_output([m, 'compress', src.as_posix(), dst.as_posix()])
        return dst.read_bytes()
    finally:
        src.unlink()
        dst.unlink()


def decompress(data: bytes, minilzo: str = MINILZO) -> bytes:
    """
    Minilzo decompress.

    Parameters
    ----------
    data : bytes

    Returns
    -------
    bytes
    """
    m = find_minilzo(minilzo)

    with (
        tempfile.NamedTemporaryFile(delete=False) as s,
        tempfile.NamedTemporaryFile(delete=False) as d,
    ):
        src = Path(s.name)
        dst = Path(d.name)
        s.write(data)

    try:
        sp.check_output([m, 'decompress', src.as_posix(), dst.as_posix()])
        return dst.read_bytes()
    finally:
        src.unlink()
        dst.unlink()


if __name__ == '__main__':
    # `dotnet build --configuration Release`로 빌드
    import rich

    console = rich.get_console()

    r = (
        b"I've seen things you people wouldn't believe. "
        b'Attack ships on fire off the shoulder of Orion. '
        b'I watched C-beams glitter in the dark near the Tannhauser Gate. '
        b'All those moments will be lost in time, like tears in rain. '
        b'Time to die.'
    )
    c = compress(r)
    d = decompress(c)

    console.print(f'raw          = {r!r}')
    console.print(f'compressed   = {c!r}')
    console.print(f'decompressed = {d!r}')
    assert r == d
