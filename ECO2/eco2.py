from itertools import cycle
from pathlib import Path

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

    HENC = 'EUC-KR'
    VENC = 'UTF-8'

    HEXT = '.header'
    VEXT = '.xml'

    DS = '</DS>'

    @classmethod
    def decrypt_bytes(cls, data: bytes):
        return bytes(d ^ k for d, k in zip(data, cycle(cls.KEY)))

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

            try:
                value = value.decode(cls.HENC)
            except ValueError:
                pass

            yield name, value

    @classmethod
    def _print_header_info(cls, header: bytes):
        for key, value in cls._decode_header(header):
            if key == 'password':
                continue

            logger.info('[HEADER] {:10s}: {}', key, value)

    @classmethod
    def _write_value(cls, path: Path, value: str):
        path.write_text(value.replace('\r\n', '\n'), encoding=cls.VENC)

    @classmethod
    def _read_value(cls, path: Path):
        return path.read_text(encoding=cls.VENC).replace('\n', '\r\n')

    @classmethod
    def _decrypt(cls, data: bytes, decrypt: bool):
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
                raise ValueError('인코딩 에러') from e

            value = value[:(value.find(cls.DS) + len(cls.DS))]

        return header_bytes, value

    @classmethod
    def decrypt(cls,
                path: str | Path,
                header: None | str | Path = None,
                value: None | str | Path = None):
        path = Path(path)
        header = path.with_suffix(cls.HEXT) if header is None else Path(header)
        value = path.with_suffix(cls.VEXT) if value is None else Path(value)

        logger.info('Input: "{}"', path)
        logger.debug('Header: "{}"', header)
        logger.debug('Value: "{}"', value)

        data = path.read_bytes()
        decrypt = path.suffix.lower() == '.eco'

        try:
            hdata, vdata = cls._decrypt(data=data, decrypt=decrypt)
        except ValueError:
            hdata, vdata = cls._decrypt(data=data, decrypt=(not decrypt))

        cls._print_header_info(hdata)

        header.write_bytes(hdata)
        cls._write_value(path=value, value=vdata)

    @classmethod
    def _encrypt(cls, header: bytes, value: bytes, save_path: Path):
        encrypted = cls.encrypt_bytes(header + value)
        save_path.write_bytes(encrypted)

    @classmethod
    def encrypt(cls,
                header: str | Path,
                value: str | Path,
                save: None | str | Path = None):
        header = Path(header)
        value = Path(value)
        save = Path(save) if save else value.with_suffix('.eco')

        logger.info('Value: "{}"', value)
        logger.info('Header: "{}"', header)
        logger.debug('Output: "{}"', save)

        hdata = header.read_bytes()
        cls._print_header_info(hdata)

        vdata = cls._read_value(path=value).encode(cls.VENC)
        cls._encrypt(header=hdata, value=vdata, save_path=save)
