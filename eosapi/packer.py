import struct
import calendar
import datetime
from .exceptions import EosApiException
import re
from typing import List, Tuple
import hashlib
from cryptos import hash_to_int, encode_privkey, decode, encode, \
    hmac, fast_multiply, G, inv, N, decode_privkey, get_privkey_format

class EosType:
    size: int = None
    fmt: str = None

    @classmethod
    def pack(cls, value: int) -> bytes:
        return struct.pack(cls.fmt, value)

    @classmethod
    def unpack(cls, value: bytes) -> int:
        return struct.unpack(cls.fmt, value[:cls.size])[0]

    @classmethod
    def pack_array(cls, items: list) -> bytes:
        mbytes = b""
        mbytes += VarUint32.pack(len(items))
        for item in items:
            mbytes += cls.pack(item)
        return mbytes

    @classmethod
    def unpack_array(cls, packed_bytes: bytes) -> List:
        size, array_len = VarUint32.unpack(packed_bytes)
        packed_bytes = packed_bytes[size:]
        values = []
        for i in range(0, array_len):
            value = cls.unpack(packed_bytes)
            values.append(value)
            packed_bytes = packed_bytes[cls.size:]
        return values


class Bytes(EosType):

    @classmethod
    def pack(cls, value: bytes) -> bytes:
        return value

    @classmethod
    def unpack(cls, value: bytes) -> bytes:
        return value


class Time(EosType):
    size = 4

    @classmethod
    def pack(cls, value: datetime.datetime) -> bytes:
        seconds = calendar.timegm(value.timetuple())
        return Uint32.pack(seconds)

    @classmethod
    def unpack(cls, value: bytes) -> datetime.datetime:
        seconds = Uint32.unpack(value)
        return datetime.datetime.utcfromtimestamp(seconds)


class Name(EosType):
    size = 8

    @classmethod
    def pack(cls, value: str) -> bytes:
        if len(value) > 13 or not re.match(r"^[\.a-z1-5]*[a-z1-5]+[\.a-z1-5]*$", value):
            raise EosApiException("invalid name")
        value_uint64 = string_to_uint64(value)
        return Uint64.pack(value_uint64)

    @classmethod
    def unpack(cls, value: bytes) -> str:
        value_uint64 = Uint64.unpack(value)
        return uint64_to_string(value_uint64)


class Int8(EosType):
    size = 1
    fmt = "<b"


class Uint8(EosType):
    size = 1
    fmt = "<B"


class Uint16(EosType):
    size = 2
    fmt = "<H"


class Uint32(EosType):
    size = 4
    fmt = "<I"


class Uint64(EosType):
    size = 8
    fmt = "<Q"


class VarUint32(EosType):

    @classmethod
    def pack(cls, value: int) -> bytes:
        mbytes = b""
        val = value
        while True:
            b = val & 0x7F
            val >>= 7
            b |= (val > 0) << 7
            uint8 = Uint8.pack(b)
            mbytes += bytes(uint8)
            if not val:
                break
        return mbytes

    @classmethod
    def unpack(value: bytes) -> Tuple[int, int]:
        offset = 0
        value = 0
        size = 0
        for n, byte in enumerate(value):
            # only the 7 first bits matter
            partial_value = byte & 0x7F
            partial_value_offset = partial_value << offset
            value |= partial_value_offset
            offset += 7
            size = n
            if n >= 8:
                break
            # first bit (carry) off
            if not byte & 0x80:
                break
        return size, value


def string_to_uint64(s: str):
    if len(s) > 13:
        raise EosApiException("invalid string length")
    name = 0
    for i in range(0, min(len(s), 12)):
        name |= (char_to_symbol(ord(s[i])) & 0x1F) << (64 - 5 * (i + 1))
    if len(s) == 13:
        name |= char_to_symbol(ord(s[12])) & 0x0F
    return name


def uint64_to_string(n, strip_dots=False):
    charmap = ".12345abcdefghijklmnopqrstuvwxyz"
    s = bytearray(13 * b".")
    tmp = n
    for i in range(0, 13):
        c = charmap[tmp & (0x0F if i == 0 else 0x1F)]
        s[12 - i] = ord(c)
        tmp >>= 4 if i == 0 else 5
    s = s.decode("utf8")
    if strip_dots:
        s = s.strip(".")
    return s


def char_to_symbol(c):
    if ord("a") <= c <= ord("z"):
        return (c - ord("a")) + 6
    if ord("1") <= c <= ord("5"):
        return (c - ord("1")) + 1
    return 0


def endian_reverse_u32(x):
    x = x & 0xFFFFFFFF
    return ((x >> 0x18) & 0xFF) \
           | (((x >> 0x10) & 0xFF) << 0x08) \
           | (((x >> 0x08) & 0xFF) << 0x10) \
           | (((x) & 0xFF) << 0x18)


def get_tapos_info(block_id):
    block_id_bin = bytes.fromhex(block_id)

    hash0 = struct.unpack("<Q", block_id_bin[0:8])[0]
    hash1 = struct.unpack("<Q", block_id_bin[8:16])[0]

    ref_block_num = endian_reverse_u32(hash0) & 0xFFFF
    ref_block_prefix = hash1 & 0xFFFFFFFF

    return ref_block_num, ref_block_prefix


def deterministic_generate_k_nonce(msghash, priv, nonce):
    v = b'\x01' * 32
    k = b'\x00' * 32
    priv = encode_privkey(priv, 'bin')
    msghash = encode(hash_to_int(msghash) + nonce, 256, 32)
    k = hmac.new(k, v + b'\x00' + priv + msghash, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b'\x01' + priv + msghash, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    return decode(hmac.new(k, v, hashlib.sha256).digest(), 256)


def ecdsa_raw_sign_nonce(msghash, priv, nonce):
    z = hash_to_int(msghash)
    k = deterministic_generate_k_nonce(msghash, priv, nonce)

    r, y = fast_multiply(G, k)
    s = inv(k, N) * (z + r * decode_privkey(priv)) % N

    v, r, s = 27 + ((y % 2) ^ (0 if s * 2 < N else 1)), r, s if s * 2 < N else N - s
    if 'compressed' in get_privkey_format(priv):
        v += 4
    return v, r, s


# like https://github.com/EOSIO/eosjs-ecc/commit/09c823ac4c4fb4f7257d8ed2df45a34215a8c537#diff-e8c843fd1f732a963ec41decb2e69133R241
def is_canonical(c):
    return not (c[1] & 0x80) \
           and not (c[1] == 0 and not (c[2] & 0x80)) \
           and not (c[33] & 0x80) \
           and not (c[33] == 0 and not (c[34] & 0x80))


def ripmed160(data):
    h = hashlib.new('ripemd160')
    h.update(data)
    return h.digest()
