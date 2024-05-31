# ruff: noqa: S320

from pathlib import Path

from lxml import etree
from lxml.etree import _Element, _ElementTree

XMLNS = 'xmlns'


class Eco2Xml:
    """Decrypt한 ECO2 데이터 (xml) 해석."""

    DS = 'DS'
    DSR = 'DSR'

    URI = 'http://tempuri.org/{}.xsd'
    DSRT = '<DSR xmlns="http://tempuri.org/DSR.xsd">'

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
            tds.replace(XMLNS, f'{XMLNS}:{cls.DS}'),
            parser=parser,
        )

        # 결과 xml
        if tdsr is None:
            dsr = None
        else:
            dsr = etree.fromstring(
                tdsr.replace(XMLNS, f'{XMLNS}:{cls.DSR}'),
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
    ):
        s = etree.tostring(obj, encoding='unicode', **kwargs)

        if remove_prefix:
            s = s.replace(f'{XMLNS}:{remove_prefix}', XMLNS)

        return s

    def tostring(self) -> str:
        s = self._tostring(self.ds, remove_prefix=self.DS)

        if self.dsr is not None:
            dsr = self._tostring(self.dsr, remove_prefix=self.DSR)
            s = f'{s}\n{dsr}'

        return s

    def write(self, path: str | Path, encoding='UTF-8'):
        Path(path).write_text(self.tostring(), encoding=encoding)

    def iterfind(self, path: str, namespaces=None):
        yield from self.ds.iterfind(path, namespaces=namespaces)

        if self.dsr is not None:
            yield from self.dsr.iterfind(path, namespaces=namespaces)


etree.register_namespace(Eco2Xml.DS, Eco2Xml.URI.format(Eco2Xml.DS))
etree.register_namespace(Eco2Xml.DSR, Eco2Xml.URI.format(Eco2Xml.DSR))
