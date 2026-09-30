"""python test_photo_gps.py  (or pytest) — checks EXIF GPS extraction on synthetic JPEGs."""
import struct

from app.photo_gps import jpeg_gps


def make_jpeg(lat, lng, bo="<", with_gps=True):
    """Minimal JPEG: SOI + APP1(Exif: IFD0 -> GPS IFD with 4 tags) + SOS."""
    def dms(v):
        v = abs(v); d = int(v); m = int((v - d) * 60); s = round(((v - d) * 60 - m) * 60 * 1000)
        return [(d, 1), (m, 1), (s, 1000)]

    hdr = (b"II" if bo == "<" else b"MM") + struct.pack(bo + "HI", 42, 8)
    ifd0 = struct.pack(bo + "H", 1) + struct.pack(bo + "HHII", 0x8825, 4, 1, 26) + struct.pack(bo + "I", 0)
    gps_off = 8 + len(ifd0)  # = 26
    rat_off = gps_off + 2 + 4 * 12 + 4
    ref = lambda c: c.encode() + b"\0\0\0"
    gps = struct.pack(bo + "H", 4)
    gps += struct.pack(bo + "HHI", 1, 2, 2) + ref("N" if lat >= 0 else "S")
    gps += struct.pack(bo + "HHII", 2, 5, 3, rat_off)
    gps += struct.pack(bo + "HHI", 3, 2, 2) + ref("E" if lng >= 0 else "W")
    gps += struct.pack(bo + "HHII", 4, 5, 3, rat_off + 24)
    gps += struct.pack(bo + "I", 0)
    rats = b"".join(struct.pack(bo + "II", n, d) for n, d in dms(lat) + dms(lng))
    tiff = hdr + (ifd0 + gps + rats if with_gps else struct.pack(bo + "HI", 0, 0))
    app1 = b"Exif\x00\x00" + tiff
    return b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xda\x00\x02"


def test_photo_gps():
    for bo in "<>":
        lat, lng = jpeg_gps(make_jpeg(50.0862, 14.4140, bo))  # 까를교
        assert abs(lat - 50.0862) < 1e-4 and abs(lng - 14.4140) < 1e-4, (bo, lat, lng)
        lat, lng = jpeg_gps(make_jpeg(-33.8568, -151.2153, bo))  # southern/western hemisphere signs
        assert lat < 0 and lng < 0, (lat, lng)
    assert jpeg_gps(make_jpeg(0, 0, with_gps=False)) is None  # EXIF without GPS
    assert jpeg_gps(b"\x89PNG\r\n\x1a\n") is None  # not a JPEG
    assert jpeg_gps(b"") is None


if __name__ == "__main__":
    test_photo_gps()
    print("ok")
