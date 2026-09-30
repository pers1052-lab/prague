"""Read the GPS position from a JPEG's EXIF block (stdlib only, no Pillow)."""
import struct


def jpeg_gps(data: bytes):
    """Return (lat, lng) from a JPEG's EXIF GPS tags, or None if absent/unreadable."""
    try:
        tiff = _jpeg_exif(data)
        return _tiff_gps(tiff) if tiff else None
    except (struct.error, IndexError, ValueError, ZeroDivisionError):
        return None


def _jpeg_exif(data):
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 4 <= len(data) and data[i] == 0xFF:
        marker = data[i + 1]
        if marker == 0xDA:  # start of scan: no more metadata
            return None
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        seg = data[i + 4:i + 2 + length]
        if marker == 0xE1 and seg[:6] == b"Exif\x00\x00":
            return seg[6:]
        i += 2 + length
    return None


def _tiff_gps(t):
    bo = {b"II": "<", b"MM": ">"}[t[:2]]
    u16 = lambda o: struct.unpack(bo + "H", t[o:o + 2])[0]
    u32 = lambda o: struct.unpack(bo + "I", t[o:o + 4])[0]

    def entries(ifd):
        for k in range(u16(ifd)):
            e = ifd + 2 + 12 * k
            yield u16(e), e  # tag, entry offset

    gps_ifd = next((u32(e + 8) for tag, e in entries(u32(4)) if tag == 0x8825), None)
    if gps_ifd is None:
        return None

    vals = {}
    for tag, e in entries(gps_ifd):
        if tag in (1, 3):  # N/S, E/W reference: ASCII stored inline
            vals[tag] = chr(t[e + 8])
        elif tag in (2, 4):  # degrees, minutes, seconds as 3 RATIONALs
            off = u32(e + 8)
            d, m, s = (u32(off + 8 * j) / u32(off + 8 * j + 4) for j in range(3))
            vals[tag] = d + m / 60 + s / 3600
    if not all(k in vals for k in (1, 2, 3, 4)):
        return None

    lat = vals[2] * (-1 if vals[1] == "S" else 1)
    lng = vals[4] * (-1 if vals[3] == "W" else 1)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0):
        return None
    return round(lat, 6), round(lng, 6)
