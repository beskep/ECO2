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
    VENC = 'UTF-8'
    HEXT = '.header'
    VEXT = '.xml'
    EEXT = '.eco'

    _LOGLEVEL: ClassVar[dict[str, str]] = {
        'header': 'DEBUG',
        'src': 'INFO',
        'dst': 'DEBUG',
    }
    DEFAULT_VERBOSE = 2
    verbose = 2  # 1~3

    @classmethod
    def _loglvl(cls, kind: Literal['header', 'src', 'dst']):
        if cls.verbose == cls.DEFAULT_VERBOSE:
            return cls._LOGLEVEL[kind]

        return 'DEBUG' if cls.verbose < cls.DEFAULT_VERBOSE else 'INFO'

    @classmethod
    def decrypt_bytes(cls, data: bytes):
        return bytes(d ^ k for d, k in zip(data, cycle(cls.KEY), strict=False))

    @classmethod
    def encrypt_bytes(cls, data: bytes):
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
        lvl = cls._loglvl('header')
        for key, value in cls._decode_header(header):
            logger.log(lvl, '[Header] {:9s} = {}', key, value)

    @classmethod
    def _write_value(cls, path: Path, value: str):
        path.write_text(value.replace('\r\n', '\n'), encoding=cls.VENC)

    @classmethod
    def _read_value(cls, path: Path):
        return path.read_text(encoding=cls.VENC).replace('\n', '\r\n')

    @classmethod
    def _decrypt(cls, data: bytes, *, decrypt: bool, decompress=False):
        if decrypt:
            data = cls.decrypt_bytes(data)
        if decompress:
            data = minilzo.decompress(data)

        hl = cls.header_length()
        header_bytes = data[:hl]
        value_bytes = data[hl:]

        value = value_bytes.decode(encoding=cls.VENC, errors='ignore')

        if (i := value.find(cls.DSR)) != -1:
            # 결과부 (<DSR>)가 존재하는 경우,
            # <DS>와 <DSR> 사이 decode 불가능한 데이터 제거
            # (안해도 출력엔 지장 없음)
            ds = value[: (value.find(cls.DS) + len(cls.DS))]
            dsr = value[i:]
            value = f'{ds}\n{dsr}'

        return header_bytes, value

    @classmethod
    def decrypt(
        cls,
        path: str | Path,
        header: str | Path | None = None,
        value: str | Path | None = None,
        *,
        write_header=True,
    ):
        """`.eco`, `.ecox`, `.tpl`, `.tplx` 파일 복호화.

        Parameters
        ----------
        path : str | Path
            ECO2 저장 파일 (`.eco`, `.tpl`) 경로
        header : str | Path | None, optional
            저장할 header 파일 경로.
            `None`이면 path의 확장자를 `.header`로 변경한 경로.
        value : str | Path | None, optional
            저장할 value 파일 경로.
            `None`이면 path의 확장자를 `.xml`로 변경한 경로.
        write_header : bool, optional
            header 저장 여부
        """
        path = Path(path)
        header = path.with_suffix(cls.HEXT) if header is None else Path(header)
        value = path.with_suffix(cls.VEXT) if value is None else Path(value)

        logger.log(cls._loglvl('src'), 'Input Path: "{}"', path)
        logger.log(cls._loglvl('dst'), 'Header Path: "{}"', header)
        logger.log(cls._loglvl('dst'), 'Value Path: "{}"', value)

        data = path.read_bytes()
        suffix = path.suffix.lower()
        decrypt = suffix.startswith(cls.EEXT)
        decompress = suffix.endswith('x')

        if decompress and not MINILZO:
            logger.error(
                'MiniLZO.dll을 불러올 수 없습니다. '
                '`ecox`, `tplx` 파일을 해석할 수 없습니다.'
            )

        try:
            hdata, vdata = cls._decrypt(
                data=data, decrypt=decrypt, decompress=decompress
            )
        except ValueError:
            hdata, vdata = cls._decrypt(
                data=data, decrypt=not decrypt, decompress=decompress
            )

        cls._log_header(hdata)

        if write_header:
            header.write_bytes(hdata)

        cls._write_value(path=value, value=vdata)

    @classmethod
    def _encrypt(cls, header: bytes, value: bytes, path: Path):
        encrypted = cls.encrypt_bytes(header + value)
        path.write_bytes(encrypted)

    @classmethod
    def encrypt(
        cls,
        header: str | Path,
        value: str | Path,
        path: str | Path | None = None,
        sftype: Literal['00', '01', '10', 'all'] | None = None,
    ):
        """`.eco` 파일 암호화.

        Parameters
        ----------
        header : str | Path
            Header 파일 경로 (`.header`)
        value : str | Path
            Value 파일 경로 (`.xml`)
        path : str | Path | None, optional
            저장 경로. `None`이면 value의 확장자를 `.eco`로 변경한 경로.
        sftype : Literal['00', '01', '10', 'all'] | None, optional
            Header에 저장되는 SFType.
            `None`이면 header 파일을 수정하지 않음.
            `'all'`이면 모든 SFType (`'00'`, `'01'`, `'10'`)의 파일 저장.
        """
        header = Path(header)
        value = Path(value)
        path = Path(path) if path else value.with_suffix(cls.EEXT)

        logger.log(cls._loglvl('src'), 'Value Path: "{}"', value)
        logger.log(cls._loglvl('dst'), 'Header Path: "{}"', header)
        logger.log(cls._loglvl('dst'), 'Output Path: "{}"', path)

        hdata = header.read_bytes()

        vdata = cls._read_value(path=value).encode(cls.VENC)

        for sf in [sftype] if sftype != 'all' else ['00', '01', '10']:
            h = hdata if sf is None else sf.encode() + hdata[2:]
            p = path if sftype != 'all' else path.with_stem(f'{path.stem}_SF{sf}')

            cls._log_header(h)
            cls._encrypt(header=h, value=vdata, path=p)
