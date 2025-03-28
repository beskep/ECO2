# ruff: noqa: S320
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lxml.etree import _Element, _ElementTree


class Eco2Xml:
    """Decrypt한 ECO2 데이터 (xml) 해석."""

    DS = 'DS'
    DSR = 'DSR'

    URI = 'http://tempuri.org/{}.xsd'
    DSRT = '<DSR xmlns="http://tempuri.org/DSR.xsd">'

    XMLNS = 'xmlns'

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._ds, self._dsr = self.read_xml(self._path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def ds(self) -> _Element:
        return self._ds

    @property
    def dsr(self) -> _Element | None:
        return self._dsr

    @classmethod
    def read_xml(cls, path: Path) -> tuple[_Element, _Element | None]:
        text = path.read_text('UTF-8')
        parser = etree.XMLParser(recover=True)

        if (i := text.find(cls.DSRT)) == -1:
            tds = text
            tdsr = None
        else:
            tds = text[:i]
            tdsr = text[i:]

        # 입력 변수 xml
        ds = etree.fromstring(
            tds.replace(cls.XMLNS, f'{cls.XMLNS}:{cls.DS}'),
            parser=parser,
        )

        # 결과 xml
        if tdsr is None:
            dsr = None
        else:
            dsr = etree.fromstring(
                tdsr.replace(cls.XMLNS, f'{cls.XMLNS}:{cls.DSR}'),
                parser=parser,
            )

        return (ds, dsr)

    @classmethod
    def _tostring(
        cls,
        obj: _Element | _ElementTree,
        /,
        remove_prefix: str | None = None,
        **kwargs,
    ) -> str:
        s = etree.tostring(obj, encoding='unicode', method='xml', **kwargs)

        if remove_prefix:
            s = s.replace(f'{cls.XMLNS}:{remove_prefix}', cls.XMLNS)

        return s

    def tostring(self) -> str:
        s = self._tostring(self.ds, remove_prefix=self.DS)

        if self.dsr is not None:
            dsr = self._tostring(self.dsr, remove_prefix=self.DSR)
            s = f'{s}\n{dsr}'

        return s

    def write(self, path: str | Path, encoding='UTF-8') -> None:
        Path(path).write_text(self.tostring(), encoding=encoding)

    def iterfind(self, path: str, namespaces=None) -> Iterator[_Element]:
        yield from self.ds.iterfind(path, namespaces=namespaces)

        if self.dsr is not None:
            yield from self.dsr.iterfind(path, namespaces=namespaces)

    @classmethod
    def register_namespace(cls):
        etree.register_namespace(cls.DS, cls.URI.format(cls.DS))
        etree.register_namespace(cls.DSR, cls.URI.format(cls.DSR))


Eco2Xml.register_namespace()
