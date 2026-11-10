#!/usr/bin/env python3
"""
make.fun "cutest-dog-01" entry.

Procedurally draws the cutest puppy we can manage in code and writes it to
/output/entry.png (override with ENTRY_OUT for local runs).

Pure Python 3 standard library (math / os / struct / zlib only):
no network, no files read, no fonts, no randomness -- the same bytes come
out on every run. Shapes are painted with signed-distance-field coverage,
which gives anti-aliased edges and soft shading without any image library.
"""

import math
import os
import struct
import zlib
from array import array

W = H = 1024
N = W * H

# Float RGB planes.
R = array("f", bytes(4 * N))
G = array("f", bytes(4 * N))
B = array("f", bytes(4 * N))


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def blend(i, col, a):
    ia = 1.0 - a
    R[i] = R[i] * ia + col[0] * a
    G[i] = G[i] * ia + col[1] * a
    B[i] = B[i] * ia + col[2] * a


# ---------------------------------------------------------------- shapes

def ellipse(cx, cy, rx, ry, rot, col, alpha=1.0, soft=2.0, fade=None):
    """Filled rotated ellipse with SDF anti-aliased edge.

    fade, if given, maps the normalised radius t (0 centre .. 1 edge) to an
    alpha multiplier -- used for blush, halos and other soft glows.
    """
    cr = math.cos(rot)
    sr = math.sin(rot)
    # Rotated bounding box half-extents.
    bx = math.sqrt((rx * cr) ** 2 + (ry * sr) ** 2) + soft + 2
    by = math.sqrt((rx * sr) ** 2 + (ry * cr) ** 2) + soft + 2
    x0 = max(0, int(cx - bx)); x1 = min(W - 1, int(cx + bx))
    y0 = max(0, int(cy - by)); y1 = min(H - 1, int(cy + by))
    minr = min(rx, ry)
    for y in range(y0, y1 + 1):
        dy = y - cy
        base = y * W
        for x in range(x0, x1 + 1):
            dx = x - cx
            # Rotate into the ellipse frame.
            px = dx * cr + dy * sr
            py = -dx * sr + dy * cr
            qx = px / rx
            qy = py / ry
            q = qx * qx + qy * qy
            if q > 4.0:
                continue
            t = math.sqrt(q)
            d = (t - 1.0) * minr  # approx signed distance in px
            cov = clamp(0.5 - d / soft)
            if cov <= 0.0:
                continue
            a = alpha * cov
            if fade is not None:
                a *= clamp(fade(t))
            if a > 0.003:
                blend(base + x, col, a)


def circle(cx, cy, r, col, alpha=1.0, soft=2.0, fade=None):
    ellipse(cx, cy, r, r, 0.0, col, alpha, soft, fade)


def stamp(cx, cy, r, col, alpha, soft):
    circle(cx, cy, r, col, alpha, soft)


def stroke(points, width, col, alpha=1.0, soft=2.0):
    """Draw a smooth polyline by stamping soft discs along it."""
    r = width / 2.0
    for k in range(len(points) - 1):
        x1, y1 = points[k]
        x2, y2 = points[k + 1]
        steps = max(1, int(math.hypot(x2 - x1, y2 - y1) / (r * 0.45)))
        for s in range(steps + 1):
            t = s / steps
            stamp(lerp(x1, x2, t), lerp(y1, y2, t), r, col, alpha, soft)


def arc(cx, cy, rx, ry, a0, a1, width, col, alpha=1.0, soft=2.0, n=48):
    pts = []
    for k in range(n + 1):
        a = lerp(a0, a1, k / n)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    stroke(pts, width, col, alpha, soft)


def heart(cx, cy, s, col, alpha=1.0, rot=0.0):
    """A little heart: two lobes + a rotated square point."""
    # Lobes.
    off = 0.40 * s
    for sgn in (-1, 1):
        lx = cx + sgn * off * math.cos(rot)
        ly = cy + sgn * off * math.sin(rot) - 0.14 * s
        circle(lx, ly, 0.46 * s, col, alpha, 2.0)
    # Point: a diamond whose tip reaches well below the lobes.
    ellipse(cx, cy + 0.34 * s, 0.66 * s, 0.66 * s, math.pi / 4 + rot, col, alpha, 2.0)


