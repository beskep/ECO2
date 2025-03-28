from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import Annotated

import cyclopts
from cyclopts import App, Group, Parameter
from loguru import logger

from eco.eco2 import Eco2, Extension, SFType
from eco.minilzo import MiniLzoImportError
from eco.utils import LogHandler, Progress

app = App(version='0.6.0', help_format='markdown')
app.meta.group_parameters = Group('Options', sort_key=0)


@app.meta.default
def launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    debug: bool = False,
):
    LogHandler.set(level=10 if debug else 20)
    app(tokens)


def _decrypt_targets(src: list[Path]):
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


@app.command
def decrypt(
    input_: Annotated[list[Path], Parameter(negative=[])],
    *,
    output: Path | None = None,
    header: bool = True,
):
    """
    ECO2 저장 파일(`.eco`, `.ecox`, `.tpl`, `.tplx`)을 해석해 header와 xml 파일 저장.

    Parameters
    ----------
    input_ : list[Path]
        해석할 ECO2 저장 파일 목록.
        하나의 폴더를 지정하면 대상 내 모든 ECO2 파일을 해석함.
    output : Path | None, optional
        저장 폴더. 대상 경로 아래 파일명이 원본과 같은 `.header`와 `.xml` 파일을 저장.
    header : bool, optional
        Header 파일 저장 여부.
    """
    input_ = _decrypt_targets(input_)
    it = (
        Progress.iter(input_, description='Decrypting...')
        if len(input_) > 1
        else input_
    )

    for src in it:
        h = output / f'{src.stem}{Eco2.HEADER_EXT}' if output else None
        xml = output / f'{src.stem}{Eco2.XML_EXT}' if output else None

        try:
            Eco2.decrypt(
                src=src,
                header=h,
                xml=xml,
                write_header=header,
            )
        except MiniLzoImportError as e:
            logger.error(e.__class__.__name__)
        except (ValueError, OSError) as e:
            logger.exception(e)


def _encrypt_targets(src: list[Path]):
    if len(src) != 1:
        return src

    if not (s := src[0]).is_dir():
        return src

    if not (paths := list(s.glob(f'*{Eco2.XML_EXT}'))):
        msg = f'다음 경로에서 파일을 찾지 못함: "{s.absolute()}"'
        raise FileNotFoundError(msg)

    return paths


@cyclopts.Parameter(name='*')
@dataclass
class EncryptConfig:
    extension: Extension = 'eco'
    """저장할 파일 형식."""

    sftype: SFType = '10'
    """저장할 `.eco` 파일 header의 SFType 값.
    `'all'`이면 모든 SFType(`'00'`, `'01'`, `'10'`)의 파일 저장."""

    dsr: bool = False
    """결과부 (`<DSR>`) 포함 여부."""


_DEFAULT_ENCRYPT_CONF = EncryptConfig()


@app.command
def encrypt(
    xml: Annotated[list[Path], Parameter(negative=[])],
    *,
    header: Path | None = None,
    output: Path | None = None,
    conf: EncryptConfig = _DEFAULT_ENCRYPT_CONF,
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
    output : Path | None, optional
        저장 폴더. 대상 경로 아래 xml 파일과 이름이 같은 `.eco` 파일 저장.
    conf : EncryptConfig, optional
    """
    xml = _encrypt_targets(xml)
    it = Progress.iter(xml, description='Encrypting...') if len(xml) > 1 else xml
    ext = f'.{conf.extension}'

    for x in it:
        h = header or x.with_suffix(Eco2.HEADER_EXT)
        dst = output / f'{x.stem}{ext}' if output else x.with_suffix(ext)

        try:
            Eco2.encrypt(
                header=h,
                xml=x,
                dst=dst,
                sftype=conf.sftype,
                write_dsr=conf.dsr,
            )
        except (ValueError, OSError) as e:
            logger.exception(e)


if __name__ == '__main__':
    app.meta()
