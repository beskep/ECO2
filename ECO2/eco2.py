from itertools import cycle
from pathlib import Path
from typing import Union


class Eco2:
    header = (
        (2, 'SF type'),
        (10, 'UI version'),
        (10, 'LG version'),
        (100, 'Name'),
        (256, 'Desc'),
        (19, 'Make time'),
        (19, 'Edit time'),
        (8, 'unknown'),
    )
    key = (172, 41, 85, 66)
    encoding = 'UTF-8'
    value_ext = '.xml'

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
                value = value.decode('euc-kr')
            except ValueError:
                pass

            header[name] = value

        return header

    @classmethod
    def _decrypt_eco2_data(cls, data: bytes):
        decrypted = cls.decrypt_bytes(data)
        hl = cls.header_length()

        header_bytes = decrypted[:hl]
        value_bytes = decrypted[hl:]
        value = value_bytes.decode()

        return header_bytes, value

    @classmethod
    def _write_value(cls, path: Path, value: str):
        path.write_text(value.replace('\r\n', '\n'), encoding=cls.encoding)

    @classmethod
    def _read_value(cls, path: Path):
        return path.read_text(encoding=cls.encoding).replace('\n', '\r\n')

    @classmethod
    def _print_header_info(cls, header: bytes):
        header_dict = cls._decode_header(header)

        print('Header info:')

        for key, value in header_dict.items():
            if key == 'unknown':
                continue

            print(f'    {key:10s}: {value}')

    @classmethod
    def decrypt(cls,
                path: Union[str, Path],
                save_dir=None,
                header_name=None,
                value_name=None):
        path = Path(path)
        save_dir = path.parent if save_dir is None else Path(save_dir)
        if not save_dir.exists():
            raise FileNotFoundError(save_dir)

        if header_name is None:
            header_name = 'header'
        if value_name is None:
            value_name = path.stem

        data = path.read_bytes()
        bheader, value = cls._decrypt_eco2_data(data)

        cls._print_header_info(bheader)

        header_path = save_dir.joinpath(header_name)
        header_path.write_bytes(bheader)

        value_path = save_dir.joinpath(value_name + cls.value_ext)
        cls._write_value(path=value_path, value=value)

    @classmethod
    def encrypt(cls, header_path, value_path, save_path=None):
        if save_path is None:
            save_path = 'output.eco'

        header_path = Path(header_path)
        value_path = Path(value_path)
        save_path = Path(save_path)

        bheader = header_path.read_bytes()
        cls._print_header_info(bheader)

        value = cls._read_value(path=value_path)
        bvalue = value.encode()

        data = bheader + bvalue
        encrypted = cls.encrypt_bytes(data)

        save_path.write_bytes(encrypted)

    @classmethod
    def encrypt_dir(cls, header_path, value_path, save_dir=None):
        header_path = Path(header_path)
        value_path = Path(value_path)

        save_dir = value_path if save_dir is None else Path(save_dir)
        if not save_dir.is_dir():
            save_dir = save_dir.parent

        if value_path.is_dir():
            vps = value_path.glob(f'*{cls.value_ext}')
        else:
            vps = [value_path]

        for vp in vps:
            cls.encrypt(header_path=header_path,
                        value_path=vp,
                        save_path=save_dir.joinpath(f'{vp.stem}.eco'))