# ---------------------------------------------------------------- palette

CREAM_BG_HI = (1.00, 0.965, 0.905)
CREAM_BG_LO = (1.00, 0.835, 0.655)
HALO = (1.00, 0.995, 0.965)
DOT_PINK = (1.00, 0.72, 0.78)
DOT_GOLD = (1.00, 0.80, 0.55)
SHADOW = (0.72, 0.47, 0.22)

FUR = (0.937, 0.663, 0.345)        # warm golden
FUR_LIGHT = (0.965, 0.745, 0.435)
FUR_DARK = (0.78, 0.50, 0.235)
EAR = (0.72, 0.435, 0.20)          # darker floppy ears
EAR_INNER = (0.85, 0.58, 0.33)
CREAM = (1.00, 0.945, 0.855)       # muzzle / chest / paws
DARK = (0.185, 0.105, 0.06)        # eyes / outline brown
NOSE = (0.26, 0.15, 0.115)
MOUTH = (0.42, 0.20, 0.14)
TONGUE = (0.965, 0.51, 0.62)
TONGUE_LINE = (0.85, 0.36, 0.47)
BLUSH = (1.00, 0.58, 0.58)
BOW = (0.90, 0.27, 0.30)
BOW_DARK = (0.76, 0.19, 0.23)
WHITE = (1.00, 1.00, 1.00)


# ---------------------------------------------------------------- scene

def background():
    cx, cy = 512.0, 400.0
    for y in range(H):
        base = y * W
        vt = y / (H - 1)
        for x in range(W):
            dx = (x - cx) / 760.0
            dy = (y - cy) / 760.0
            d = math.sqrt(dx * dx + dy * dy)
            glow = clamp(1.0 - d, 0.0, 1.0) ** 1.5
            col = mix(CREAM_BG_LO, CREAM_BG_HI, 0.25 + 0.75 * glow)
            # Gentle top-to-bottom warmth shift.
            col = mix(col, CREAM_BG_LO, vt * 0.18)
            i = base + x
            R[i], G[i], B[i] = col


def decorations():
    # Halo sun behind the puppy.
    circle(512, 415, 345, HALO, 0.85, 90.0, fade=lambda t: 1.0 - 0.55 * t)
    # Soft polka dots.
    dots = [
        (120, 180, 17, DOT_PINK, 0.50), (215, 95, 11, DOT_GOLD, 0.55),
        (905, 150, 15, DOT_PINK, 0.50), (825, 80, 10, DOT_GOLD, 0.55),
        (90, 420, 12, DOT_GOLD, 0.45), (945, 430, 13, DOT_GOLD, 0.45),
        (150, 640, 10, DOT_PINK, 0.45), (880, 660, 11, DOT_PINK, 0.45),
        (300, 60, 9, DOT_PINK, 0.5), (720, 55, 12, DOT_GOLD, 0.5),
        (60, 830, 13, DOT_GOLD, 0.4), (960, 845, 12, DOT_PINK, 0.4),
    ]
    for (x, y, r, c, a) in dots:
        circle(x, y, r, c, a, 6.0, fade=lambda t: 1.0 - 0.35 * t)
    # Sparkles (four-point stars as plus strokes).
    for (x, y, s, a) in [(255, 300, 20, 0.65), (775, 265, 16, 0.6), (150, 520, 14, 0.55)]:
        stroke([(x - s, y), (x + s, y)], 7, WHITE, a, 3.0)
        stroke([(x, y - s), (x, y + s)], 7, WHITE, a, 3.0)
        circle(x, y, 4.5, WHITE, a, 2.0)


