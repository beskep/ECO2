from itertools import cycle
from pathlib import Path

from loguru import logger


class Eco2:
    header = (
        (2, 'SF type'),
        (10, 'UI version'),
        (10, 'LG version'),
        (100, 'Name'),
        (256, 'Desc'),
        (19, 'Make time'),
        (19, 'Edit time'),
        (8, 'password'),
    )
    key = (172, 41, 85, 66)
    header_encoding = 'EUC-KR'
    value_encoding = 'UTF-8'
    header_ext = '.header'
    value_ext = '.xml'
    ds = '</DS>'

    @classmethod
    def decrypt_bytes(cls, data: bytes):
        return bytes((d ^ k for d, k in zip(data, cycle(cls.key))))

    @classmethod
    def encrypt_bytes(cls, data: bytes):
        return cls.decrypt_bytes(data)

    @classmethod
    def header_length(cls):
        return sum([x[0] for x in cls.header])

    @staticmethod
    def _decode_chunk(b: bytes, length: int):
        data = b[:length]
        bnext = b[length:]

        return data, bnext

    @classmethod
    def _decode_header(cls, data: bytes):
        header = {}
        b = data
        for length, name in cls.header:
            value, b = cls._decode_chunk(b=b, length=length)

            try:
                value = value.decode(cls.header_encoding)
            except ValueError:
                pass

            header[name] = value

        return header

    @classmethod
    def _print_header_info(cls, header: bytes):
        header_dict = cls._decode_header(header)

        for key, value in header_dict.items():
            if key == 'password':
                continue

            logger.info('[HEADER] {:10s}: {}', key, value)

    @classmethod
    def _write_value(cls, path: Path, value: str):
        path.write_text(value.replace('\r\n', '\n'),
                        encoding=cls.value_encoding)

    @classmethod
    def _read_value(cls, path: Path):
        return path.read_text(encoding=cls.value_encoding).replace('\n', '\r\n')

    @classmethod
    def _decrypt(cls, data: bytes, decrypt: bool):
        if decrypt:
            data = cls.decrypt_bytes(data)

        hl = cls.header_length()
        header_bytes = data[:hl]
        value_bytes = data[hl:]

        try:
            value = value_bytes.decode(cls.value_encoding)
        except ValueError:
            # 케이스 설정 부분 (<DS>...</DS>)만 추출하고
            # 결과부 (<DSR>...</DSR>)은 버림
            logger.debug('ECO2 파일의 결과부 (DSR)를 제외합니다.')
            value = value_bytes.decode(cls.value_encoding, 'replace')

            if cls.ds not in value:
                raise ValueError('인코딩 에러')

            value = value[:(value.find(cls.ds) + len(cls.ds))]

        return header_bytes, value

    @classmethod
    def decrypt(cls, path, header_path=None, value_path=None):
        path = Path(path)

        if header_path is None:
            header_path = path.with_suffix(cls.header_ext)
        else:
            header_path = Path(header_path)

        if value_path is None:
            value_path = path.with_suffix(cls.value_ext)
        else:
            value_path = Path(value_path)

        logger.info('Input: {}', path)
        logger.debug('Header: {}', header_path)
        logger.debug('Value: {}', value_path)

        data = path.read_bytes()
        decrypt = (path.suffix == '.eco')
        try:
            header, value = cls._decrypt(data=data, decrypt=decrypt)
        except ValueError:
            header, value = cls._decrypt(data=data, decrypt=(not decrypt))

        cls._print_header_info(header)

        header_path.write_bytes(header)
        cls._write_value(path=value_path, value=value)

    @classmethod
    def _encrypt(cls, header: bytes, value: bytes, save_path: Path):
        encrypted = cls.encrypt_bytes(header + value)
        save_path.write_bytes(encrypted)

    @classmethod
    def encrypt(cls, header_path, value_path, save_path=None):
        header_path = Path(header_path)
        value_path = Path(value_path)

        if save_path:
            save_path = Path(save_path)
        else:
            save_path = value_path.with_suffix('.eco')

        logger.info('Value: {}', value_path)
        logger.info('Header: {}', header_path)
        logger.debug('Output: {}', save_path)

        header = header_path.read_bytes()
        cls._print_header_info(header)

        value = cls._read_value(path=value_path)
        value_bytes = value.encode(cls.value_encoding)

        cls._encrypt(header=header, value=value_bytes, save_path=save_path)
