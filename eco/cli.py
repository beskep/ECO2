from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, Group, Parameter
from loguru import logger
from rich.progress import track

from eco.eco2 import Eco2
from eco.minilzo import MiniLzoImportError
from eco.utils import set_logger

app = App(help_format='markdown')
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


_header = Parameter('--header', negative=['--no-header', '-X'])


@app.command
def decrypt(
    src: Annotated[list[Path], Parameter(negative=[])],
    dst: Path | None = None,
    *,
    write_header: Annotated[bool, _header] = True,
):
    """
    ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`)을 해석해 header와 xml 파일 저장.

    Parameters
    ----------
    src : list[Path]
        해석할 ECO2 저장 파일 목록.
        하나의 폴더를 지정하면 대상 내 모든 ECO2 파일을 해석함.
    dst : Path | None, optional
        저장 폴더. 대상 경로 아래 파일명이 원본과 같은
        `.header`와 `.xml` 파일을 저장.
    write_header : bool, optional
        Header 파일 저장 여부.
    """
    src = decrypt_targets(src)
    it = track(src, description='Decrypting...') if len(src) > 1 else src

    for path in it:
        header = dst / f'{path.stem}{Eco2.HEXT}' if dst else None
        xml = dst / f'{path.stem}{Eco2.XEXT}' if dst else None

        try:
            Eco2.decrypt(
                src=path,
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
    xml: list[Path],
    header: Path | None = None,
    dst: Path | None = None,
    sftype: Literal['00', '01', '10', 'all'] | None = None,
):
    """
    header와 xml 파일을 암호화해 `.eco` 파일로 변환.

    Parameters
    ----------
    xml : list[Path]
        대상 xml 파일. 폴더를 지정하는 경우 해당 폴더 내 모든 xml 파일을 암호화.
    header : Path | None, optional
        header 파일 경로. 지정 시 모든 xml에 같은 header 적용.
        미지정 시 각 xml 파일과 같은 경로에 확장자가 `.header`인 파일로 추정.
    dst : Path | None, optional
        저장 폴더. 대상 경로 아래 xml 파일과 이름이 같은 `.eco` 파일 저장.
    sftype : Literal['00', '01', '10', 'all'] | None, optional
        저장할 `.eco` 파일 header의 SFType 값. `None`이면 변경하지 않음.
        'all'이면 '00', '01', '10'으로 변경한 `.eco` 파일을 각각 저장.
    """
    xml = encrypt_targets(xml)
    it = track(xml, description='Encrypting...') if len(xml) > 1 else xml
    for _xml in it:
        _header = header or _xml.with_suffix(Eco2.HEXT)
        _dst = dst / f'{_xml.stem}{Eco2.EEXT}' if dst else _xml.with_suffix(Eco2.EEXT)

        try:
            Eco2.encrypt(header=_header, xml=_xml, dst=_dst, sftype=sftype)
        except (ValueError, OSError) as e:
            logger.exception(e)


if __name__ == '__main__':
    app.meta()
