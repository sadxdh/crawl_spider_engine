"""
Geetest v4  w 参数纯 Python 加密实现

支持两种加密模式（由 /load 返回的 pt 决定）：
  pt=1 → AES-128-CBC + RSA-1024
  pt=2 → SM4-CBC + SM2
"""

import os
import secrets
import struct
from hashlib import md5

# ── 常量 ─────────────────────────────────────────────────────────────────────

_AES_IV = b"0000000000000000"

_RSA_N = int(
    "00C1E3934D1614465B33053E7F48EE4EC87B14B95EF88947713D25EECBFF7E74"
    "C7977D02DC1D9451F79DD5D1C10C29ACB6A9B4D6FB7D0A0279B6719E1772565F"
    "09AF627715919221AEF91899CAE08C0D686D748B20A3603BE2318CA6BC2B59706"
    "592A9219D0BF05C9F65023A21D2330807252AE0066D59CEEFA5F2748EA80BAB81",
    16,
)
_RSA_E = 0x10001
_RSA_KEY_BYTES = 128  # 1024-bit

_SM4_IV = b"0000000000000000"

_SM2_PUB_KEY = (
    "9a4ea935b2576f37516d9b29cd8d8cc9bffe548ba6853253ba20f4ba44fba8c9"
    "e97a398882769aa0dd1e3e1b5601429287303880ca17bd244ed73bf702a68fc7"
)

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _guid() -> str:
    return secrets.token_hex(8)


def _array_to_hex(data: list[int] | bytes) -> str:
    return bytes(data).hex()


def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - len(data) % block_size
    return data + bytes([pad_len] * pad_len)


# ── AES-128-CBC ──────────────────────────────────────────────────────────────

# 标准 AES S-box
_AES_SBOX = bytes([
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
])

_AES_RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]

def _xtime(a: int) -> int:
    return ((a << 1) ^ 0x11b) & 0xff if a & 0x80 else (a << 1) & 0xff

def _mix_single(a: int, b: int) -> int:
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r

