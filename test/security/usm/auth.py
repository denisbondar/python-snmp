__all__ = [
    "HmacMd5Test", "HmacShaTest", "HmacSha224Test", "HmacSha256Test",
    "HmacSha384Test", "HmacSha512Test",
]

import re
import unittest
from snmp.security.usm.auth import *

class HmacMd5Test(unittest.TestCase):
    def setUp(self):
        self.authProtocol = HmacMd5
        self.engineID = bytes(11) + b"\x02"
        self.secret = b"maplesyrup"

        self.authKey = bytes.fromhex(re.sub(r"\n", "", """
            52 6f 5e ed 9f cc e2 6f 89 64 c2 93 07 87 d8 2b
        """))

        self.digest = bytes.fromhex(re.sub(r"\n", "", """
            07 5f 47 b1 57 95 d1 15 77 df 58 19
        """))

    def testLocalize(self):
        authKey = self.authProtocol.localize(self.secret, self.engineID)
        self.assertEqual(authKey, self.authKey)

    def testSign(self):
        auth = self.authProtocol(self.authKey)
        digest = auth.sign(auth.msgAuthenticationParameters)
        self.assertEqual(auth.msgAuthenticationParameters, bytes(len(digest)))
        self.assertEqual(digest, self.digest)

class HmacShaTest(unittest.TestCase):
    def setUp(self):
        self.authProtocol = HmacSha
        self.engineID = bytes(11) + b"\x02"
        self.secret = b"maplesyrup"

        self.authKey = bytes.fromhex(re.sub(r"\n", "", """
            66 95 fe bc 92 88 e3 62 82 23 5f c7 15 1f 12 84
            97 b3 8f 3f
        """))

        self.digest = bytes.fromhex(re.sub(r"\n", "", """
            60 e3 8c 0e 8d e1 8f e2 b4 17 fc 4d
        """))

    def testLocalize(self):
        authKey = self.authProtocol.localize(self.secret, self.engineID)
        self.assertEqual(authKey, self.authKey)

    def testSign(self):
        auth = self.authProtocol(self.authKey)
        digest = auth.sign(auth.msgAuthenticationParameters)
        self.assertEqual(auth.msgAuthenticationParameters, bytes(len(digest)))
        self.assertEqual(digest, self.digest)

class HmacSha224Test(unittest.TestCase):
    def setUp(self):
        self.authProtocol = HmacSha224
        self.engineID = bytes(11) + b"\x02"
        self.secret = b"maplesyrup"

        self.authKey = bytes.fromhex(re.sub(r"\n", "", """
            0b d8 82 7c 6e 29 f8 06 5e 08 e0 92 37 f1 77 e4
            10 f6 9b 90 e1 78 2b e6 82 07 56 74
        """))

        self.digest = bytes.fromhex(re.sub(r"\n", "", """
            1d 6f 2b fe d5 dc 44 94 12 ec 42 01 72 7f d0 41
        """))

    def testLocalize(self):
        authKey = self.authProtocol.localize(self.secret, self.engineID)
        self.assertEqual(authKey, self.authKey)

    def testSign(self):
        auth = self.authProtocol(self.authKey)
        digest = auth.sign(auth.msgAuthenticationParameters)
        self.assertEqual(auth.msgAuthenticationParameters, bytes(len(digest)))
        self.assertEqual(digest, self.digest)

class HmacSha256Test(unittest.TestCase):
    def setUp(self):
        self.authProtocol = HmacSha256
        self.engineID = bytes(11) + b"\x02"
        self.secret = b"maplesyrup"

        self.authKey = bytes.fromhex(re.sub(r"\n", "", """
            89 82 e0 e5 49 e8 66 db 36 1a 6b 62 5d 84 cc cc
            11 16 2d 45 3e e8 ce 3a 64 45 c2 d6 77 6f 0f 8b
        """))

        self.digest = bytes.fromhex(re.sub(r"\n", "", """
            42 8b f9 6e 69 98 5f f6 3e 87 1d 01 02 53 0b 44
            df 57 63 80 99 35 8f 54
        """))

    def testLocalize(self):
        authKey = self.authProtocol.localize(self.secret, self.engineID)
        self.assertEqual(authKey, self.authKey)

    def testSign(self):
        auth = self.authProtocol(self.authKey)
        digest = auth.sign(auth.msgAuthenticationParameters)
        self.assertEqual(auth.msgAuthenticationParameters, bytes(len(digest)))
        self.assertEqual(digest, self.digest)

class HmacSha384Test(unittest.TestCase):
    def setUp(self):
        self.authProtocol = HmacSha384
        self.engineID = bytes(11) + b"\x02"
        self.secret = b"maplesyrup"

        self.authKey = bytes.fromhex(re.sub(r"\n", "", """
            3b 29 8f 16 16 4a 11 18 42 79 d5 43 2b f1 69 e2
            d2 a4 83 07 de 02 b3 d3 f7 e2 b4 f3 6e b6 f0 45
            5a 53 68 9a 39 37 ee a0 73 19 a6 33 d2 cc ba 78
        """))

        self.digest = bytes.fromhex(re.sub(r"\n", "", """
            17 c5 9b c6 90 3d e9 a7 ee bb 97 a6 6f f2 37 1b
            8d 77 2a 59 95 1f 81 96 c2 54 2a 19 75 07 b3 af
        """))

    def testLocalize(self):
        authKey = self.authProtocol.localize(self.secret, self.engineID)
        self.assertEqual(authKey, self.authKey)

    def testSign(self):
        auth = self.authProtocol(self.authKey)
        digest = auth.sign(auth.msgAuthenticationParameters)
        self.assertEqual(auth.msgAuthenticationParameters, bytes(len(digest)))
        self.assertEqual(digest, self.digest)

class HmacSha512Test(unittest.TestCase):
    def setUp(self):
        self.authProtocol = HmacSha512
        self.engineID = bytes(11) + b"\x02"
        self.secret = b"maplesyrup"

        self.authKey = bytes.fromhex(re.sub(r"\n", "", """
            22 a5 a3 6c ed fc c0 85 80 7a 12 8d 7b c6 c2 38
            21 67 ad 6c 0d bc 5f df f8 56 74 0f 3d 84 c0 99
            ad 1e a8 7a 8d b0 96 71 4d 97 88 bd 54 40 47 c9
            02 1e 42 29 ce 27 e4 c0 a6 92 50 ad fc ff bb 0b
        """))

        self.digest = bytes.fromhex(re.sub(r"\n", "", """
            63 11 9e 45 4a 13 82 fa b6 90 e0 34 b6 3b 59 9a
            4d 5c 1a 40 c0 c6 fb 0e 2d cb 10 c7 6c 45 4e 29
            14 84 5a 89 a1 cd b7 42 4a f5 c7 07 11 c3 b9 f4
        """))

    def testLocalize(self):
        authKey = self.authProtocol.localize(self.secret, self.engineID)
        self.assertEqual(authKey, self.authKey)

    def testSign(self):
        auth = self.authProtocol(self.authKey)
        digest = auth.sign(auth.msgAuthenticationParameters)
        self.assertEqual(auth.msgAuthenticationParameters, bytes(len(digest)))
        self.assertEqual(digest, self.digest)

if __name__ == '__main__':
    unittest.main()
