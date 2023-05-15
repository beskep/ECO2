import re
from io import StringIO
from pathlib import Path
from xml.etree import ElementTree as ET  # noqa: N817

# ruff: noqa: S314


def get_namespace(element: ET.Element):
    m = re.match(r'\{(.*)\}', element.tag)
    return m.group(1) if m else ''


class Eco2Data:
    """Decrypt한 ECO2 데이터 (xml) 해석 예시."""

    DS = 'http://tempuri.org/DS.xsd'
    DSR = 'http://tempuri.org/DSR.xsd'
    DSRT = f'<DSR xmlns="{DSR}">'

    # namespace
    NSDS = {'': DS}
    NSDSR = {'': DSR}

    def __init__(self, xml: str | Path) -> None:
        self._ds, self._dsr = self.read_xml(xml)

    @classmethod
    def read_xml(cls, path):
        text = Path(path).read_text('UTF-8')

        if (i := text.find(cls.DSRT)) == -1:
            tds = text
            tdsr = None
        else:
            tds = text[:i]
            tdsr = text[i:]

        # 입력 변수 xml
        ds = ET.parse(StringIO(tds))
        assert get_namespace(ds.getroot()) == cls.DS

        if tdsr is None:
            dsr = None
        else:
            # 결과 xml
            dsr = ET.parse(StringIO(tdsr))
            assert get_namespace(dsr.getroot()) == cls.DSR

        return (ds, dsr)

    @property
    def ds(self) -> ET.ElementTree:
        return self._ds

    @property
    def dsr(self) -> ET.ElementTree | None:
        return self._dsr

    @classmethod
    def iterfind(cls, elemenet: ET.Element, path: str):
        yield from elemenet.iterfind(path, namespaces=cls.NSDS)
        yield from elemenet.iterfind(path, namespaces=cls.NSDSR)

    @classmethod
    def find(cls, elemenet: ET.Element, path: str):
        return next(cls.iterfind(elemenet=elemenet, path=path))

    @classmethod
    def monthly_data(cls, elemenet: ET.Element):
        return (
            float(cls.find(elemenet=elemenet, path=f'M{x:02d}').text)
            for x in range(1, 13)
        )

    def findall(self, path: str):
        yield from self.ds.iterfind(path, namespaces=self.NSDS)

        if self.dsr is not None:
            yield from self.dsr.iterfind(path, namespaces=self.NSDSR)
