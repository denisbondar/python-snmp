__all__ = ["Aes128Cfb"]

import os

from Crypto.Cipher import AES

from snmp.security.usm import PrivProtocol
from snmp.security.usm.priv import DecryptionError
from snmp.typing import *

class Aes128Cfb(PrivProtocol):
    BYTEORDER:  ClassVar[Literal["big"]] = "big"

    BITS:       ClassVar[int] = 128
    INTSIZE:    ClassVar[int] = 4
    BLOCKLEN:   ClassVar[int] = BITS // 8
    KEYLEN:     ClassVar[int] = BLOCKLEN
    SALTLEN:    ClassVar[int] = BLOCKLEN - (2 * INTSIZE)
    SALTWRAP:   ClassVar[int] = 1 << (8 * SALTLEN)

    def __init__(self, key: bytes) -> None:
        if len(key) < self.KEYLEN:
            errmsg = "key must be at least {} bytes long".format(self.KEYLEN)
            raise ValueError(errmsg)

        self.key = key[:self.KEYLEN]
        self.salt = int.from_bytes(os.urandom(self.SALTLEN), self.BYTEORDER)

    def packIV(self, engineBoots: int, engineTime: int, salt: bytes) -> bytes:
        if len(salt) != self.SALTLEN:
            raise ValueError("Invalid salt")

        return b''.join((
            engineBoots.to_bytes(self.INTSIZE, self.BYTEORDER),
            engineTime .to_bytes(self.INTSIZE, self.BYTEORDER),
            salt
        ))

    def decrypt(self,
        data: bytes,
        engineBoots: int,
        engineTime: int,
        salt: bytes,
    ) -> bytes:
        try:
            iv = self.packIV(engineBoots, engineTime, salt)
        except ValueError as err:
            raise DecryptionError(err) from err

        cipher = AES.new(self.key, AES.MODE_CFB, iv=iv, segment_size=self.BITS)

        return cipher.decrypt(data)

    def encrypt(self,
        data: bytes,
        engineBoots: int,
        engineTime: int,
    ) -> Tuple[bytes, bytes]:
        self.salt = (self.salt + 1) % self.SALTWRAP

        salt = self.salt.to_bytes(self.SALTLEN, self.BYTEORDER)
        iv = self.packIV(engineBoots, engineTime, salt)
        cipher = AES.new(self.key, AES.MODE_CFB, iv=iv, segment_size=self.BITS)

        return cipher.encrypt(data), salt
