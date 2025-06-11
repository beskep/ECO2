from __future__ import annotations

import dataclasses as dc
from itertools import cycle
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, Self

from loguru import logger

from eco import minilzo

if TYPE_CHECKING:
    from collections.abc import Iterable

try:  # noqa: SIM105
    minilzo.load_dll()
except minilzo.MiniLzoDllNotFoundError:
    pass


type Extension = Literal['eco', 'tpl']
type SFType = Literal['00', '01', '10']

DS_CLOSING = '</DS>'
DSR_OPENING = '<DSR xmlns="http://tempuri.org/DSR.xsd'


def split_xml(text: str) -> tuple[str, str | None]:
    """
    xml을 DR(설계 정보), DSR(계산 결과)로 분리.

    Parameters
    ----------
    text : str

    Returns
    -------
    tuple[str, str | None]
    """
    if (i := text.find(DSR_OPENING)) == -1:
        return text, None

    ds = text[: (text.find(DS_CLOSING) + len(DS_CLOSING))]
    dsr = text[i:]
    return ds, dsr


@dc.dataclass
class Eco2:
    """ECO2 저장 파일 해석."""

    header: bytes
    xml: str

    KEY: ClassVar[tuple[int, ...]] = (172, 41, 85, 66)
    HEADER: ClassVar[tuple[tuple[int, str], ...]] = (
        # SFType: Password가 있으면 b'01',
        # UserAuthType가 ADMIN, BOTH, BOTH1, BOTH2 면 b'00',
        # 이외 b'10'으로 추정
        (2, 'SFType'),
        (10, 'UIVersion'),
        (10, 'LGVersion'),
        (100, 'Name'),
        (256, 'Desc'),
        (19, 'MakeTime'),
        (19, 'EditTime'),
        (8, 'Password'),
    )

    def __post_init__(self) -> None:  # noqa: D105
        self.xml = self.xml.replace('\r\n', '\n')

    @classmethod
    def xor(cls, data: bytes) -> bytes:
        """
        ECO2 `Pub.cs`의 decrypt, encrypt 재현.

        Parameters
        ----------
        data : bytes

        Returns
        -------
        bytes
        """
        return bytes(d ^ k for d, k in zip(data, cycle(cls.KEY), strict=False))

    @classmethod
    def decode_header(cls, data: bytes) -> Iterable[tuple[str, str | bytes]]:
        """
        Header 정보 디코드.

        Parameters
        ----------
        data : bytes

        Yields
        ------
        Iterator[Iterable[tuple[str, str | bytes]]]
            항목 이름, 값.
        """
        v: bytes | str
        for length, name in cls.HEADER:
            b, data = data[:length], data[length:]

            try:
                v = b.decode('EUC-KR').rstrip('\x00')
            except ValueError:
                v = b

            yield name, v

    @classmethod
    def decrypt(cls, data: bytes, *, xor: bool, decompress: bool) -> Self:
        """
        ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`) 데이터 복호화.

        Parameters
        ----------
        data : bytes
            Raw data.
        xor : bool
            xor 적용 여부. `.eco` 또는 `.ecox` 파일이면 `True`.
        decompress : bool
            MiniLZO 압축 해제 여부. `.ecox` 또는 `.tplx` 파일이면 `True`.

        Returns
        -------
        Self
        """
        if xor:
            data = cls.xor(data)
        if decompress:
            data = minilzo.decompress(data)

        header_length = sum(x[0] for x in cls.HEADER)
        header = data[:header_length]
        xml = data[header_length:].decode(errors='ignore')

        # 결과부 (<DSR>)가 존재하는 경우,
        # <DS>와 <DSR> 사이 decode 불가능한 데이터 제거
        # (안해도 출력엔 지장 없음)
        ds, dsr = split_xml(xml)
        if dsr is not None:
            xml = f'{ds}\n{dsr}'

        return cls(header, xml)

    @classmethod
    def read(cls, src: str | Path) -> Self:
        """
        ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`) 복호화.

        Parameters
        ----------
        src : str | Path
            대상 파일 경로

        Returns
        -------
        Self
        """
        src = Path(src)

        suffix = src.suffix.lower()
        xor = suffix.startswith('.eco')
        decompress = suffix.endswith('x')

        raw = src.read_bytes()

        try:
            data = cls.decrypt(raw, xor=xor, decompress=decompress)
        except ValueError:  # pragma: no cover
            logger.info(
                'xor={} 설정으로 해석 실패. xor={} 설정으로 재시도.',
                xor,
                not xor,
            )
            data = cls.decrypt(raw, xor=not xor, decompress=decompress)

        return data

    def encrypt(self, *, xor: bool = True) -> bytes:
        """
        `.eco` 파일로 저장하기 위해 암호화.

        Parameters
        ----------
        xor : bool, optional
            xor 적용 여부. `.eco`로 저장할 경우 적용.

        Returns
        -------
        bytes
        """
        b = self.header + self.xml.encode('UTF-8')

        if xor:
            b = self.xor(b)

        return b

    def replace_sftype(self, sftype: SFType) -> Self:
        """
        Header의 SFType 수정.

        ECO2 guest 계정으로 열기 위해선 SFType을 '10'으로 수정.

        Parameters
        ----------
        sftype : SFType

        Returns
        -------
        Self
        """
        return dc.replace(self, header=sftype.encode() + self.header[2:])

    def drop_dsr(self) -> Self:
        """
        결과부 (DSR) 삭제.

        Returns
        -------
        Self
        """
        ds, _dsr = split_xml(self.xml)
        return dc.replace(self, xml=ds)
