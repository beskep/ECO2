from pathlib import Path

import pytest

from ECO2.cli import cli
from ECO2.eco2 import Eco2

data_dir = Path(__file__).parent.joinpath('data')
eco2_path = data_dir.joinpath('test.eco')
header_path = data_dir.joinpath('header')
value_path = data_dir.joinpath('value.xml')


def test_eco2():
    encrypted_path = data_dir.joinpath('encrypted.eco')

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)

    Eco2.decrypt(path=eco2_path,
                 save_dir=data_dir,
                 header_name=header_path.stem,
                 value_name=value_path.stem)

    header, value = Eco2._decrypt_eco2_data(eco2_path.read_bytes())
    saved_header = header_path.read_bytes()
    saved_value = Eco2._read_value(value_path)

    assert header == saved_header
    assert hash(value) == hash(saved_value)

    Eco2.encrypt(header_path=header_path,
                 value_path=value_path,
                 save_path=encrypted_path)

    eco2 = eco2_path.read_bytes()
    encrypted = encrypted_path.read_bytes()

    assert hash(eco2) == hash(encrypted)

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)


def test_cli():
    encrypted_path = value_path.with_suffix('.eco')

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)

    try:
        cli([
            'decrypt',
            eco2_path.as_posix(),
            '-s',
            eco2_path.parent.as_posix(),
            '-h',
            header_path.as_posix(),
            '-v',
            value_path.with_suffix('').as_posix(),
        ])
    except SystemExit:
        pass

    assert header_path.exists()
    assert value_path.exists()

    try:
        cli([
            'encrypt',
            header_path.as_posix(),
            value_path.parent.as_posix(),
            '-s',
            header_path.parent.as_posix(),
        ])
    except SystemExit:
        pass

    assert encrypted_path.exists()

    header_path.unlink(missing_ok=True)
    value_path.unlink(missing_ok=True)
    encrypted_path.unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main(['-v'])
