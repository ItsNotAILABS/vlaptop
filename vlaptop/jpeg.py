"""Baseline JPEG encoder. Stdlib only, so the framebuffer is real on every device."""

from __future__ import annotations

import math

_ZZ = (
    0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5,
    12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63,
)
_QY = (
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99,
)
_QC = (
    17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99,
    24, 26, 56, 99, 99, 99, 99, 99, 47, 66, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
)
_LDC_BITS = (0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0)
_LDC_VAL = tuple(range(12))
_CDC_BITS = (0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0)
_CDC_VAL = tuple(range(12))
_LAC_BITS = (0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7D)
_LAC_VAL = (
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
    0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0,
    0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
    0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
    0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
    0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5,
    0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
    0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
    0xF9, 0xFA,
)
_CAC_BITS = (0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77)
_CAC_VAL = (
    0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21, 0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61, 0x71,
    0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91, 0xA1, 0xB1, 0xC1, 0x09, 0x23, 0x33, 0x52, 0xF0,
    0x15, 0x62, 0x72, 0xD1, 0x0A, 0x16, 0x24, 0x34, 0xE1, 0x25, 0xF1, 0x17, 0x18, 0x19, 0x1A, 0x26,
    0x27, 0x28, 0x29, 0x2A, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
    0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
    0x69, 0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
    0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5,
    0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3,
    0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA,
    0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
    0xF9, 0xFA,
)
_COS = tuple(tuple(math.cos((2 * n + 1) * k * math.pi / 16) for n in range(8)) for k in range(8))
_CK = tuple((1 / math.sqrt(2)) if k == 0 else 1.0 for k in range(8))


def _codes(bits: tuple, vals: tuple) -> dict:
    found = {}
    code = 0
    index = 0
    for length, count in enumerate(bits, start=1):
        for _ in range(count):
            found[vals[index]] = (code, length)
            index += 1
            code += 1
        code <<= 1
    return found


_HUFF = {
    (0, 0): _codes(_LDC_BITS, _LDC_VAL),
    (1, 0): _codes(_CDC_BITS, _CDC_VAL),
    (0, 1): _codes(_LAC_BITS, _LAC_VAL),
    (1, 1): _codes(_CAC_BITS, _CAC_VAL),
}


class _Bits:
    def __init__(self) -> None:
        self.buf = bytearray()
        self.acc = 0
        self.n = 0

    def put(self, code: int, length: int) -> None:
        self.acc = (self.acc << length) | (code & ((1 << length) - 1))
        self.n += length
        while self.n >= 8:
            self.n -= 8
            byte = (self.acc >> self.n) & 255
            self.buf.append(byte)
            if byte == 255:
                self.buf.append(0)

    def flush(self) -> None:
        if self.n:
            self.put((1 << (8 - self.n)) - 1, 8 - self.n)


def _quant(table: tuple, quality: int) -> list:
    quality = max(1, min(100, int(quality)))
    scale = 5000 / quality if quality < 50 else 200 - quality * 2
    out = []
    for value in table:
        stepped = int((value * scale + 50) / 100)
        out.append(max(1, min(255, stepped)))
    return out


def _dct(block: list) -> list:
    tmp = [0.0] * 64
    for y in range(8):
        row = block[y * 8:(y + 1) * 8]
        for k in range(8):
            tmp[y * 8 + k] = 0.5 * _CK[k] * sum(row[n] * _COS[k][n] for n in range(8))
    out = [0.0] * 64
    for x in range(8):
        for k in range(8):
            out[k * 8 + x] = 0.5 * _CK[k] * sum(tmp[n * 8 + x] * _COS[k][n] for n in range(8))
    return out


def _amp(value: int) -> tuple:
    if value == 0:
        return 0, 0
    size = abs(value).bit_length()
    magnitude = value if value > 0 else (1 << size) + value - 1
    return size, magnitude


def _block(bits: _Bits, samples: list, quant: list, prev: int, dc_table: int) -> int:
    shifted = [sample - 128.0 for sample in samples]
    coeff = _dct(shifted)
    zz = [int(round(coeff[_ZZ[i]] / quant[i])) for i in range(64)]
    size, magnitude = _amp(zz[0] - prev)
    code, length = _HUFF[(dc_table, 0)][size]
    bits.put(code, length)
    if size:
        bits.put(magnitude, size)
    run = 0
    ac = _HUFF[(dc_table, 1)]
    for value in zz[1:]:
        if value == 0:
            run += 1
            continue
        while run > 15:
            code, length = ac[0xF0]
            bits.put(code, length)
            run -= 16
        size, magnitude = _amp(value)
        code, length = ac[(run << 4) | size]
        bits.put(code, length)
        bits.put(magnitude, size)
        run = 0
    if run:
        code, length = ac[0x00]
        bits.put(code, length)
    return zz[0]


def _marker(out: bytearray, code: bytes, payload: bytes = b"") -> None:
    out.extend(code)
    if payload:
        out.extend((len(payload) + 2).to_bytes(2, "big"))
        out.extend(payload)


def encode_jpeg(rgb: bytes, width: int, height: int, *, quality: int = 75) -> bytes:
    """Encode tightly packed RGB bytes to a baseline 4:4:4 JPEG."""
    if width < 1 or height < 1:
        raise ValueError("frame is empty")
    pad_w = (width + 7) & ~7
    pad_h = (height + 7) & ~7
    qy = [_quant(_QY, quality)[slot] for slot in _ZZ]
    qc = [_quant(_QC, quality)[slot] for slot in _ZZ]
    bits = _Bits()
    prev = [0, 0, 0]
    for by in range(0, pad_h, 8):
        for bx in range(0, pad_w, 8):
            planes = [[0.0] * 64 for _ in range(3)]
            for py in range(8):
                yy = min(by + py, height - 1)
                for px in range(8):
                    xx = min(bx + px, width - 1)
                    i = (yy * width + xx) * 3
                    r = rgb[i]
                    g = rgb[i + 1]
                    b = rgb[i + 2]
                    slot = py * 8 + px
                    planes[0][slot] = 0.299 * r + 0.587 * g + 0.114 * b
                    planes[1][slot] = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
                    planes[2][slot] = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
            for index, quant in enumerate((qy, qc, qc)):
                prev[index] = _block(bits, planes[index], quant, prev[index], 0 if index == 0 else 1)
    bits.flush()
    out = bytearray(b"\xff\xd8")
    _marker(out, b"\xff\xe0", b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
    _marker(out, b"\xff\xdb", bytes([0, *qy]))
    _marker(out, b"\xff\xdb", bytes([1, *qc]))
    sof = bytearray([8, pad_h >> 8, pad_h & 255, pad_w >> 8, pad_w & 255, 3])
    sof.extend((1, 0x11, 0, 2, 0x11, 1, 3, 0x11, 1))
    _marker(out, b"\xff\xc0", bytes(sof))
    for klass, ident, table_bits, table_vals in (
        (0, 0, _LDC_BITS, _LDC_VAL),
        (1, 0, _LAC_BITS, _LAC_VAL),
        (0, 1, _CDC_BITS, _CDC_VAL),
        (1, 1, _CAC_BITS, _CAC_VAL),
    ):
        payload = bytes([(klass << 4) | ident, *table_bits, *table_vals])
        _marker(out, b"\xff\xc4", payload)
    _marker(out, b"\xff\xda", bytes([3, 1, 0x00, 2, 0x11, 3, 0x11, 0, 63, 0]))
    out.extend(bits.buf)
    out.extend(b"\xff\xd9")
    return bytes(out)