def _aes_key_expansion(key: bytes) -> list[list[int]]:
    nk, nr = 4, 10
    w = []
    for i in range(nk):
        w.append(list(key[4*i:4*i+4]))
    for i in range(nk, 4*(nr+1)):
        temp = list(w[i-1])
        if i % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [_AES_SBOX[b] for b in temp]
            temp[0] ^= _AES_RCON[i // nk - 1]
        w.append([w[i-nk][j] ^ temp[j] for j in range(4)])
    return w

def _aes_sub_bytes(state: list[list[int]]) -> None:
    for i in range(4):
        for j in range(4):
            state[i][j] = _AES_SBOX[state[i][j]]

def _aes_shift_rows(state: list[list[int]]) -> None:
    for i in range(1, 4):
        state[i] = state[i][i:] + state[i][:i]

def _aes_mix_columns(state: list[list[int]]) -> None:
    for j in range(4):
        col = [state[i][j] for i in range(4)]
        state[0][j] = _mix_single(2,col[0])^_mix_single(3,col[1])^col[2]^col[3]
        state[1][j] = col[0]^_mix_single(2,col[1])^_mix_single(3,col[2])^col[3]
        state[2][j] = col[0]^col[1]^_mix_single(2,col[2])^_mix_single(3,col[3])
        state[3][j] = _mix_single(3,col[0])^col[1]^col[2]^_mix_single(2,col[3])

def _aes_add_round_key(state: list[list[int]], rk: list[list[int]], rnd: int) -> None:
    for j in range(4):
        for i in range(4):
            state[i][j] ^= rk[rnd*4+j][i]

def _aes_encrypt_block(block: bytes, round_keys: list[list[int]]) -> bytes:
    state = [[0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            state[i][j] = block[j*4+i]
    _aes_add_round_key(state, round_keys, 0)
    for rnd in range(1, 10):
        _aes_sub_bytes(state)
        _aes_shift_rows(state)
        _aes_mix_columns(state)
        _aes_add_round_key(state, round_keys, rnd)
    _aes_sub_bytes(state)
    _aes_shift_rows(state)
    _aes_add_round_key(state, round_keys, 10)
    out = bytearray(16)
    for i in range(4):
        for j in range(4):
            out[j*4+i] = state[i][j]
    return bytes(out)

def aes_128_cbc_encrypt(plaintext: str, key: str) -> list[int]:
    key_bytes = key.encode("utf-8")
    data = _pkcs7_pad(plaintext.encode("utf-8"))
    rk = _aes_key_expansion(key_bytes)
    prev = bytearray(_AES_IV)
    result = []
    for off in range(0, len(data), 16):
        block = bytearray(data[off:off+16])
        for i in range(16):
            block[i] ^= prev[i]
        enc = _aes_encrypt_block(bytes(block), rk)
        result.extend(enc)
        prev = bytearray(enc)
    return result


# ── RSA-1024 PKCS#1 v1.5 加密 ───────────────────────────────────────────────

def _rsa_encrypt(data: str) -> str:
    msg = data.encode("utf-8")
    k = _RSA_KEY_BYTES
    if len(msg) > k - 11:
        raise ValueError("RSA plaintext too long")
    ps_len = k - len(msg) - 3
    ps = bytearray()
    while len(ps) < ps_len:
        b = os.urandom(1)
        if b[0] != 0:
            ps.append(b[0])
    em = b"\x00\x02" + bytes(ps) + b"\x00" + msg
    m = int.from_bytes(em, "big")
    c = pow(m, _RSA_E, _RSA_N)
    return format(c, f"0{k*2}x")


# ── SM4 ──────────────────────────────────────────────────────────────────────

_SM4_SBOX = bytes([
    0xd6,0x90,0xe9,0xfe,0xcc,0xe1,0x3d,0xb7,0x16,0xb6,0x14,0xc2,0x28,0xfb,0x2c,0x05,
    0x2b,0x67,0x9a,0x76,0x2a,0xbe,0x04,0xc3,0xaa,0x44,0x13,0x26,0x49,0x86,0x06,0x99,
    0x9c,0x42,0x50,0xf4,0x91,0xef,0x98,0x7a,0x33,0x54,0x0b,0x43,0xed,0xcf,0xac,0x62,
    0xe4,0xb3,0x1c,0xa9,0xc9,0x08,0xe8,0x95,0x80,0xdf,0x94,0xfa,0x75,0x8f,0x3f,0xa6,
    0x47,0x07,0xa7,0xfc,0xf3,0x73,0x17,0xba,0x83,0x59,0x3c,0x19,0xe6,0x85,0x4f,0xa8,
    0x68,0x6b,0x81,0xb2,0x71,0x64,0xda,0x8b,0xf8,0xeb,0x0f,0x4b,0x70,0x56,0x9d,0x35,
    0x1e,0x24,0x0e,0x5e,0x63,0x58,0xd1,0xa2,0x25,0x22,0x7c,0x3b,0x01,0x21,0x78,0x87,
    0xd4,0x00,0x46,0x57,0x9f,0xd3,0x27,0x52,0x4c,0x36,0x02,0xe7,0xa0,0xc4,0xc8,0x9e,
    0xea,0xbf,0x8a,0xd2,0x40,0xc7,0x38,0xb5,0xa3,0xf7,0xf2,0xce,0xf9,0x61,0x15,0xa1,
    0xe0,0xae,0x5d,0xa4,0x9b,0x34,0x1a,0x55,0xad,0x93,0x32,0x30,0xf5,0x8c,0xb1,0xe3,
    0x1d,0xf6,0xe2,0x2e,0x82,0x66,0xca,0x60,0xc0,0x29,0x23,0xab,0x0d,0x53,0x4e,0x6f,
    0xd5,0xdb,0x37,0x45,0xde,0xfd,0x8e,0x2f,0x03,0xff,0x6a,0x72,0x6d,0x6c,0x5b,0x51,
    0x8d,0x1b,0xaf,0x92,0xbb,0xdd,0xbc,0x7f,0x11,0xd9,0x5c,0x41,0x1f,0x10,0x5a,0xd8,
    0x0a,0xc1,0x31,0x88,0xa5,0xcd,0x7b,0xbd,0x2d,0x74,0xd0,0x12,0xb8,0xe5,0xb4,0xb0,
    0x89,0x69,0x97,0x4a,0x0c,0x96,0x77,0x7e,0x65,0xb9,0xf1,0x09,0xc5,0x6e,0xc6,0x84,
    0x18,0xf0,0x7d,0xec,0x3a,0xdc,0x4d,0x20,0x79,0xee,0x5f,0x3e,0xd7,0xcb,0x39,0x48,
])

_SM4_FK = [0xa3b1bac6, 0x56aa3350, 0x677d9197, 0xb27022dc]
_SM4_CK = [
    0x00070e15,0x1c232a31,0x383f464d,0x545b6269,
    0x70777e85,0x8c939aa1,0xa8afb6bd,0xc4cbd2d9,
    0xe0e7eef5,0xfc030a11,0x181f262d,0x343b4249,
    0x50575e65,0x6c737a81,0x888f969d,0xa4abb2b9,
    0xc0c7ced5,0xdce3eaf1,0xf8ff060d,0x141b2229,
    0x30373e45,0x4c535a61,0x686f767d,0x848b9299,
    0xa0a7aeb5,0xbcc3cad1,0xd8dfe6ed,0xf4fb0209,
    0x10171e25,0x2c333a41,0x484f565d,0x646b7279,
]

def _sm4_rotl(x: int, n: int) -> int:
    return ((x << n) | (x >> (32 - n))) & 0xffffffff

def _sm4_tau(x: int) -> int:
    return (
        (_SM4_SBOX[(x >> 24) & 0xff] << 24) |
        (_SM4_SBOX[(x >> 16) & 0xff] << 16) |
        (_SM4_SBOX[(x >>  8) & 0xff] <<  8) |
        (_SM4_SBOX[ x        & 0xff])
    )

def _sm4_L(b: int) -> int:
    return b ^ _sm4_rotl(b,2) ^ _sm4_rotl(b,10) ^ _sm4_rotl(b,18) ^ _sm4_rotl(b,24)

def _sm4_L_prime(b: int) -> int:
    return b ^ _sm4_rotl(b, 13) ^ _sm4_rotl(b, 23)

def _sm4_T(x: int) -> int:
    return _sm4_L(_sm4_tau(x))

def _sm4_round_keys(key: bytes) -> list[int]:
    mk = [int.from_bytes(key[i*4:(i+1)*4], "big") for i in range(4)]
    k = [mk[i] ^ _SM4_FK[i] for i in range(4)]
    rk = []
    for i in range(32):
        tmp = k[1] ^ k[2] ^ k[3] ^ _SM4_CK[i]
        rk_i = k[0] ^ _sm4_L_prime(_sm4_tau(tmp))
        rk.append(rk_i)
        k = [k[1], k[2], k[3], rk_i]
    return rk

def _sm4_encrypt_block(block: bytes, rk: list[int]) -> bytes:
    x = [int.from_bytes(block[i*4:(i+1)*4], "big") for i in range(4)]
    for i in range(32):
        tmp = x[1] ^ x[2] ^ x[3] ^ rk[i]
        x_new = x[0] ^ _sm4_T(tmp)
        x = [x[1], x[2], x[3], x_new]
    out = b""
    for v in reversed(x):
        out += v.to_bytes(4, "big")
    return out

def sm4_cbc_encrypt(plaintext: str, key: str) -> list[int]:
    key_bytes = key.encode("utf-8")
    data = _pkcs7_pad(plaintext.encode("utf-8"))
    rk = _sm4_round_keys(key_bytes)
    prev = bytearray(_SM4_IV)
    result = []
    for off in range(0, len(data), 16):
        block = bytearray(data[off:off+16])
        for i in range(16):
            block[i] ^= prev[i]
        enc = _sm4_encrypt_block(bytes(block), rk)
        result.extend(enc)
        prev = bytearray(enc)
    return result


# ── SM2 加密 ─────────────────────────────────────────────────────────────────

# SM2 曲线参数 (sm2p256v1)
_SM2_P  = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
_SM2_A  = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
_SM2_B  = 0x28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93
_SM2_N  = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123
_SM2_GX = 0x32C4AE2C1F1981195F9904466A39C9948FE30BBFF2660BE1715A4589334C74C7
_SM2_GY = 0xBC3736A2F4F6779C59BDCEE36B692153D0A9877CC62A474002DF32E52139F0A0


def _sm2_inv_mod(a: int, m: int) -> int:
    return pow(a, m - 2, m)


class _SM2Point:
    __slots__ = ("x", "y", "inf")

    def __init__(self, x: int = 0, y: int = 0, inf: bool = False):
        self.x = x
        self.y = y
        self.inf = inf

    def double(self) -> "_SM2Point":
        if self.inf:
            return _SM2Point(inf=True)
        lam = (3 * self.x * self.x + _SM2_A) * _sm2_inv_mod(2 * self.y, _SM2_P) % _SM2_P
        x3 = (lam * lam - 2 * self.x) % _SM2_P
        y3 = (lam * (self.x - x3) - self.y) % _SM2_P
        return _SM2Point(x3, y3)

    def __add__(self, other: "_SM2Point") -> "_SM2Point":
        if self.inf:
            return other
        if other.inf:
            return self
        if self.x == other.x:
            if self.y == other.y:
                return self.double()
            return _SM2Point(inf=True)
        lam = (other.y - self.y) * _sm2_inv_mod(other.x - self.x, _SM2_P) % _SM2_P
        x3 = (lam * lam - self.x - other.x) % _SM2_P
        y3 = (lam * (self.x - x3) - self.y) % _SM2_P
        return _SM2Point(x3, y3)

    def __mul__(self, k: int) -> "_SM2Point":
        result = _SM2Point(inf=True)
        addend = self
        while k:
            if k & 1:
                result = result + addend
            addend = addend.double()
            k >>= 1
        return result


def _sm3_hash(data: bytes) -> bytes:
    """SM3 哈希，用于 SM2 加密中的 KDF 和 C3"""
    IV = [
        0x7380166f, 0x4914b2b9, 0x172442d7, 0xda8a0600,
        0xa96f30bc, 0x163138aa, 0xe38dee4d, 0xb0fb0e4e,
    ]

    def _rotl32(x: int, n: int) -> int:
        return ((x << n) | (x >> (32 - n))) & 0xffffffff

    def _p0(x: int) -> int:
        return x ^ _rotl32(x, 9) ^ _rotl32(x, 17)

    def _p1(x: int) -> int:
        return x ^ _rotl32(x, 15) ^ _rotl32(x, 23)

    def _ff(j: int, x: int, y: int, z: int) -> int:
        if j < 16:
            return x ^ y ^ z
        return (x & y) | (x & z) | (y & z)

    def _gg(j: int, x: int, y: int, z: int) -> int:
        if j < 16:
            return x ^ y ^ z
        return (x & y) | (~x & 0xffffffff & z)

    def _t(j: int) -> int:
        return 0x79cc4519 if j < 16 else 0x7a879d8a

    msg = bytearray(data)
    bit_len = len(data) * 8
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0x00)
    msg.extend(bit_len.to_bytes(8, "big"))

    v = list(IV)
    for i in range(0, len(msg), 64):
        w = [int.from_bytes(msg[i+j*4:i+j*4+4], "big") for j in range(16)]
        for j in range(16, 68):
            w.append(_p1(w[j-16] ^ w[j-9] ^ _rotl32(w[j-3], 15)) ^ _rotl32(w[j-13], 7) ^ w[j-6])
        w_prime = [w[j] ^ w[j+4] for j in range(64)]

        a, b, c, d, e, f, g, h = v
        for j in range(64):
            ss1 = _rotl32((_rotl32(a, 12) + e + _rotl32(_t(j), j % 32)) & 0xffffffff, 7)
            ss2 = ss1 ^ _rotl32(a, 12)
            tt1 = (_ff(j, a, b, c) + d + ss2 + w_prime[j]) & 0xffffffff
            tt2 = (_gg(j, e, f, g) + h + ss1 + w[j]) & 0xffffffff
            d = c
            c = _rotl32(b, 9)
            b = a
            a = tt1
            h = g
            g = _rotl32(f, 19)
            f = e
            e = _p0(tt2)
        v = [v[i] ^ [a,b,c,d,e,f,g,h][i] for i in range(8)]

    return b"".join(x.to_bytes(4, "big") for x in v)


def _sm2_kdf(z: bytes, klen: int) -> bytes:
    ct = 1
    ha = b""
    while len(ha) < klen:
        ha += _sm3_hash(z + ct.to_bytes(4, "big"))
        ct += 1
    return ha[:klen]


def _sm2_encrypt(data: str) -> str:
    msg = data.encode("utf-8")
    pub_hex = _SM2_PUB_KEY
    px = int(pub_hex[:64], 16)
    py = int(pub_hex[64:], 16)
    pb = _SM2Point(px, py)
    g = _SM2Point(_SM2_GX, _SM2_GY)

    while True:
        k = int.from_bytes(os.urandom(32), "big") % (_SM2_N - 1) + 1
        c1_point = g * k
        s = pb * k
        x2 = s.x.to_bytes(32, "big")
        y2 = s.y.to_bytes(32, "big")
        t = _sm2_kdf(x2 + y2, len(msg))
        if any(b != 0 for b in t):
            break

    c2 = bytes(a ^ b for a, b in zip(msg, t))
    c3 = _sm3_hash(x2 + msg + y2)

    c1_hex = format(c1_point.x, "064x") + format(c1_point.y, "064x")
    c3_hex = c3.hex()
    c2_hex = c2.hex()
    # cipherMode=1: C1 || C3 || C2
    return c1_hex + c3_hex + c2_hex


# ── 对外接口 ─────────────────────────────────────────────────────────────────

def encrypt_w(plaintext: str, pt: str) -> str:
    """
    生成 Geetest v4 的 w 参数。

    plaintext: JSON 字符串（已包含 em 字段）
    pt:        /load 返回的 pt 值（"1" 或 "2"）
    """
    random_key = _guid()

    if pt == "1":
        encrypted_data = aes_128_cbc_encrypt(plaintext, random_key)
        encrypted_key = _rsa_encrypt(random_key)
        while len(encrypted_key) != 256:
            random_key = _guid()
            encrypted_data = aes_128_cbc_encrypt(plaintext, random_key)
            encrypted_key = _rsa_encrypt(random_key)
        return _array_to_hex(encrypted_data) + encrypted_key

    elif pt == "2":
        encrypted_data = sm4_cbc_encrypt(plaintext, random_key)
        encrypted_key = _sm2_encrypt(random_key)
        return _array_to_hex(encrypted_data) + encrypted_key

    else:
        raise ValueError(f"不支持的 pt 值: {pt}")
