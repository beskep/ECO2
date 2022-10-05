from pathlib import Path

import click
from loguru import logger

from ECO2.eco2 import Eco2
from ECO2.utils import set_logger
from ECO2.utils import track


@click.group()
@click.option('-d', '--debug', is_flag=True, help='Show debug message.')
@click.option('-v',
              '--verbose',
              count=True,
              default=2,
              help='Verbosity (default: `-vv`).')
def cli(debug: bool, verbose: int):
    """
    \b
    사용 방법 안내: 다음 명령어 입력
    `ECO2 --help`
    `ECO2 encrypt --help`
    `ECO2 decrypt --help`
    """
    set_logger(level=(10 if debug else 20))
    Eco2.verbose = verbose


@cli.command()
@click.argument('inputs', nargs=-1, required=True)
@click.option('-o',
              '--output',
              help=('저장할 파일 경로. 대상 경로 아래 파일명이 원본과 같은'
                    'header (`.header`)와 value (`.xml`) 파일을 저장함'))
def decrypt(inputs: tuple, output):
    """
    \b
    ECO2 저장 파일 (`.eco`, `.tpl`)을 해석해서 header와 value 파일로 나눠 저장.
    header: ECO2 저장 파일의 버전, 생성 날짜 등 정보를 담은 바이너리 파일.
            `.header` 형식.
    value : 해석 설정 정보를 담은 xml 파일. `.xml` 형식.

    \b
    Argument:
        INPUTS: 해석할 ECO2 저장 파일의 경로.
                폴더를 지정하는 경우 해당 폴더 내 모든 저장 파일을 대상으로 함.
    """
    inputs = tuple(Path(x) for x in inputs)

    if len(inputs) == 1 and inputs[0].is_dir():
        paths = tuple(x for x in inputs[0].glob('*')
                      if x.is_file() and x.suffix in {'.eco', '.tpl'})
    else:
        paths = inputs

    if not paths:
        src = inputs[0].resolve().as_posix()
        raise FileNotFoundError(f'다음 경로에서 파일을 찾지 못함: "{src}"')

    output = Path(output) if output else None

    if len(paths) > 1:
        paths = track(paths, description='Decrypting...')

    for path in paths:
        header = output / f'{path.stem}{Eco2.HEXT}' if output else None
        value = output / f'{path.stem}{Eco2.VEXT}' if output else None

        try:
            Eco2.decrypt(path=path, header=header, value=value)
        except (ValueError, OSError) as e:
            logger.exception(e)

        if Eco2.verbose > 2:
            logger.log('BLANK', '')


@cli.command()
@click.argument('inputs', nargs=-1, required=True)
@click.option('-h',
              '--header',
              help=('header 파일 경로. 미지정 시 value 파일과 동일한 경로·이름에 '
                    '확장자가 `.header`인 파일로 추정.'))
@click.option('-o',
              '--output',
              help=('저장할 파일의 경로. 대상 경로 아래 파일명이 '
                    'value 파일과 같은 `.eco` 파일을 저장함'))
def encrypt(inputs: tuple, header, output):
    """
    header와 value를 암호화해서 eco 파일로 변환

    \b
    Argument:
        INPUTS: 해석할 value 파일의 경로.
                폴더를 지정하는 경우 해당 폴더 내 모든 xml 파일을 대상으로 함.
    """
    inputs = tuple(Path(x) for x in inputs)

    if len(inputs) == 1 and inputs[0].is_dir():
        paths = tuple(inputs[0].glob(f'*{Eco2.VEXT}'))
    else:
        paths = inputs

    if not paths:
        src = inputs[0].resolve().as_posix()
        raise FileNotFoundError(f'다음 경로에서 파일을 찾지 못함: "{src}"')

    output = Path(output) if output else None
    header = Path(header) if header else None

    if len(paths) > 1:
        paths = track(paths, description='Encrypting...')

    for path in paths:
        hp = header if header else path.with_suffix(Eco2.HEXT)
        if output:
            op = output / f'{path.stem}{Eco2.EEXT}'
        else:
            op = path.with_suffix(Eco2.EEXT)

        try:
            Eco2.encrypt(header=hp, value=path, path=op)
        except (ValueError, OSError) as e:
            logger.exception(e)

        if Eco2.verbose > 2:
            logger.log('BLANK', '')


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    cli()
