# ruff: noqa: B008 UP007

from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.progress import track

from eco.eco2 import Eco2
from eco.minilzo import MiniLzoImportError
from eco.utils import set_logger

_debug = typer.Option(False, '--debug', '-d', help='Show debug message')  # noqa: FBT003
_verbose = typer.Option(2, '-v', count=True, help='Verbosity (default: `-vv`)')


def callback(*, debug: bool = _debug, verbose: int = _verbose):
    set_logger(level=10 if debug else 20)
    Eco2.verbose = verbose


app = typer.Typer(callback=callback)


class HELP:
    DI = (
        '해석할 ECO2 저장 파일의 경로. 폴더를 지정하는 경우 해당 폴더 내 모든 저장'
        ' 파일을 대상으로 함.'
    )
    DO = (
        '저장할 파일 경로. 대상 경로 아래 파일명이 원본과 같은 header'
        ' (`.header`)와 value (`.xml`) 파일을 저장함'
    )
    DH = 'Header 파일 저장 여부'

    EI = (
        '해석할 value 파일의 경로. 폴더를 지정하는 경우 해당 폴더 내 모든'
        ' xml 파일을 대상으로 함.'
    )
    EH = (
        'header 파일 경로. 미지정 시 value 파일과 동일한 경로·이름에 확장자가'
        ' `.header`인 파일로 추정.'
    )
    EO = (
        '저장할 파일의 경로. 대상 경로 아래 파일명이 value 파일과 같은 '
        '`.eco` 파일을 저장함'
    )


@app.command()
def decrypt(
    *,
    inputs: list[Path] = typer.Argument(..., show_default=False, help=HELP.DI),
    output: Optional[Path] = typer.Option(None, '--output', '-o', help=HELP.DO),
    write_header: bool = typer.Option(
        True,  # noqa: FBT003
        '--header/--no-header',
        '-h/-H',
        help=HELP.DH,
    ),
):
    """ECO2 저장 파일 (`.eco`, `.tpl`)을 해석해 header와 value 파일로 나눠 저장."""
    if len(inputs) == 1 and inputs[0].is_dir():
        paths = [
            x
            for x in inputs[0].glob('*')
            if x.is_file() and x.suffix.lower() in {'.eco', '.ecox', '.tpl', '.tplx'}
        ]
    else:
        paths = inputs

    if not paths:
        msg = f'다음 경로에서 파일을 찾지 못함: "{inputs[0].resolve()}"'
        raise FileNotFoundError(msg)

    output = Path(output) if output else None

    it = track(paths, description='Decrypting...') if len(paths) > 1 else paths
    for path in it:
        header = output / f'{path.stem}{Eco2.HEXT}' if output else None
        value = output / f'{path.stem}{Eco2.VEXT}' if output else None

        try:
            Eco2.decrypt(
                path=path,
                header=header,
                value=value,
                write_header=write_header,
            )
        except MiniLzoImportError:
            pass
        except (ValueError, OSError) as e:
            logger.exception(e)

        if Eco2.verbose > Eco2.DEFAULT_VERBOSE:
            logger.log('BLANK', '')


@app.command()
def encrypt(
    *,
    inputs: list[Path] = typer.Argument(..., show_default=False, help=HELP.EI),
    header: Optional[Path] = typer.Option(None, '--header', '-h', help=HELP.EH),
    output: Optional[Path] = typer.Option(None, '--output', '-o', help=HELP.EO),
):
    """header와 value를 암호화해 eco 파일로 변환."""
    if len(inputs) == 1 and inputs[0].is_dir():
        paths = list(inputs[0].glob(f'*{Eco2.VEXT}'))
    else:
        paths = inputs

    if not paths:
        msg = f'다음 경로에서 파일을 찾지 못함: "{inputs[0].resolve()}"'
        raise FileNotFoundError(msg)

    output = Path(output) if output else None
    header = Path(header) if header else None

    it = track(paths, description='Encrypting...') if len(paths) > 1 else paths
    for path in it:
        hp = header if header else path.with_suffix(Eco2.HEXT)
        if output:
            op = output / f'{path.stem}{Eco2.EEXT}'
        else:
            op = path.with_suffix(Eco2.EEXT)

        try:
            Eco2.encrypt(header=hp, value=path, path=op)
        except MiniLzoImportError:
            pass
        except (ValueError, OSError) as e:
            logger.exception(e)

        if Eco2.verbose > Eco2.DEFAULT_VERBOSE:
            logger.log('BLANK', '')


if __name__ == '__main__':
    app()
