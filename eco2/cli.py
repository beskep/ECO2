from __future__ import annotations

import dataclasses as dc
import functools
from collections.abc import Sequence  # noqa: TC003
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, ClassVar, Literal

import cyclopts
from cyclopts import App, Group, Parameter
from loguru import logger

from eco2.eco2data import Eco2, Header
from eco2.eco2xml import Eco2Xml
from eco2.minilzo import MiniLzoImportError
from eco2.utils import LogHandler, Progress

if TYPE_CHECKING:
    from collections.abc import Iterable


def _all_unique[T](iterable: Iterable[T]) -> bool:
    seen: set[T] = set()

    for x in iterable:
        if x in seen:
            return False

        seen.add(x)

    return True


app = App(
    version='0.8.0',
    config=cyclopts.config.Toml('config.toml'),
    help_format='markdown',
    help_on_error=True,
)
app.meta.group_parameters = Group('Options', sort_key=0)


@app.meta.default
def launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    debug: bool = False,
) -> None:
    """Meta app launcher."""
    LogHandler.set(level=10 if debug else 20)
    app(tokens)


@cyclopts.Parameter(name='*')
@dc.dataclass
class _Converter:
    input_: Annotated[tuple[Path, ...], Parameter(negative=[])]

    _: dc.KW_ONLY

    output: Path | None = None
    target: Sequence[str] = ('.eco', '.ecox', '.tpl', '.tplx')

    def __post_init__(self) -> None:
        self.input_ = tuple(self._resolve_input(self.input_))

    def _resolve_input(self, paths: Sequence[Path]) -> Sequence[Path]:
        if len(paths) != 1 or not paths[0].is_dir():
            return paths

        directory = paths[0]
        paths = tuple(
            x
            for x in directory.glob('*')
            if x.is_file() and x.suffix.lower() in self.target
        )

        if not paths:
            msg = f'다음 경로에서 파일을 찾지 못함: "{directory.absolute()}"'
            raise FileNotFoundError(msg)

        return paths

    def __call__(self) -> None:
        it = (
            Progress.iter(self.input_, description='Encrypting...')
            if len(self.input_) > 1
            else self.input_
        )

        for src in it:
            ext = 'eco' if src.suffix.lower().startswith('.tpl') else 'tpl'
            dst = self.output or src.parent / f'{src.stem}.{ext}'

            if dst.exists():
                logger.error('파일이 이미 존재합니다: "{}"', dst)
                continue

            logger.info('dst="{}"', dst)

            eco = Eco2.read(src)
            eco.write(dst)


@app.command
def convert(converter: _Converter) -> None:
    """`.eco`, `.ecox`를 `.tpl`로, 또는 `.tpl`, `.tplx`를 `.eco`로 변환."""
    converter()


@dc.dataclass
class _Ext:
    eco2: Sequence[str] = ('.eco', '.ecox', '.tpl', '.tplx')
    """대상 ECO2 파일 확장자 (대소문자 미구분.)"""

    eco2od: Sequence[str] = ('.ecl2',)
    """대상 ECO2-OD 파일 확장자 (대소문자 미구분.)"""


@cyclopts.Parameter(name='*')
@dc.dataclass
class _Decryptor:
    input_: Annotated[tuple[Path, ...], Parameter(negative=[])]
    """해석할 ECO2 저장 파일 목록.
    폴더 하나를 지정하면 대상 내 모든 ECO2 파일을 해석함."""

    _: dc.KW_ONLY

    output: Path | None = None
    """저장 폴더. 대상 경로 아래 파일명이 원본과 같은 `.json`과 `.xml` 파일을 저장."""

    header: bool = True
    """Header 파일 저장 여부."""

    encoding: str = 'UTF-8'
    """Header (json), 데이터 (xml) 저장 인코딩."""

    ext: _Ext = dc.field(default_factory=_Ext)

    def __post_init__(self) -> None:
        self.input_ = tuple(self._resolve_input(self.input_))

    def _resolve_input(self, paths: Sequence[Path]) -> Sequence[Path]:
        if len(paths) != 1 or not paths[0].is_dir():
            return paths

        ext = {*self.ext.eco2, *self.ext.eco2od}
        directory = paths[0]
        paths = tuple(
            x for x in directory.glob('*') if x.is_file() and x.suffix.lower() in ext
        )

        if not paths:
            msg = f'다음 경로에서 파일을 찾지 못함: "{directory.absolute()}"'
            raise FileNotFoundError(msg)

        return paths

    @functools.cached_property
    def unique_stem(self) -> bool:
        return _all_unique(x.stem for x in self.input_)

    def decrypt_eco2(self, src: Path) -> None:
        name = src.stem if self.unique_stem else src.name
        dst = self.output or src.parent
        header = dst / f'{name}.json' if self.header else None
        xml = dst / f'{name}.xml'

        logger.info('src="{}"', src)
        logger.debug('header="{}"', header)
        logger.debug('xml="{}"', xml)

        eco = Eco2.read(src)

        if header:
            header.write_text(eco.header.dump(), encoding=self.encoding)

        xml.write_text(eco.xml, encoding=self.encoding)

    def decrypt_eco2od(self, src: Path) -> None:
        name = src.stem if self.unique_stem else src.name
        dst = self.output or src.parent
        xml = dst / f'{name}.xml'

        logger.info('src="{}"', src)
        logger.debug('xml="{}"', xml)

        eco = Eco2Xml.read(src)
        eco.write(xml)

    def _decrypt(self, src: Path) -> None:
        ext = src.suffix.lower()

        if ext in self.ext.eco2:
            self.decrypt_eco2(src)
        elif ext in self.ext.eco2od:
            self.decrypt_eco2od(src)
        else:
            raise ValueError(src)

    def __call__(self) -> None:
        it = (
            Progress.iter(self.input_, description='Decrypting...')
            if len(self.input_) > 1
            else self.input_
        )

        for src in it:
            try:
                self._decrypt(src)
            except MiniLzoImportError as e:
                logger.error(e)
            except (ValueError, RuntimeError, OSError) as e:
                logger.exception(e)


