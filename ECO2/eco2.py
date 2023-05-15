import contextlib
from itertools import cycle
from pathlib import Path
from typing import Literal

from loguru import logger

from .utils import StrPath


class Eco2DecodeError(ValueError):
    pass


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

        try:
            value = value_bytes.decode(cls.VENC)
        except ValueError as e:
            # 케이스 설정 부분 (<DS>...</DS>)만 추출하고
            # 결과부 (<DSR>...</DSR>)은 버림
            logger.debug('ECO2 파일의 결과부 (DSR)를 제외합니다.')
            value = value_bytes.decode(cls.VENC, 'replace')

            if cls.DS not in value:
                raise Eco2DecodeError from e

            value = value[: (value.find(cls.DS) + len(cls.DS))]

        return header_bytes, value

    @classmethod
    def decrypt(
        cls,
        path: StrPath,
        header: StrPath | None = None,
        value: StrPath | None = None,
    ):
        """
        `.eco`, `.tpl` 파일 복호화

        Parameters
        ----------
        path : StrPath
            ECO2 저장 파일 (`.eco`, `.tpl`) 경로
        header : StrPath | None, optional
            저장할 header 파일 경로.
            `None`이면 path의 확장자를 `.header`로 변경한 경로.
        value : StrPath | None, optional
            저장할 header 파일 경로.
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
        header: StrPath,
        value: StrPath,
        path: StrPath | None = None,
    ):
        """
        `.eco` 파일 암호화

        Parameters
        ----------
        header : StrPath
            Header 파일 경로 (`.header`)
        value : StrPath
            Value 파일 경로 (`.xml`)
        path : StrPath | None, optional
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
