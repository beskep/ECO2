from pathlib import Path
from typing import Annotated

from cyclopts import App, Group, Parameter
from loguru import logger
from rich.progress import track

from eco.eco2 import Eco2, SFType
from eco.minilzo import MiniLzoImportError
from eco.utils import set_logger

app = App(version='0.5.0', help_format='markdown')
app.meta.group_parameters = Group('Options', sort_key=0)


@app.meta.default
def launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    debug: Annotated[bool, Parameter(name=['--debug', '-d'], negative=[])] = False,
):
    set_logger(level=10 if debug else 20)
    app(tokens)


def decrypt_targets(src: list[Path]):
    if len(src) != 1:
        return src

    if not (s := src[0]).is_dir():
        return src

    paths = [
        x
        for x in s.glob('*')
        if x.is_file() and x.suffix.lower() in {'.eco', '.ecox', '.tpl', '.tplx'}
    ]

    if not paths:
        msg = f'다음 경로에서 파일을 찾지 못함: "{s.absolute()}"'
        raise FileNotFoundError(msg)

    return paths


_header = Parameter(['--header', '-H'], negative=['--no-header', '-X'])


@app.command
def decrypt(
    input_: Annotated[list[Path], Parameter(negative=[])],
    *,
    output: Annotated[Path | None, Parameter(['--output', '-o'])] = None,
    write_header: Annotated[bool, _header] = True,
):
    """
    ECO2 저장 파일(`.eco`, `.ecox`, `.tpl`, `.tplx`)을 해석해 header와 xml 파일 저장.

    Parameters
    ----------
    input_ : list[Path]
        해석할 ECO2 저장 파일 목록.
        하나의 폴더를 지정하면 대상 내 모든 ECO2 파일을 해석함.
    output : Path | None, optional
        저장 폴더. 대상 경로 아래 파일명이 원본과 같은
        `.header`와 `.xml` 파일을 저장.
    write_header : bool, optional
        Header 파일 저장 여부.
    """
    input_ = decrypt_targets(input_)
    it = track(input_, description='Decrypting...') if len(input_) > 1 else input_

    for src in it:
        header = output / f'{src.stem}{Eco2.HEXT}' if output else None
        xml = output / f'{src.stem}{Eco2.XEXT}' if output else None

        try:
            Eco2.decrypt(
                src=src,
                header=header,
                xml=xml,
                write_header=write_header,
            )
        except MiniLzoImportError as e:
            logger.error(e.__class__.__name__)
        except (ValueError, OSError) as e:
            logger.exception(e)


def encrypt_targets(src: list[Path]):
    if len(src) != 1:
        return src

    if not (s := src[0]).is_dir():
        return src

    if not (paths := list(s.glob(f'*{Eco2.XEXT}'))):
        msg = f'다음 경로에서 파일을 찾지 못함: "{s.absolute()}"'
        raise FileNotFoundError(msg)

    return paths


@app.command
def encrypt(
    xml: Annotated[list[Path], Parameter(negative=[])],
    *,
    header: Annotated[Path | None, Parameter(['--header', '-H'])] = None,
    output: Annotated[Path | None, Parameter(['--output', '-o'])] = None,
    sftype: Annotated[SFType | None, Parameter(['--sftype', '-s'])] = None,
    dsr: bool = True,
):
    r"""
    header와 xml 파일을 암호화해 `.eco` 파일로 변환.

    Parameters
    ----------
    xml : list[Path]
        대상 xml 파일. 폴더를 지정하는 경우 해당 폴더 내 모든 xml 파일을 암호화.
    header : Path | None, optional
        header 파일 경로. 지정 시 모든 xml에 같은 header 적용.
        미지정 시 각 xml 파일과 같은 경로에 확장자가 `.header`인 파일로 추정.
    output : Path | None, optional
        저장 폴더. 대상 경로 아래 xml 파일과 이름이 같은 `.eco` 파일 저장.
    sftype : SFType | None, optional
        저장할 `.eco` 파일 header의 SFType 값. 미지정 시 변경하지 않음.
        `'all'`이면 모든 SFType(`'00'`, `'01'`, `'10'`)의 파일 저장.
        인증용 파일을 guest 계정으로 사용 시 SFType을 `'10'`으로 변경 필요.
    dsr : bool, optional
        결과부 (\<DSR\>) 포함 여부.
    """
    xml = encrypt_targets(xml)
    it = track(xml, description='Encrypting...') if len(xml) > 1 else xml
    for x in it:
        h = header or x.with_suffix(Eco2.HEXT)
        dst = output / f'{x.stem}{Eco2.EEXT}' if output else x.with_suffix(Eco2.EEXT)

        try:
            Eco2.encrypt(header=h, xml=x, dst=dst, sftype=sftype, dsr=dsr)
        except (ValueError, OSError) as e:
            logger.exception(e)


if __name__ == '__main__':
    app.meta()
