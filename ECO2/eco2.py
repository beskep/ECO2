import contextlib
from itertools import cycle
from os import PathLike
from pathlib import Path
from typing import Literal

from loguru import logger


class Eco2:
    HEADER = (
        (2, 'SF type'),
        (10, 'UI version'),
        (10, 'LG version'),
        (100, 'Name'),
        (256, 'Desc'),
        (19, 'Make time'),
        (19, 'Edit time'),
        (8, 'Password'),
    )
    KEY = (172, 41, 85, 66)
    DS = '</DS>'
    DSR = '<DSR xmlns="http://tempuri.org/DSR.xsd">'

    HENC = 'EUC-KR'
    VENC = 'UTF-8'
    HEXT = '.header'
    VEXT = '.xml'
    EEXT = '.eco'

    _LOGLEVEL = {'header': 'DEBUG', 'src': 'INFO', 'dst': 'DEBUG'}
    DEFAULT_VERBOSE = 2
    verbose = 2  # 1~3

    @classmethod
    def _loglvl(cls, kind: Literal['header', 'src', 'dst']):
        if cls.verbose == cls.DEFAULT_VERBOSE:
            lvl = cls._LOGLEVEL[kind]
        else:
            lvl = 'DEBUG' if cls.verbose < cls.DEFAULT_VERBOSE else 'INFO'

        return lvl

    @classmethod
    def decrypt_bytes(cls, data: bytes):
        return bytes(d ^ k for d, k in zip(data, cycle(cls.KEY), strict=False))

    @classmethod
    def encrypt_bytes(cls, data: bytes):
        return cls.decrypt_bytes(data)

    @classmethod
    def header_length(cls):
        return sum(x[0] for x in cls.HEADER)

    @classmethod
    def _decode_header(cls, data: bytes):
        value: bytes | str
        for length, name in cls.HEADER:
            value, data = data[:length], data[length:]

            with contextlib.suppress(ValueError):
                value = value.decode(cls.HENC)

            yield name, value

    @classmethod
    def _print_header_info(cls, header: bytes):
        lvl = cls._loglvl('header')
        for key, value in cls._decode_header(header):
            logger.log(lvl, '[Header] {:10s}: {}', key, value)

    @classmethod
    def _write_value(cls, path: Path, value: str):
        path.write_text(value.replace('\r\n', '\n'), encoding=cls.VENC)

    @classmethod
    def _read_value(cls, path: Path):
        return path.read_text(encoding=cls.VENC).replace('\n', '\r\n')

    @classmethod
    def _decrypt(cls, data: bytes, *, decrypt: bool):
        if decrypt:
            data = cls.decrypt_bytes(data)

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
        path: str | PathLike,
        header: str | PathLike | None = None,
        value: str | PathLike | None = None,
    ):
        """`.eco`, `.tpl` 파일 복호화.

        Parameters
        ----------
        path : str | PathLike
            ECO2 저장 파일 (`.eco`, `.tpl`) 경로
        header : str | PathLike | None, optional
            저장할 header 파일 경로.
            `None`이면 path의 확장자를 `.header`로 변경한 경로.
        value : str | PathLike | None, optional
            저장할 value 파일 경로.
            `None`이면 path의 확장자를 `.xml`로 변경한 경로.
        """
        path = Path(path)
        header = path.with_suffix(cls.HEXT) if header is None else Path(header)
        value = path.with_suffix(cls.VEXT) if value is None else Path(value)

        logger.log(cls._loglvl('src'), 'Input Path: "{}"', path)
        logger.log(cls._loglvl('dst'), 'Header Path: "{}"', header)
        logger.log(cls._loglvl('dst'), 'Value Path: "{}"', value)

        data = path.read_bytes()
        decrypt = path.suffix.lower() == cls.EEXT

        try:
            hdata, vdata = cls._decrypt(data=data, decrypt=decrypt)
        except ValueError:
            hdata, vdata = cls._decrypt(data=data, decrypt=not decrypt)

        cls._print_header_info(hdata)

        header.write_bytes(hdata)
        cls._write_value(path=value, value=vdata)

    @classmethod
    def _encrypt(cls, header: bytes, value: bytes, path: Path):
        encrypted = cls.encrypt_bytes(header + value)
        path.write_bytes(encrypted)

    @classmethod
    def encrypt(
        cls,
        header: str | PathLike,
        value: str | PathLike,
        path: str | PathLike | None = None,
    ):
        """`.eco` 파일 암호화.

        Parameters
        ----------
        header : str | PathLike
            Header 파일 경로 (`.header`)
        value : str | PathLike
            Value 파일 경로 (`.xml`)
        path : str | PathLike | None, optional
            저장 경로. `None`이면 value의 확장자를 `.eco`로 변경한 경로.
        """
        header = Path(header)
        value = Path(value)
        path = Path(path) if path else value.with_suffix(cls.EEXT)

        logger.log(cls._loglvl('src'), 'Value Path: "{}"', value)
        logger.log(cls._loglvl('dst'), 'Header Path: "{}"', header)
        logger.log(cls._loglvl('dst'), 'Output Path: "{}"', path)

        hdata = header.read_bytes()
        cls._print_header_info(hdata)

        vdata = cls._read_value(path=value).encode(cls.VENC)
        cls._encrypt(header=hdata, value=vdata, path=path)
