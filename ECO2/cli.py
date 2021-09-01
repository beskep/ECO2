from itertools import chain
from pathlib import Path
import sys

import click
from loguru import logger

from ECO2.eco2 import Eco2

_log_format = ('<green>{time:HH:mm:ss}</green> | '
               '<level>{level: <8}</level> | '
               '<cyan>{module}</cyan>:<cyan>{line}</cyan> '
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
               format=_log_format,
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
    paths = [Path(x) for x in inputs]

    op = None
    if len(paths) == 1:
        if paths[0].is_dir():
            paths = chain(paths[0].glob('*.eco'), paths[0].glob('*.tpl'))
        elif output:
            op = Path(output)

    for path in paths:
        header_path = op.with_suffix(Eco2.header_ext) if op else None
        value_path = op.with_suffix(Eco2.value_ext) if op else None

        try:
            Eco2.decrypt(path=path,
                         header_path=header_path,
                         value_path=value_path)
        except (ValueError, OSError) as e:
            logger.exception(e)


@cli.command()
@click.argument('inputs', nargs=-1, required=True)
@click.option('-h',
              '--header',
              help=('header 파일 경로. 미지정 시 value 파일과 동일한 경로·이름에 '
                    '확장자가 `.header`인 파일로 추정. INPUT이 폴더일 경우 무시됨.'))
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
    paths = [Path(x) for x in inputs]

    header_path = None
    output_path = None
    if len(paths) == 1:
        if paths[0].is_dir():
            paths = paths[0].glob(f'*{Eco2.value_ext}')
        else:
            if header:
                header_path = Path(header)
            if output:
                output_path = Path(output)

    for path in paths:
        hp = header_path if header_path else path.with_suffix(Eco2.header_ext)
        op = output_path if output_path else path.with_suffix('.eco')

        try:
            Eco2.encrypt(header_path=hp, value_path=path, save_path=op)
        except (ValueError, OSError) as e:
            logger.exception(e)


if __name__ == '__main__':
    cli()
