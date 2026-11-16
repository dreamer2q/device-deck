"""Small Annex-B SPS reader; dimensions include the encoder's crop rectangle."""
from __future__ import annotations


def nal_units(data: bytes):
    import re
    markers = list(re.finditer(b"\x00\x00(?:\x00)?\x01", data))
    for i, marker in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(data)
        if marker.end() < end:
            yield data[marker.end():end]


class Bits:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def read(self, n=1):
        if self.pos + n > len(self.data) * 8:
            raise ValueError("truncated SPS")
        value = 0
        for _ in range(n):
            value = value * 2 + ((self.data[self.pos // 8] >> (7 - self.pos % 8)) & 1)
            self.pos += 1
        return value

    def ue(self):
        zeros = 0
        while self.read() == 0:
            zeros += 1
            if zeros > 31:
                raise ValueError("invalid SPS code")
        return (1 << zeros) - 1 + self.read(zeros)

    def se(self):
        n = self.ue()
        return (n + 1) // 2 if n & 1 else -n // 2


def sps_info(data: bytes):
    """Return (codec, width, height) or None for a packet without an SPS."""
    for nal in nal_units(data):
        if nal[0] & 31 != 7:
            continue
        import re
        rbsp = re.sub(b"\x00\x00\x03", b"\x00\x00", nal[1:])
        b = Bits(rbsp)
        profile = b.read(8)
        b.read(16)
        b.ue()
        chroma = 1
        if profile in {100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135}:
            chroma = b.ue()
            if chroma > 3:
                raise ValueError("invalid chroma format")
            if chroma == 3 and b.read():
                chroma = 0  # separate_colour_plane_flag
            b.ue(); b.ue(); b.read()
            if b.read():
                for i in range(8 if chroma != 3 else 12):
                    if b.read():
                        last = nxt = 8
                        for _ in range(16 if i < 6 else 64):
                            if nxt:
                                nxt = (last + b.se() + 256) % 256
                            last = nxt or last
        b.ue()
        order = b.ue()
        if order == 0:
            b.ue()
        elif order == 1:
            b.read(); b.se(); b.se()
            cycle = b.ue()
            if cycle > 256:
                raise ValueError("invalid SPS cycle")
            for _ in range(cycle):
                b.se()
        b.ue(); b.read()
        width = (b.ue() + 1) * 16
        height_units = b.ue() + 1
        frame = b.read()
        if not frame:
            b.read()
        b.read()
        left = right = top = bottom = 0
        if b.read():
            left, right, top, bottom = (b.ue() for _ in range(4))
        sx = 2 if chroma in (1, 2) else 1
        sy = (2 if chroma == 1 else 1) * (2 - frame)
        width -= (left + right) * sx
        height = height_units * 16 * (2 - frame) - (top + bottom) * sy
        if not (0 < width <= 16384 and 0 < height <= 16384):
            raise ValueError("invalid SPS dimensions")
        return "avc1." + nal[1:4].hex(), width, height
    return None