def puppy():
    # Ground shadow.
    ellipse(512, 918, 330, 52, 0.0, SHADOW, 0.32, 46.0, fade=lambda t: 1.0 - 0.4 * t)

    # Tail peeking out on the right, cream tip.
    ellipse(770, 845, 105, 42, -0.5, FUR_DARK, 1.0, 3.0)
    ellipse(838, 812, 42, 26, -0.5, CREAM, 1.0, 3.0)

    # Body.
    ellipse(512, 800, 218, 172, 0.0, FUR, 1.0, 2.5)
    ellipse(512, 812, 128, 128, 0.0, CREAM, 1.0, 2.5)          # chest
    ellipse(512, 700, 190, 90, 0.0, FUR_LIGHT, 0.25, 40.0,
            fade=lambda t: 1.0 - t)                              # body sheen

    # Hind paws.
    for sgn in (-1, 1):
        px = 512 + sgn * 185
        ellipse(px, 908, 82, 42, 0.0, FUR_LIGHT, 1.0, 2.5)
        ellipse(px, 912, 62, 30, 0.0, CREAM, 0.85, 2.5)
    # Front paws.
    for sgn in (-1, 1):
        px = 512 + sgn * 82
        ellipse(px, 922, 47, 29, 0.0, CREAM, 1.0, 2.5)
        for toe in (-1, 1):
            stroke([(px + toe * 13, 908), (px + toe * 13, 922)], 5,
                   FUR_DARK, 0.45, 1.5)

    # Neck shadow so the head sits on the body.
    ellipse(512, 648, 175, 42, 0.0, SHADOW, 0.16, 26.0, fade=lambda t: 1.0 - t)

    # ---- head ----
    ellipse(512, 418, 268, 244, 0.0, FUR, 1.0, 2.5)
    # Forehead / crown light.
    ellipse(455, 265, 150, 105, -0.25, FUR_LIGHT, 0.35, 55.0,
            fade=lambda t: 1.0 - t)
    # Faint cream blaze up the forehead.
    ellipse(512, 372, 52, 128, 0.0, CREAM, 0.30, 34.0, fade=lambda t: 1.0 - t)
    # Little cowlick curls on top.
    arc(500, 196, 26, 18, 1.05 * math.pi, 2.05 * math.pi, 9, FUR_DARK, 0.65)
    arc(528, 190, 16, 12, 1.0 * math.pi, 2.0 * math.pi, 8, FUR_DARK, 0.55)

    # ---- floppy ears: tucked in at the top, hanging down the cheeks ----
    for sgn in (-1, 1):
        ex = 512 + sgn * 240
        rot = -sgn * 0.38
        ellipse(ex, 420, 72, 185, rot, EAR, 1.0, 2.5)
        ellipse(ex + sgn * 8, 442, 40, 132, rot, EAR_INNER, 0.8, 3.0)
        # Darker ear tip (bottom-outward end of the ear).
        tx = ex + 165 * 0.37 * sgn
        ellipse(tx, 420 + 158, 46, 58, rot, EAR, 0.35, 30.0,
                fade=lambda t: 1.0 - t)

    # Collar with a gold tag, hugging the bottom of the head (ears and
    # muzzle overlap it, the tongue will stick out over it).
    arc(512, 418, 238, 216, 0.18 * math.pi, 0.82 * math.pi, 27,
        (0.22, 0.58, 0.56), 1.0, 2.5)
    arc(512, 418, 238, 216, 0.18 * math.pi, 0.82 * math.pi, 27,
        (0.16, 0.46, 0.45), 0.35, 2.5)
    circle(512, 662, 15, (0.98, 0.78, 0.30), 1.0, 2.0)
    circle(507, 657, 5, WHITE, 0.65, 1.5)

    # ---- muzzle ----
    ellipse(512, 522, 152, 106, 0.0, CREAM, 1.0, 2.5)
    ellipse(512, 470, 120, 70, 0.0, CREAM, 0.55, 30.0, fade=lambda t: 1.0 - t)

    # Blush.
    for sgn in (-1, 1):
        ellipse(512 + sgn * 160, 556, 58, 30, 0.0, BLUSH, 0.5, 26.0,
                fade=lambda t: 1.0 - t * t)

    # Tongue (drawn before the mouth line so the line overlaps its top).
    ellipse(512, 596, 27, 40, 0.0, TONGUE, 1.0, 2.5)
    ellipse(503, 578, 10, 18, 0.0, (1.0, 0.66, 0.74), 0.7, 8.0,
            fade=lambda t: 1.0 - t)
    stroke([(512, 578), (512, 616)], 5, TONGUE_LINE, 0.8, 1.5)

    # Mouth: two happy arcs (the classic w smile), plus philtrum.
    stroke([(512, 532), (512, 552)], 8, MOUTH, 0.9, 2.0)
    arc(478, 540, 36, 26, 0.15 * math.pi, 0.95 * math.pi, 9, MOUTH, 0.9)
    arc(546, 540, 36, 26, 0.05 * math.pi, 0.85 * math.pi, 9, MOUTH, 0.9)

    # Nose with a soft highlight.
    ellipse(512, 508, 35, 25, 0.0, NOSE, 1.0, 2.0)
    ellipse(500, 499, 11, 6, -0.3, WHITE, 0.55, 3.0, fade=lambda t: 1.0 - t)

    # Whisker dots.
    for sgn in (-1, 1):
        for (ox, oy) in [(58, 8), (84, 22), (48, 30)]:
            circle(512 + sgn * ox, 512 + oy, 3.2, FUR_DARK, 0.35, 1.2)

    # ---- eyes: big, dark, sparkling ----
    for sgn in (-1, 1):
        ex = 512 + sgn * 98
        ey = 428
        ellipse(ex, ey, 41, 54, 0.0, DARK, 1.0, 2.0)
        # Iris warmth at the bottom of the eye.
        ellipse(ex, ey + 26, 30, 24, 0.0, (0.36, 0.20, 0.09), 0.65, 12.0,
                fade=lambda t: 1.0 - t)
        # Highlights: one big, one small.
        circle(ex - 13, ey - 19, 14.5, WHITE, 0.98, 2.0)
        circle(ex + 11, ey + 13, 6.5, WHITE, 0.9, 1.5)
        # Upper lash line.
        arc(ex, ey - 6, 44, 52, 1.15 * math.pi, 1.85 * math.pi, 10, DARK, 0.85)

    # Eyebrows: small, raised, a little wistful -- peak cute.
    for sgn in (-1, 1):
        ex = 512 + sgn * 100
        arc(ex, 352, 34, 20, 1.08 * math.pi, 1.92 * math.pi, 11, FUR_DARK, 0.8)

    # ---- bow where the right ear tucks into the head ----
    bx, by = 700, 216
    ellipse(bx - 34, by, 36, 24, 0.55, BOW, 1.0, 2.0)
    ellipse(bx + 34, by, 36, 24, -0.55, BOW, 1.0, 2.0)
    ellipse(bx - 36, by + 4, 26, 15, 0.55, BOW_DARK, 0.5, 8.0,
            fade=lambda t: 1.0 - t)
    ellipse(bx + 36, by + 4, 26, 15, -0.55, BOW_DARK, 0.5, 8.0,
            fade=lambda t: 1.0 - t)
    circle(bx, by, 15, BOW_DARK, 1.0, 2.0)
    circle(bx - 4, by - 4, 5, WHITE, 0.5, 1.5)

    # Floating hearts.
    heart(168, 268, 30, DOT_PINK, 0.9, -0.15)
    heart(862, 330, 24, DOT_PINK, 0.85, 0.2)
    heart(196, 760, 20, DOT_GOLD, 0.8, 0.1)


# ---------------------------------------------------------------- png out

def write_png(path):
    raw = bytearray()
    for y in range(H):
        base = y * W
        row = bytearray(3 * W)
        for x in range(W):
            i = base + x
            o = 3 * x
            row[o] = int(clamp(R[i]) * 255.0 + 0.5)
            row[o + 1] = int(clamp(G[i]) * 255.0 + 0.5)
            row[o + 2] = int(clamp(B[i]) * 255.0 + 0.5)
        # Sub filter (uses original left neighbour, so walk right-to-left).
        for i in range(len(row) - 1, 2, -1):
            row[i] = (row[i] - row[i - 3]) & 0xFF
        raw.append(1)
        raw += row
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    background()
    decorations()
    puppy()
    out = os.environ.get("ENTRY_OUT", "/output/entry.png")
    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    size = write_png(out)
    print(f"wrote {out} ({size} bytes)")


if __name__ == "__main__":
    main()
