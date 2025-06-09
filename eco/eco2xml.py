from __future__ import annotations

from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

from lxml import etree

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Mapping

    from lxml.etree import _Element, _ElementTree


def _lines(
    source: str | Path | IO[str],
    encoding: str | None = 'UTF-8',
    errors: str | None = 'ignore',
) -> Generator[str]:
    with (
        Path(source).open('r', encoding=encoding, errors=errors)
        if isinstance(source, str | Path)
        else source as f
    ):
        yield from f


class Eco2Xml:
    """Decrypt한 ECO2 데이터 (xml), ECO2-OD 파일 (.ECL2) 해석."""

    DS = 'DS'
    DSR = 'DSR'

    URI = 'http://tempuri.org/{}.xsd'
    TAG_DS = '<DS xmlns="http://tempuri.org/DS.xsd">'
    TAG_DSR = '<DSR xmlns="http://tempuri.org/DSR.xsd">'

    XMLNS = 'xmlns'

    def __init__(self, source: str | Path | IO[str]) -> None:
        self.source = source
        xml = self.read_xml(source)
        self.ds: _Element = xml[0]
        self.dsr: _Element | None = xml[1]

    @classmethod
    def _read_text(cls, source: str | Path | IO[str]) -> Generator[str]:
        it = _lines(source)

        # ECO2-OD 파일 앞부분 (EUC-KR 인코딩) 처리
        if not (line := next(it).rstrip()).endswith(cls.TAG_DS):  # pragma: no cover
            msg = f'Unexpected first line: {line}'
            raise ValueError(msg)

        yield f'{cls.TAG_DS}\n'
        yield from it

    @classmethod
    def read_xml(cls, source: str | Path | IO[str]) -> tuple[_Element, _Element | None]:
        text = ''.join(cls._read_text(source))

        if (i := text.find(cls.TAG_DSR)) == -1:
            tds = text
            tdsr = None
        else:
            tds = text[:i]
            tdsr = text[i:]

        parser = etree.XMLParser(recover=True)

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

        return ds, dsr

    @classmethod
    def _tostring(
        cls,
        obj: _Element | _ElementTree,
        /,
        remove_prefix: str | None = None,
        **kwargs: Any,
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

    def write(self, path: str | Path, encoding: str | None = 'UTF-8') -> None:
        Path(path).write_text(self.tostring(), encoding=encoding)

    def iterfind(
        self,
        path: str,
        namespaces: Mapping[str | None, str] | None = None,
    ) -> Iterator[_Element]:
        yield from self.ds.iterfind(path, namespaces=namespaces)

        if self.dsr is not None:
            yield from self.dsr.iterfind(path, namespaces=namespaces)

    @classmethod
    def register_namespace(cls) -> None:
        etree.register_namespace(cls.DS, cls.URI.format(cls.DS))
        etree.register_namespace(cls.DSR, cls.URI.format(cls.DSR))


Eco2Xml.register_namespace()