@app.command
def decrypt(decrypter: _Decryptor) -> None:
    """ECO2, ECO2-OD 저장 파일을 해석해 header와 xml 파일 저장."""
    decrypter()


@cyclopts.Parameter(name='*')
@dc.dataclass
class _Encryptor:
    xml: Annotated[tuple[Path, ...], Parameter(negative=[])]
    """대상 xml 파일. 폴더를 지정하는 경우 해당 폴더 내 모든 xml 파일을 암호화."""

    _: dc.KW_ONLY

    header: Path | None = None
    """header 파일 경로. 지정 시 모든 xml에 같은 header 적용.
    미지정 시 각 xml 파일과 같은 경로에 확장자가 `.header`인 파일로 추정."""

    output: Path | None = None
    """저장 폴더. 대상 경로 아래 xml 파일과 이름이 같은 `.eco` 파일 저장."""

    extension: Literal['eco', 'tpl'] = 'eco'
    """저장할 파일 형식."""

    encoding: str = 'UTF-8'
    """Header (json), 데이터 (xml) 해석 인코딩."""

    dsr: bool | None = None
    """결과부 (`<DSR>`) 포함 여부. 포함 시 ECO2에서 불러올 때 오류 발생 가능."""

    DSR: ClassVar[str] = '<DSR xmlns'

    def __post_init__(self) -> None:
        self.xml = self._resolve_xml(self.xml)

    @staticmethod
    def _resolve_xml(paths: Sequence[Path]) -> tuple[Path, ...]:
        if len(paths) != 1 or not paths[0].is_dir():
            return tuple(paths)

        directory = paths[0]
        if not (paths := tuple(directory.glob('*.xml'))):
            msg = f'다음 경로에서 파일을 찾지 못함: "{directory.absolute()}"'
            raise FileNotFoundError(msg)

        return paths

    def _read_header(self, path: Path) -> Header:
        return Header.load(path.read_text(self.encoding))

    def _read_xml(self, path: Path) -> tuple[str, str | None]:
        xml = path.read_text(self.encoding)

        if (idx := xml.find(self.DSR)) == -1:
            return xml, None

        ds = xml[: idx - 1]
        dsr = xml[idx:]
        return ds, dsr

    @functools.cached_property
    def common_header(self) -> Header | None:
        return None if self.header is None else self._read_header(self.header)

    def _encrypt(self, xml: Path) -> None:
        header = self.common_header or self._read_header(xml.with_suffix('.json'))
        output = (
            self.output / f'{xml.stem}.{self.extension}'
            if self.output
            else xml.with_suffix(f'.{self.extension}')
        )

        logger.info('xml="{}"', xml)
        logger.debug('header="{}"', header)
        logger.debug('output="{}"', output)

        ds, dsr = self._read_xml(xml)
        eco = Eco2(header=header, ds=ds, dsr=dsr)
        eco.write(output, dsr=self.dsr)

    def __call__(self) -> None:
        it = (
            Progress.iter(self.xml, description='Encrypting...')
            if len(self.xml) > 1
            else self.xml
        )

        if self.header:
            logger.info('header="{}"', self.header)

        for xml in it:
            try:
                self._encrypt(xml)
            except (ValueError, RuntimeError, OSError) as e:
                logger.exception(e)


@app.command
def encrypt(encryptor: _Encryptor) -> None:
    """header와 xml 파일을 암호화해 `.eco` 파일로 변환."""
    encryptor()


if __name__ == '__main__':
    app.meta()
