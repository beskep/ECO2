# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pycryptodome>=3.23.0",
# ]
# ///

import base64
import hashlib
import sys
from pathlib import Path

from Crypto.Cipher import DES3  # noqa: S413 # ty:ignore[unresolved-import]


def _dotnet_hash(text: str, length: int) -> bytes:
    sha1 = hashlib.sha1()  # noqa: S324
    sha1.update(text.encode('UTF-16LE'))
    hash_bytes = sha1.digest()

    # C# Utils.CopyArray
    res = bytearray(length)
    copy_len = min(len(hash_bytes), length)
    res[:copy_len] = hash_bytes[:copy_len]
    return bytes(res)


def _main(
    data: Path,
    password: str,
    head_len: int = 3,
    key_len: int = 24,
    iv_len: int = 8,
) -> None:
    raw = data.read_bytes()[head_len:].decode()
    encrypted = base64.b64decode(raw)

    key = _dotnet_hash(password, key_len)
    iv = _dotnet_hash('', iv_len)
    cipher = DES3.new(key=key, mode=DES3.MODE_CBC, iv=iv)
    decrypted: bytes = cipher.decrypt(encrypted)

    # PKCS7 패딩 제거 (3DES 블록 사이즈는 8)
    padding_len = decrypted[-1]
    decrypted = decrypted[:-padding_len]

    text = decrypted.decode('UTF-16LE')

    print(text)  # noqa: T201


if __name__ == '__main__':
    encrypted, password = sys.argv[1:]
    _main(Path(encrypted), password)
