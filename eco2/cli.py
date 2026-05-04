# ruff: noqa: D102 D105
from __future__ import annotations

import dataclasses as dc
import functools
from collections.abc import Sequence  # noqa: TC003
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, ClassVar, Literal

import cyclopts
import structlog
from cyclopts import App, Group, Parameter

from eco2.core import Eco2, Eco2Xml, Header
from eco2.editor import Eco2Editor
from eco2.utils import setup_logger, track

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
    version='0.10.0',
    config=cyclopts.config.Toml('config.toml'),
    help_format='markdown',
    help_on_error=True,
    result_action=['call_if_callable', 'print_non_int_sys_exit'],
)
app.meta.group_parameters = Group('Options', sort_key=0)
logger = structlog.stdlib.get_logger()


@app.meta.default
def launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    debug: bool = False,
) -> None:
    """Meta app launcher."""
    setup_logger(10 if debug else 20)
    return app(tokens)


@app.command
@dc.dataclass
class Convert:
    """`.eco`, `.ecox`를 `.tpl`로, 또는 `.tpl`, `.tplx`를 `.eco`로 변환."""

    input_: Annotated[tuple[Path, ...], Parameter(negative=[])]
    """입력 파일 또는 입력 파일이 있는 폴더."""

    _: dc.KW_ONLY

    x: bool = True
    """비압축 파일(.eco, .tpl) 대신 압축 파일(.ecox, .tplx)로 변환 여부."""

    output: Path | None = None
    """결과 파일 경로. 미지정 시 입력 파일에서 확장자만 바꾼 파일."""

    target: Sequence[str] = ('.eco', '.ecox', '.tpl', '.tplx')
    """`input`이 폴더일 경우 변환 대상 파일의 확장자."""

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

    def _destination(self, src: Path) -> Path:
        ext = 'eco' if src.suffix.lower().startswith('.tpl') else 'tpl'
        if self.x:
            ext = f'{ext}x'

        return self.output or src.parent / f'{src.stem}.{ext}'

    def __call__(self) -> None:
        for src in track(self.input_, description='Converting...'):
            dst = self._destination(src)

            if dst.exists():
                logger.error('파일이 이미 존재합니다', path=dst.as_posix())
                continue

            logger.info(src.as_posix(), dst=dst.as_posix())

            eco = Eco2.read(src)
            eco.write(dst)


@dc.dataclass
class _Ext:
    eco2: Sequence[str] = ('.eco', '.ecox', '.tpl', '.tplx')
    """대상 ECO2 파일 확장자 (대소문자 미구분)."""

    eco2od: Sequence[str] = ('.ecl2',)
    """대상 ECO2-OD 파일 확장자 (대소문자 미구분)."""


@app.command
@dc.dataclass
class Decrypt:
    """ECO2, ECO2-OD 저장 파일을 해석해 header와 xml 파일 저장."""

    input_: Annotated[tuple[Path, ...], Parameter(negative=[])]
    """해석할 ECO2 저장 파일 목록.
    폴더 하나를 지정하면 대상 내 모든 ECO2 파일을 해석."""

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

        logger.info(src.as_posix())
        logger.debug(
            'decrypt',
            header=header.as_posix() if header else header,
            xml=xml.as_posix(),
        )

        eco = Eco2.read(src)

        if header:
            header.write_text(eco.header.dump(), encoding=self.encoding)

        xml.write_text(eco.xml, encoding=self.encoding)

    def decrypt_eco2od(self, src: Path) -> None:
        name = src.stem if self.unique_stem else src.name
        dst = self.output or src.parent
        xml = dst / f'{name}.xml'

        logger.info(src.as_posix(), xml=xml.as_posix())

        eco = Eco2Xml.read(src)
        eco.write(xml)

    def _decrypt(self, src: Path) -> None:
        src.stat()
        ext = src.suffix.lower()

        if ext in self.ext.eco2:
            self.decrypt_eco2(src)
        elif ext in self.ext.eco2od:
            self.decrypt_eco2od(src)
        else:
            msg = f'Unknown file extension: "{ext}"'
            raise ValueError(msg)

    def __call__(self) -> None:
        it = (
            track(self.input_, description='Decrypting...')
            if len(self.input_) > 1
            else self.input_
        )

        for src in it:
            try:
                self._decrypt(src)
            except (ValueError, RuntimeError, OSError):
                logger.exception(src.as_posix())


