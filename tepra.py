#!/usr/bin/env python3
"""TEPRA PRO (SR5900P / SR-R7900P) network printing without the official driver.

Unofficial; protocol ported from https://github.com/hikalium/sr5900p (MIT).
Usage: tepra.py IP status | tepra.py IP print TEXT [--dry-run]
"""
import os, socket, struct, sys, time
from PIL import Image, ImageDraw, ImageFont

PORT = 9100
FONT = os.environ.get("TEPRA_FONT", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
# status tape index -> (name, printable width mm). From SR5900P analysis; 50mm index unknown.
TAPES = {0x0B: ("4mm", 2.85), 0x01: ("6mm", 5.0), 0x02: ("9mm", 7.0), 0x03: ("12mm", 10.0),
         0x04: ("18mm", 15.2), 0x05: ("24mm", 20.0), 0x06: ("36mm", 26.0)}


def udp(sock, ip, cmd):
    sock.sendto(b"TPRT" + struct.pack(">7I", 0, 1, 0x20, cmd, 0, 0, 0), (ip, PORT))
    d, _ = sock.recvfrom(512)
    assert d[:4] == b"tprt", d
    return d[32:]


def status(sock, ip):
    # SR5900P returns 20 bytes, SR-R7900P 78; the leading fields match.
    p = udp(sock, ip, 1)
    return {"printing": p[1] == 2, "error": p[2], "tape": TAPES.get(p[3]), "raw": p}


def esc(*payload):
    return bytes([0x1B, 0x7B, len(payload) + 2, *payload, sum(payload) & 0xFF, 0x7D])


def render(text, width_px):
    font = ImageFont.truetype(FONT, int(width_px * 0.8))
    l, t, r, b = font.getbbox(text)
    margin = width_px // 2
    im = Image.new("1", (r - l + 2 * margin, width_px), 0)  # 1 = ink
    ImageDraw.Draw(im).text((margin - l, (width_px - (b - t)) // 2 - t), text, font=font, fill=1)
    return im


def job(im):
    w, h = im.size
    data = esc(0x40) + esc(0x7B, 0, 0, 0x53, 0x54) + esc(0x43, 2, 2, 1, 1) + esc(0x44, 5) + esc(0x47)
    data += esc(0x4C, *struct.pack("<I", w + 4))  # tape length + safe margin
    data += esc(0x54, 0x2A, 0) + esc(0x48, 5) + esc(0x73, 0)
    rows = im.transpose(Image.Transpose.ROTATE_90)  # row 0 = last column, MSB = top pixel
    stride = (h + 7) // 8
    raw = rows.tobytes()
    for i in range(w):
        data += b"\x1b\x2e\x00\x00\x00\x01" + struct.pack("<H", h) + raw[i * stride:(i + 1) * stride]
    return data + b"\x0c" + esc(0x40)


def main():
    ip, cmd = sys.argv[1], sys.argv[2]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    st = status(sock, ip)
    print("status:", {k: v for k, v in st.items() if k != "raw"})
    if cmd == "status":
        return
    if st["printing"] or st["error"] or not st["tape"]:
        sys.exit(f"printer not ready: raw={list(st['raw'][:20])}")
    mm = st["tape"][1]
    px = (int(mm * 360 / 25.4) + 7) // 8 * 8
    im = render(sys.argv[3], px)
    im.convert("L").point(lambda v: 255 - v).save("preview.png")
    print(f"preview.png {im.size[0]}x{px}px ({im.size[0] * 25.4 / 360:.1f}mm long)")
    if "--dry-run" in sys.argv:
        return
    payload = job(im)
    assert udp(sock, ip, 2) == b"\x02\x00\x00", "start rejected"
    try:
        time.sleep(0.5)
        with socket.create_connection((ip, PORT), timeout=10) as tcp:
            time.sleep(0.5)
            udp(sock, ip, 0x0101)
            r = udp(sock, ip, 0x0100)
            # SR5900P: 0x10 (sometimes 0x00), SR-R7900P: 0x18
            assert len(r) == 1 and (r[0] & 0x10 or r[0] == 0), f"notify rejected: {r!r}"
            time.sleep(0.5)
            tcp.sendall(payload)
            while time.sleep(0.5) or status(sock, ip)["printing"]:
                pass
    finally:
        print("stop:", list(udp(sock, ip, 3)))


if __name__ == "__main__":
    main()
