from collections.abc import Iterable
from itertools import cycle
from pathlib import Path
from typing import ClassVar, Literal

from loguru import logger

from eco import minilzo

try:
    minilzo.load_dll()
except FileNotFoundError as e:
    logger.warning('`{}`를 찾을 수 없음.', e)
    logger.warning('`.ecox`, `.tplx` 파일을 해석할 수 없습니다.')
    MINILZO = False
else:
    MINILZO = True

SFType = Literal['00', '01', '10', 'all']


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

    HENC = 'EUC-KR'
    XENC = 'UTF-8'
    HEXT = '.header'
    XEXT = '.xml'
    EEXT = '.eco'

    LOG_LEVEL: ClassVar[dict[str, int | str]] = {
        'header': 10,
        'src': 10,
        'dst': 20,
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
                v = b.decode(cls.HENC).rstrip('\x00')
            except ValueError:
                v = b

            yield name, v

    @classmethod
    def _log_header(cls, header: bytes):
        lvl = cls.LOG_LEVEL['header']
        for key, value in cls._decode_header(header):
            logger.log(lvl, '[Header] {:9s} = {}', key, value)

    @classmethod
    def _write_xml(cls, path: Path, data: str):
        path.write_text(data.replace('\r\n', '\n'), encoding=cls.XENC)

    @classmethod
    def _split_xml(cls, text: str) -> tuple[str, str | None]:
        if (i := text.find(cls.DSR)) == -1:
            return text, None

        ds = text[: (text.find(cls.DS) + len(cls.DS))]
        dsr = text[i:]
        return ds, dsr

    @classmethod
    def _read_xml(cls, path: Path, *, dsr: bool = True) -> str:
        text = path.read_text(encoding=cls.XENC).replace('\n', '\r\n')

        if not dsr:
            text = cls._split_xml(text)[0]

        return text

    @classmethod
    def _decrypt(
        cls,
        data: bytes,
        *,
        decrypt: bool,
        decompress: bool = False,
    ) -> tuple[bytes, str]:
        if decrypt:
            data = cls.decrypt_bytes(data)
        if decompress:
            data = minilzo.decompress(data)

        hl = cls.header_length()
        header_bytes = data[:hl]
        xml_bytes = data[hl:]

        xml = xml_bytes.decode(encoding=cls.XENC, errors='ignore')

        # 결과부 (<DSR>)가 존재하는 경우,
        # <DS>와 <DSR> 사이 decode 불가능한 데이터 제거
        # (안해도 출력엔 지장 없음)
        ds, dsr = cls._split_xml(xml)
        if dsr is not None:
            xml = f'{ds}\n{dsr}'

        return header_bytes, xml

    @classmethod
    def decrypt(
        cls,
        src: str | Path,
        header: str | Path | None = None,
        xml: str | Path | None = None,
        *,
        write_header=True,
    ):
        """
        `.eco`, `.ecox`, `.tpl`, `.tplx` 파일 복호화.

        Parameters
        ----------
        src : str | Path
            ECO2 저장 파일 (`.eco`, `.ecox`, `.tpl`, `.tplx`) 경로
        header : str | Path | None, optional
            저장할 header 파일 경로.
            `None`이면 path의 확장자를 `.header`로 변경한 경로.
        xml : str | Path | None, optional
            저장할 xml 파일 경로.
            `None`이면 path의 확장자를 `.xml`로 변경한 경로.
        write_header : bool, optional
            header 저장 여부
        """
        src = Path(src)
        header = src.with_suffix(cls.HEXT) if header is None else Path(header)
        xml = src.with_suffix(cls.XEXT) if xml is None else Path(xml)

        logger.log(cls.LOG_LEVEL['src'], 'Source="{}"', src)
        logger.log(cls.LOG_LEVEL['header'], 'Header="{}"', header)
        logger.log(cls.LOG_LEVEL['dst'], 'XML="{}"', xml)

        data = src.read_bytes()
        suffix = src.suffix.lower()
        decrypt = suffix.startswith(cls.EEXT)
        decompress = suffix.endswith('x')

        if decompress and not MINILZO:
            logger.error(
                'MiniLZO.dll을 불러올 수 없습니다. '
                '`.ecox`, `.tplx` 파일을 해석할 수 없습니다.'
            )

        try:
            hdata, xdata = cls._decrypt(
                data=data, decrypt=decrypt, decompress=decompress
            )
        except ValueError:
            hdata, xdata = cls._decrypt(
                data=data, decrypt=not decrypt, decompress=decompress
            )

        cls._log_header(hdata)

        if write_header:
            header.write_bytes(hdata)

        cls._write_xml(path=xml, data=xdata)

    @classmethod
    def encrypt(
        cls,
        header: str | Path,
        xml: str | Path,
        dst: str | Path | None = None,
        *,
        sftype: SFType | None = None,
        dsr: bool = True,
    ):
        """
        `.eco` 파일 암호화.

        Parameters
        ----------
        header : str | Path
            Header 파일 경로 (`.header`)
        xml : str | Path
            Value 파일 경로 (`.xml`)
        dst : str | Path | None, optional
            저장 경로. `None`이면 xml의 확장자를 `.eco`로 변경한 경로.
        sftype : SFType | None, optional
            Header에 저장되는 SFType.
            `None`이면 header 파일을 수정하지 않음.
            `'all'`이면 모든 SFType(`'00'`, `'01'`, `'10'`)의 파일 저장.
            인증용 파일을 guest 계정으로 사용 시 SFType을 `'10'`으로 변경 필요.
        dsr : bool, optional
            결과부 (<DSR>) 포함 여부.
        """
        header = Path(header)
        xml = Path(xml)
        dst = Path(dst) if dst else xml.with_suffix(cls.EEXT)

        logger.log(cls.LOG_LEVEL['src'], 'XML="{}"', xml)
        logger.log(cls.LOG_LEVEL['header'], 'Header="{}"', header)
        logger.log(cls.LOG_LEVEL['dst'], 'Destination="{}"', dst)

        hdata = header.read_bytes()
        xdata = cls._read_xml(path=xml, dsr=dsr).encode(cls.XENC)

        for sf in [sftype] if sftype != 'all' else ['00', '01', '10']:
            h = hdata if sf is None else sf.encode() + hdata[2:]
            p = dst if sftype != 'all' else dst.with_stem(f'{dst.stem}_SF{sf}')

            cls._log_header(h)

            encrypted = cls.encrypt_bytes(h + xdata)
            p.write_bytes(encrypted)
