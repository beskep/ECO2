from __future__ import annotations

import dataclasses as dc
import io
import json
import struct
from itertools import cycle
from pathlib import Path
from typing import IO, TYPE_CHECKING, ClassVar, Self

from loguru import logger

from eco2 import minilzo

if TYPE_CHECKING:
    from collections.abc import Generator

try:  # noqa: SIM105
    minilzo.load_dll()
except minilzo.MiniLzoDllNotFoundError:
    pass


def _lf2crlf(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\n', '\r\n')


@dc.dataclass
class Header:
    """프로젝트 메타 정보."""

    SFType: str
    UIVersion: str
    LGVersion: str
    Name: str
    Desc: str
    MakeTime: str
    EditTime: str

    KEYS: ClassVar[tuple[tuple[int, str], ...]] = (
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
    )

    @classmethod
    def load(cls, data: str | bytes | bytearray) -> Self:
        """
        Load header data from json.

        Parameters
        ----------
        data : str | bytes | bytearray

        Returns
        -------
        Self
        """
        return cls(**json.loads(data))

    def dump(self, indent: int | None = 2) -> str:
        """
        Dump header data to json.

        Parameters
        ----------
        indent : int | None, optional

        Returns
        -------
        str
        """
        data = {k: v.rstrip('\x00') for k, v in dc.asdict(self).items()}
        return json.dumps(data, ensure_ascii=False, indent=indent)

    def _encode(self) -> Generator[bytes]:
        for width, key in self.KEYS:
            value: str = getattr(self, key)
            yield value.encode('EUC-KR').ljust(width, b'\x00')

    def encode(self) -> bytes:
        """
        ECO2 파일에 저장하기 위한 형식으로 encode.

        Returns
        -------
        bytes
        """
        return b''.join(self._encode())


@dc.dataclass
class Eco2:
    """ECO2 저장 파일 해석."""

    header: Header
    """프로젝트 메타 정보 (ECO2 버전, 프로젝트명 등)"""

    ds: str
    """설계 정보 및 계산 데이터베이스"""

    dsr: str | None
    """계산 결과"""

    KEY: ClassVar[tuple[int, ...]] = (172, 41, 85, 66)
    EMPTY_DSR: ClassVar[str] = '<DSR xmlns="http://tempuri.org/DSR.xsd"></DSR>'

    def __post_init__(self) -> None:  # noqa: D105
        self.ds = self.ds.replace('\r\n', '\n')
        if self.dsr is not None:
            self.dsr = self.dsr.replace('\r\n', '\n')

    @property
    def xml(self) -> str:
        """DS, DSR을 합한 xml 형식 정보."""
        if self.dsr is None:
            return self.ds

        return f'{self.ds}\n{self.dsr}'

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
    def parse(cls, data: bytes | IO[bytes]) -> tuple[Header, str, str | None]:
        """
        ECO2 저장 파일을 Header, DS(설계), DSR(해석 결과)로 나눠 해석.

        Parameters
        ----------
        data : bytes
            _description_

        Returns
        -------
        tuple[Header, str, str | None]
            Header, DS, DSR
        """
        stream = data if isinstance(data, IO) else io.BytesIO(data)

        # header
        header = {}
        for length, key in Header.KEYS:
            b = stream.read(length)
            header[key] = b.decode('EUC-KR')

        # DS
        length = struct.unpack('<q', stream.read(8))[0]
        ds = stream.read(length).decode()

        if not ds.startswith('<DS'):
            logger.warning('Unexpected DS start: {}', ds.split('\n')[0])

        # DSR
        if b'</DSR>' not in data:
            dsr = None
        else:
            length = struct.unpack('<q', stream.read(8))[0]
            dsr = stream.read(length).decode()

            if not dsr.startswith('<DSR'):
                logger.warning('Unexpected DSR start: {}', dsr.split('\n')[0])

        return Header(**header), ds, dsr

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

        return cls(*cls.parse(data))

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
        return cls.decrypt(raw, xor=xor, decompress=decompress)

    def encrypt(self, *, xor: bool, compress: bool = False) -> bytes:
        """
        ECO2 파일로 저장하기 위해 암호화.

        Parameters
        ----------
        xor : bool
            xor 적용 여부. `.eco`로 저장할 경우 적용.
        compress : bool, optional
            MiniLZO 압축 여부. `.ecox`, `.tplx`로 저장할 경우 적용 (오류 발생 가능).

        Returns
        -------
        bytes
        """
        # header
        header = dc.replace(self.header, SFType='10' if xor else '00')
        data = header.encode()

        # DS
        ds = _lf2crlf(self.ds).encode()
        data += struct.pack('<q', len(ds))
        data += ds

        # DSR
        dsr = _lf2crlf(self.dsr or self.EMPTY_DSR).encode()
        data += struct.pack('<q', len(dsr))
        data += dsr

        if xor:
            data = self.xor(data)
        if compress:
            data = minilzo.compress(data)

        return data

    def write(self, dst: str | Path, *, dsr: bool | None = None) -> None:
        """
        ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`) 변환 및 저장.

        저장 경로 확장자에 따라 xor 암호화, MiniLZO 압축 여부 자동 결정.
        **`.ecox`, `.tplx` 저장 시 오류 발생 가능**

        Parameters
        ----------
        dst : str | Path
            저장 경로.
        dsr : bool | None
            DSR (결과) 부분 저장 여부.
            `None`일 경우, `.eco` 또는 `.ecox`로 저장할 때 DSR 제외.
        """
        dst = Path(dst)

        suffix = dst.suffix.lower()
        is_eco = suffix.startswith('.eco')
        compress = suffix.endswith('x')

        if dsr is None:
            dsr = not is_eco

        eco = self if dsr else dc.replace(self, dsr=None)
        data = eco.encrypt(xor=is_eco, compress=compress)
        dst.write_bytes(data)
