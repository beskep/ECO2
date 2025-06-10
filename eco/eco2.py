from __future__ import annotations

from itertools import cycle
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, NamedTuple, Self

from loguru import logger

from eco import minilzo

if TYPE_CHECKING:
    from collections.abc import Iterable

try:
    minilzo.load_dll()
except minilzo.MiniLzoDllNotFoundError:
    MINILZO = False
else:
    MINILZO = True


type Extension = Literal['eco', 'tpl']
type SFType = Literal['00', '01', '10']


class Eco2Data(NamedTuple):
    header: bytes
    xml: str

    def replace_sftype(self, sftype: SFType) -> Self:
        header = sftype.encode() + self.header[2:]
        return type(self)(header, self.xml)


class Eco2:
    HEADER = (
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
    KEY = (172, 41, 85, 66)
    DS = '</DS>'
    DSR = '<DSR xmlns="http://tempuri.org/DSR.xsd'

    EUC_KR = 'EUC-KR'
    UTF8 = 'UTF-8'

    HEADER_EXT = '.header'
    XML_EXT = '.xml'
    ECO_EXT = '.eco'

    LOG_LEVEL: ClassVar[dict[str, int | str]] = {
        'header': 'DEBUG',
        'src': 'DEBUG',
        'dst': 'INFO',
    }

    @classmethod
    def decrypt_bytes(cls, data: bytes) -> bytes:
        return bytes(d ^ k for d, k in zip(data, cycle(cls.KEY), strict=False))

    @classmethod
    def encrypt_bytes(cls, data: bytes) -> bytes:
        return cls.decrypt_bytes(data)

    @classmethod
    def header_length(cls) -> int:
        return sum(x[0] for x in cls.HEADER)

    @classmethod
    def _decode_header(cls, data: bytes) -> Iterable[tuple[str, str | bytes]]:
        v: bytes | str
        for length, name in cls.HEADER:
            b, data = data[:length], data[length:]

            try:
                v = b.decode(cls.EUC_KR).rstrip('\x00')
            except ValueError:
                v = b

            yield name, v

    @classmethod
    def _log_header(cls, header: bytes) -> None:
        lvl = cls.LOG_LEVEL['header']
        for key, value in cls._decode_header(header):
            logger.log(lvl, '[Header] {:9s} = {}', key, value)

    @classmethod
    def _write_xml(cls, path: Path, text: str) -> None:
        path.write_text(text.replace('\r\n', '\n'), encoding=cls.UTF8)

    @classmethod
    def _split_xml(cls, text: str) -> tuple[str, str | None]:
        if (i := text.find(cls.DSR)) == -1:
            return text, None

        ds = text[: (text.find(cls.DS) + len(cls.DS))]
        dsr = text[i:]
        return ds, dsr

    @classmethod
    def _read_xml(cls, path: Path, *, dsr: bool = True) -> str:
        text = path.read_text(encoding=cls.UTF8).replace('\n', '\r\n')

        if not dsr:
            text = cls._split_xml(text)[0]

        return text

    @classmethod
    def decrypt(
        cls,
        data: bytes,
        *,
        decrypt: bool,
        decompress: bool = False,
    ) -> Eco2Data:
        """
        ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`) 데이터 복호화.

        Parameters
        ----------
        data : bytes
            원본 데이터.
        decrypt : bool
            decrypt 여부. `.eco` 또는 `.ecox` 파일이면 `True`.
        decompress : bool, optional
            MiniLZO 압축 해제 여부. `.ecox` 또는 `.tplx` 파일이면 `True`.

        Returns
        -------
        Eco2Data
        """
        if decrypt:
            data = cls.decrypt_bytes(data)
        if decompress:
            if not MINILZO:  # pragma: no cover
                logger.error(
                    'MiniLZO.dll을 불러올 수 없습니다. '
                    '`.ecox`, `.tplx` 파일을 해석할 수 없습니다.'
                )

            data = minilzo.decompress(data)

        hl = cls.header_length()
        header = data[:hl]
        xml_bytes = data[hl:]

        xml = xml_bytes.decode(encoding=cls.UTF8, errors='ignore')

        # 결과부 (<DSR>)가 존재하는 경우,
        # <DS>와 <DSR> 사이 decode 불가능한 데이터 제거
        # (안해도 출력엔 지장 없음)
        ds, dsr = cls._split_xml(xml)
        if dsr is not None:
            xml = f'{ds}\n{dsr}'

        return Eco2Data(header, xml)

    @classmethod
    def read_and_decrypt(cls, src: str | Path) -> Eco2Data:
        """
        ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`) 복호화.

        Parameters
        ----------
        src : str | Path
            대상 파일 경로.

        Returns
        -------
        Eco2Data
        """
        src = Path(src)

        suffix = src.suffix.lower()
        decrypt = suffix.startswith(cls.ECO_EXT)
        decompress = suffix.endswith('x')

        raw = src.read_bytes()

        try:
            data = cls.decrypt(raw, decrypt=decrypt, decompress=decompress)
        except ValueError:  # pragma: no cover
            logger.info(
                'decrypt={} 설정으로 해석 실패. decrypt={} 설정으로 재시도.',
                decrypt,
                not decrypt,
            )
            data = cls.decrypt(raw, decrypt=not decrypt, decompress=decompress)

        return data

    @classmethod
    def decrypt_and_write(
        cls,
        src: str | Path,
        header: str | Path | None = None,
        xml: str | Path | None = None,
        *,
        write_header: bool = True,
        write_dsr: bool = False,
    ) -> None:
        """
        ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`) 파일 복호화 및 저장.

        Parameters
        ----------
        src : str | Path
            대상 파일 경로.
        header : str | Path | None, optional
            저장할 header 파일 경로.
            `None`이면 path의 확장자를 `.header`로 변경한 경로.
        xml : str | Path | None, optional
            저장할 xml 파일 경로.
            `None`이면 path의 확장자를 `.xml`로 변경한 경로.
        write_header : bool, optional
            header 저장 여부.
        write_dsr : bool, optional
            결과부 (<DSR>) 포함 여부.
        """
        src = Path(src)
        header = src.with_suffix(cls.HEADER_EXT) if header is None else Path(header)
        xml = src.with_suffix(cls.XML_EXT) if xml is None else Path(xml)

        logger.log(cls.LOG_LEVEL['src'], 'Source="{}"', src)
        logger.log(cls.LOG_LEVEL['header'], 'Header="{}"', header)
        logger.log(cls.LOG_LEVEL['dst'], 'XML="{}"', xml)

        data = cls.read_and_decrypt(src)

        cls._log_header(data.header)
        if write_header:
            header.write_bytes(data.header)

        text = data.xml if write_dsr else cls._split_xml(data.xml)[0]
        cls._write_xml(path=xml, text=text)

    @classmethod
    def encrypt(
        cls,
        data: Eco2Data,
        sftype: SFType | None = None,
        *,
        encrypt: bool = True,
    ) -> bytes:
        """
        `Eco2Data` 데이터를 ECO2 파일 형식으로 인코딩/암호화.

        Parameters
        ----------
        data : Eco2Data
            대상 데이터.
        sftype : SFType | None, optional
            Header에 저장되는 SFType.
            `None`이면 header 파일을 수정하지 않음.
        encrypt : bool, optional
            encrypt 여부. `.eco` 또는 파일이면 `True`.

        Returns
        -------
        bytes
        """
        if sftype:
            data = data.replace_sftype(sftype)

        b = data.header + data.xml.encode(cls.UTF8)

        if encrypt:
            b = cls.encrypt_bytes(b)

        return b

    @classmethod
    def encrypt_and_write(
        cls,
        header: str | Path,
        xml: str | Path,
        dst: Extension | Path = 'eco',
        *,
        sftype: SFType | Literal['all'] | None = '10',
        write_dsr: bool = False,
    ) -> None:
        """
        header와 xml 파일을 `.eco` 파일로 암호화.

        Parameters
        ----------
        header : str | Path
            Header 파일 경로 (`.header`).
        xml : str | Path
            Value 파일 경로 (`.xml`).
        dst : Literal['eco', 'tpl'] | Path, optional
            저장 경로. `Path`면 대상 경로에 저장.
            `'eco'` 또는 `'tpl'`면 `xml`의 확장자를 해당 값으로 변경한 경로에 저장.
        sftype : SFType | None, optional
            Header에 저장되는 SFType.
            `None`이면 header 파일을 수정하지 않음.
            `'all'`이면 모든 SFType(`'00'`, `'01'`, `'10'`)의 파일 저장.
        write_dsr : bool, optional
            결과부 (<DSR>) 포함 여부.
        """
        header = Path(header)
        xml = Path(xml)
        dst = dst if isinstance(dst, Path) else xml.with_suffix(f'.{dst}')

        logger.log(cls.LOG_LEVEL['src'], 'XML="{}"', xml)
        logger.log(cls.LOG_LEVEL['header'], 'Header="{}"', header)
        logger.log(cls.LOG_LEVEL['dst'], 'Destination="{}"', dst)

        data = Eco2Data(
            header=header.read_bytes(),
            xml=cls._read_xml(xml, dsr=write_dsr),
        )

        sf: Any
        for sf in [sftype] if sftype != 'all' else ['00', '01', '10']:
            b = cls.encrypt(
                data,
                sftype=sf,
                encrypt='eco' in dst.suffix.lower(),
            )
            p = dst if sftype != 'all' else dst.with_stem(f'{dst.stem} SF{sf}')
            p.write_bytes(b)
