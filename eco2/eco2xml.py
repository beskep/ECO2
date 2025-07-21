from __future__ import annotations

import dataclasses as dc
import struct
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self

from lxml import etree

from eco2.eco2data import Eco2

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from lxml.etree import _Element, _ElementTree


def _split(data: bytes, encoding: str = 'UTF-8') -> tuple[str, str | None]:
    tag = b'<DSR xmlns="http://tempuri.org/DSR.xsd">'
    split = data.split(tag, maxsplit=1)

    ds = split[0].decode(encoding)
    dsr = None if len(split) == 1 else split[1].decode(encoding)

    return ds, dsr


def _tostring(
    obj: _Element | _ElementTree,
    /,
    remove_namespace: str | None = None,
    **kwargs: Any,
) -> str:
    text: str = etree.tostring(obj, encoding='unicode', method='xml', **kwargs)

    if remove_namespace:
        text = text.replace(f'xmlns:{remove_namespace}', 'xmlns')

    return text


@dc.dataclass
class Eco2Xml:
    """Decrypt한 ECO2 데이터 (xml), ECO2-OD 파일 (.ECL2) 해석."""

    ds: _Element
    dsr: _Element | None

    URI: ClassVar[str] = 'http://tempuri.org/{}.xsd'

    @classmethod
    def _create(cls, ds: str, dsr: str | None) -> Self:
        parser = etree.XMLParser(recover=True)

        def parse(text: str, tag: str) -> _Element:
            return etree.fromstring(
                text.replace('xmlns', f'xmlns:{tag}'), parser=parser
            )

        return cls(ds=parse(ds, 'DS'), dsr=None if dsr is None else parse(dsr, 'DSR'))

    @classmethod
    def create(cls, src: str | bytes | Eco2) -> Self:
        """
        XML 데이터 (str | bytes) 또는 `Eco2`로부터 생성.

        Parameters
        ----------
        src : str | bytes | Eco2

        Returns
        -------
        Self
        """
        match src:
            case Eco2():
                return cls._create(src.ds, src.dsr)
            case str():
                raw = src.encode()
            case _:
                raw = src

        ds, dsr = _split(raw)
        return cls._create(ds, dsr)

    @classmethod
    def read(cls, src: str | Path, encoding: str = 'UTF-8') -> Self:
        """
        ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`) 또는 XML 파일 해석.

        Parameters
        ----------
        src : str | Path
        encoding : str, optional

        Returns
        -------
        Self
        """
        try:
            eco2 = Eco2.read(src)
            ds = eco2.ds
            dsr = eco2.dsr
        except (ValueError, struct.error):
            ds = None
            dsr = None

        if ds is None or not ds.startswith('<DS'):
            # XML 파일
            ds, dsr = _split(Path(src).read_bytes(), encoding=encoding)

        return cls._create(ds, dsr)

    def _tostring(self, namespace: Literal['DS', 'DSR'], /) -> str:
        if (element := self.ds if namespace == 'DS' else self.dsr) is None:
            return ''

        return _tostring(element, remove_namespace=namespace)

    def tostring(self, namespace: Literal['DS', 'DSR'] | None = None) -> str:
        """
        XML string으로 변환.

        Parameters
        ----------
        namespace : Literal['DS', 'DSR'] | None, optional
            변환 대상. `None`인 경우, DS와 DSR을 합한 문자열 반환.

        Returns
        -------
        str

        Raises
        ------
        ValueError
            Namespace 지정 오류.
        """
        match namespace:
            case 'DS' | 'DSR':
                return self._tostring(namespace)
            case None:
                txt = self._tostring('DS')
                if dsr := self._tostring('DSR'):
                    txt = f'{txt}\n{dsr}'

                return txt
            case _:
                raise ValueError(namespace)

    def write(self, path: str | Path, encoding: str | None = 'UTF-8') -> None:
        """
        XML 파일 저장.

        Parameters
        ----------
        path : str | Path
        encoding : str | None, optional
        """
        Path(path).write_text(self.tostring(), encoding=encoding)

    def iterfind(
        self,
        path: str,
        namespaces: Mapping[str | None, str] | None = None,
    ) -> Iterator[_Element]:
        """
        하위 element 탐색.

        Parameters
        ----------
        path : str
        namespaces : Mapping[str  |  None, str] | None, optional

        Yields
        ------
        Iterator[_Element]
        """
        yield from self.ds.iterfind(path, namespaces=namespaces)

        if self.dsr is not None:
            yield from self.dsr.iterfind(path, namespaces=namespaces)

    @classmethod
    def register_namespace(cls) -> None:
        """Namespace 등록."""
        etree.register_namespace('DS', cls.URI.format('DS'))
        etree.register_namespace('DSR', cls.URI.format('DSR'))


Eco2Xml.register_namespace()
