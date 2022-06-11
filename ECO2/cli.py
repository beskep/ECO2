from pathlib import Path
import sys

import click
from loguru import logger

from ECO2.eco2 import Eco2

_LOG_FORMAT = ('<green>{time:HH:mm:ss}</green> | '
               '<level>{level: <8}</level> | '
               '<cyan>{module}</cyan>:<cyan>{line: >4}</cyan> | '
               '<level>{message}</level>')


@click.group()
@click.option('-d', '--debug', is_flag=True, help='Show debug message')
def cli(debug: bool):
    """
    \b
    사용 방법 안내: 다음 명령어 입력
    `ECO2 --help`
    `ECO2 encrypt --help`
    `ECO2 decrypt --help`
    """
    logger.remove()
    logger.add(sys.stdout,
               level=(10 if debug else 20),
               format=_LOG_FORMAT,
               backtrace=False)


@cli.command()
@click.argument('inputs', nargs=-1, required=True)
@click.option('-o',
              '--output',
              help=('저장할 파일 경로. 확장자를 `.header`, `.xml`로 바꾼 경로에 '
                    '각각 header와 value를 저장함. INPUT이 여러 개일 경우 무시됨.'))
def decrypt(inputs: tuple, output):
    """
    \b
    ECO2 저장 파일 (`.eco`, `.tpl`)을 해석해서 header와 value 파일로 나눠 저장.
    header: ECO2 저장 파일의 버전, 생성 날짜 등 정보를 담은 바이너리 파일.
            `output.header` 형식.
    value : 해석 설정 정보를 담은 xml 파일. `output.xml` 형식.

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
        inputs_ = tuple(x.resolve().as_posix() for x in inputs)
        raise FileNotFoundError(f'다음 경로에서 파일을 찾지 못함: {inputs_}')

    op = Path(output) if (output and len(inputs) == 1) else None

    for path in paths:
        header = op.with_suffix(Eco2.HEXT) if op else None
        value = op.with_suffix(Eco2.VEXT) if op else None

        try:
            Eco2.decrypt(path=path, header=header, value=value)
        except (ValueError, OSError) as e:
            logger.exception(e)


@cli.command()
@click.argument('inputs', nargs=-1, required=True)
@click.option('-h',
              '--header',
              help=('header 파일 경로. 미지정 시 value 파일과 동일한 경로·이름에 '
                    '확장자가 `.header`인 파일로 추정.'))
@click.option('-o',
              '--output',
              help=('저장할 eco 파일의 경로. '
                    'INPUT이 여러 개일 경우 무시됨.'))
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
        inputs_ = tuple(x.resolve().as_posix() for x in inputs)
        raise FileNotFoundError(f'다음 경로에서 파일을 찾지 못함: {inputs_}')

    output = Path(output) if (output and len(inputs) == 1) else None
    header = Path(header) if header else None

    for path in paths:
        hp = header if header else path.with_suffix(Eco2.HEXT)
        op = output if output else path.with_suffix('.eco')

        try:
            Eco2.encrypt(header=hp, value=path, save=op)
        except (ValueError, OSError) as e:
            logger.exception(e)


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    cli()