@app.command
@dc.dataclass
class Encrypt:
    """header와 xml 파일을 암호화해 `.eco` 또는 `.tpl` 파일로 변환."""

    xml: Annotated[tuple[Path, ...], Parameter(negative=[])]
    """대상 xml 파일. 폴더를 지정하는 경우 해당 폴더 내 모든 xml 파일을 암호화."""

    _: dc.KW_ONLY

    header: Path | None = None
    """header 파일 경로. 지정 시 모든 xml에 같은 header 적용.
    미지정 시 각 xml 파일과 같은 경로에 확장자가 `.header`인 파일로 추정."""

    output: Path | None = None
    """저장 폴더. 대상 경로 아래 xml 파일과 이름이 같은 `.eco` 파일 저장."""

    extension: Literal['eco', 'ecox', 'tpl', 'tplx'] = 'ecox'
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
        xml.stat()

        header = self.common_header or self._read_header(xml.with_suffix('.json'))
        output = (
            self.output / f'{xml.stem}.{self.extension}'
            if self.output
            else xml.with_suffix(f'.{self.extension}')
        )

        logger.info(xml.as_posix())
        logger.debug('encrypt', header=header, output=output.as_posix())

        ds, dsr = self._read_xml(xml)
        eco = Eco2(header=header, ds=ds, dsr=dsr)
        eco.write(output, dsr=self.dsr)

    def __call__(self) -> None:
        it = (
            track(self.xml, description='Encrypting...')
            if len(self.xml) > 1
            else self.xml
        )

        if self.header:
            logger.info('header 지정됨', header=self.header)

        for xml in it:
            try:
                self._encrypt(xml)
            except (ValueError, RuntimeError, OSError):
                logger.exception(xml.as_posix())


@app.command
@dc.dataclass
class Prune:
    """Weather 등 ECO2 공용 정보를 제외한 설계 정보 xml 추출."""

    input_: Annotated[tuple[Path, ...], Parameter(negative=[])]
    """해석할 ECO2 저장 파일 목록.
    폴더 하나를 지정하면 대상 내 모든 ECO2 파일을 해석."""

    _: dc.KW_ONLY

    output: Path | None = None
    """저장 폴더."""

    encoding: str = 'UTF-8'
    """xml 저장 인코딩."""

    ext: Sequence[str] = ('.eco', '.ecox', '.tpl', '.tplx')
    """대상 ECO2 파일 확장자 (대소문자 미구분)."""

    TAGS: ClassVar[tuple[str, ...]] = (
        'tbl_common',
        'tbl_profile',
        'tbl_weather',
        'weather_cha',
        'weather_group',
        'weather_ilsa',
        'weather_river',
        'weather_supdo',
        'weather_temp',
        'weather_water',
        'weather_wind',
    )

    def __post_init__(self) -> None:
        self.input_ = tuple(self._resolve_input(self.input_))

    def _resolve_input(self, paths: Sequence[Path]) -> Sequence[Path]:
        if len(paths) != 1 or not paths[0].is_dir():
            return paths

        directory = paths[0]
        paths = tuple(
            x
            for x in directory.glob('*')
            if x.is_file() and x.suffix.lower() in self.ext
        )

        if not paths:
            msg = f'다음 경로에서 파일을 찾지 못함: "{directory.absolute()}"'
            raise FileNotFoundError(msg)

        return paths

    def prune(self, src: Path) -> str:
        xml = Eco2Editor(src).xml

        for e in tuple(xml.ds.iter()):
            if e.tag in self.TAGS:
                xml.ds.remove(e)

        return xml.tostring('DS')

    def __call__(self) -> None:
        for src in track(self.input_, description='Pruning...'):
            dst = (self.output or src.parent) / f'{src.stem}.xml'

            if dst.exists():
                logger.error('파일이 이미 존재합니다', path=dst.as_posix())
                continue

            xml = self.prune(src)
            dst.write_text(xml, encoding=self.encoding)


if __name__ == '__main__':
    app.meta()
