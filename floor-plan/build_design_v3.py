#!/usr/bin/env python3
"""Colour furnished design layout of replanning variant 3 (sheet 5), still at exactly 1:50.

Same walls, doors, dimensions and room areas as build_replan_v3.py (sheet 4); adds floor
finishes, coloured furniture and decor. Outputs:
    output/design-v3_1-50_A3.pdf, output/design-v3_1-50_A3.png, output/design-v3_1-50.dxf
"""

import math
import os

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from shapely.geometry import LineString, box
from shapely.ops import unary_union

import build_plan as bp
import build_replan as br
import build_replan_v3 as v3
from build_plan import DIMS, LAYERS, M, P, CAP, SCALE, X_FAC, X_PART, Y_FAC, Y_LG, Y_LK

OUT = bp.OUT
KEEP = {"A-GLAZ", "A-GLAZ-FRAME", "A-DOOR", "A-DOOR-SWING", "A-SHAFT", "A-COLS"}
kept_items = [it for it in M.items if it[1] in KEEP]
M.items.clear()
P.items.clear()

for name in ("I-FLOOR", "I-FLOOR-PAT", "I-RUG", "I-FURN", "I-FIXT", "I-PLANT", "I-LABEL"):
    LAYERS[name] = ((0.35, 0.35, 0.35), 0.13)

# ---------------------------------------------------------------------------------------
# palette
# ---------------------------------------------------------------------------------------
OAK = (0.87, 0.75, 0.58)
OAK_LINE = (0.76, 0.62, 0.45)
STONE = (0.88, 0.87, 0.84)
STONE_LINE = (0.76, 0.75, 0.72)
TILE = (0.83, 0.88, 0.91)
TILE_LINE = (0.70, 0.77, 0.81)
CARPET = (0.27, 0.28, 0.34)
CARPET_LINE = (0.33, 0.34, 0.41)
DECK = (0.72, 0.56, 0.40)
DECK_LINE = (0.58, 0.43, 0.30)
WALNUT = (0.47, 0.34, 0.25)
WOOD = (0.66, 0.50, 0.35)
WHITE = (1.0, 1.0, 1.0)
LINEN = (0.95, 0.93, 0.89)
CHAR = (0.20, 0.21, 0.23)
STEEL = (0.78, 0.80, 0.83)
EDGE = (0.30, 0.30, 0.32)
PINK = (0.95, 0.73, 0.79)
BLUE = (0.60, 0.75, 0.92)
TEAL = (0.36, 0.52, 0.58)
MUSTARD = (0.88, 0.67, 0.28)
BURGUNDY = (0.55, 0.14, 0.19)
GREEN = (0.36, 0.60, 0.36)
GREEN_D = (0.22, 0.44, 0.24)
SAND = (0.84, 0.77, 0.66)
GLOW = (0.35, 0.65, 0.98)


# ---------------------------------------------------------------------------------------
# drawing helpers (all in model mm, working frame y down)
# ---------------------------------------------------------------------------------------
def rect(x0, y0, x1, y1, fill, stroke=EDGE, lw=0.13, layer="I-FURN"):
    M.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, fill=fill, color=stroke, lw=lw)


def rpts(x0, y0, x1, y1, rad):
    rad = min(rad, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = []
    for cx, cy, a in ((x1 - rad, y0 + rad, -90), (x1 - rad, y1 - rad, 0),
                      (x0 + rad, y1 - rad, 90), (x0 + rad, y0 + rad, 180)):
        for k in range(7):
            t = math.radians(a + 15 * k)
            pts.append((cx + rad * math.cos(t), cy + rad * math.sin(t)))
    return pts


def rrect(x0, y0, x1, y1, rad, fill, stroke=EDGE, lw=0.13, layer="I-FURN"):
    M.poly(rpts(x0, y0, x1, y1, rad), layer, fill=fill, color=stroke, lw=lw)


def circle(c, rad, fill, stroke=EDGE, lw=0.13, layer="I-FURN"):
    M.circle(c, rad, layer, fill=fill, color=stroke, lw=lw)


def ellipse(cx, cy, rx, ry, fill, stroke=EDGE, lw=0.13, layer="I-FIXT"):
    M.poly([(cx + rx * math.cos(2 * math.pi * k / 48), cy + ry * math.sin(2 * math.pi * k / 48))
            for k in range(48)], layer, fill=fill, color=stroke, lw=lw)


def line(a, b, color=EDGE, lw=0.13, layer="I-FURN"):
    M.line(a, b, layer, color=color, lw=lw)


def segs(g):
    if g.is_empty:
        return []
    if g.geom_type == "LineString":
        return [list(g.coords)]
    return [list(p.coords) for p in getattr(g, "geoms", []) if p.geom_type == "LineString"]


def floor(poly, fill, pat_color, kind, s=180, joint=1200):
    """Floor finish: kind 'plank-x', 'plank-y', 'tile' (s = tile size) or 'plain'."""
    M.region(poly, "I-FLOOR", fill=fill)
    x0, y0, x1, y1 = poly.bounds
    lines = []
    if kind in ("plank-x", "tile"):
        k, y = 0, y0 + s
        while y < y1:
            lines.append(LineString([(x0 - 10, y), (x1 + 10, y)]))
            if kind == "plank-x":
                off = (k % 3) * joint / 3
                x = x0 + off
                while x < x1:
                    lines.append(LineString([(x, y - s), (x, y)]))
                    x += joint
            y += s
            k += 1
    if kind in ("plank-y", "tile"):
        k, x = 0, x0 + s
        while x < x1:
            lines.append(LineString([(x, y0 - 10), (x, y1 + 10)]))
            if kind == "plank-y":
                off = (k % 3) * joint / 3
                y = y0 + off
                while y < y1:
                    lines.append(LineString([(x - s, y), (x, y)]))
                    y += joint
            x += s
            k += 1
    for ln in lines:
        for sg in segs(ln.intersection(poly)):
            M.line(sg[0], sg[-1], "I-FLOOR-PAT", color=pat_color, lw=0.08)


def plant(c, rad):
    circle(c, rad, GREEN, GREEN_D, 0.13, "I-PLANT")
    for k in range(7):
        t = math.radians(360 / 7 * k + 10)
        ellipse(c[0] + rad * 0.45 * math.cos(t), c[1] + rad * 0.45 * math.sin(t),
                rad * 0.42, rad * 0.22, (0.45, 0.70, 0.42), GREEN_D, 0.08, "I-PLANT")
    circle(c, rad * 0.18, (0.55, 0.38, 0.25), GREEN_D, 0.08, "I-PLANT")


def pillow(x0, y0, x1, y1):
    rrect(x0, y0, x1, y1, 70, WHITE, (0.6, 0.6, 0.62), 0.1)


def bed(x0, y0, x1, y1, head, duvet, throw=None, pillows=2, board=WALNUT):
    """Bed with frame, mattress, duvet (from 600 mm below the head), throw and pillows."""
    rrect(x0, y0, x1, y1, 50, board)
    L = x1 - x0
    s = 1 if head == "left" else -1
    hx = x0 if head == "left" else x1

    def span(a, b):                       # distances a..b from the head -> x range
        return sorted((hx + s * a, hx + s * b))

    mx0, mx1 = span(90, L - 30)
    rrect(mx0, y0 + 30, mx1, y1 - 30, 60, WHITE, (0.7, 0.7, 0.7), 0.1)
    dx0, dx1 = span(600, L - 30)
    rrect(dx0, y0 + 20, dx1, y1 - 20, 60, duvet, (0.5, 0.5, 0.55), 0.1)
    if throw:
        tx0, tx1 = span(L - 480, L - 60)
        rect(tx0, y0 + 10, tx1, y1 - 10, throw, (0.4, 0.4, 0.45), 0.1)
    w = y1 - y0
    for k in range(pillows):
        py0 = y0 + 60 + k * (w - 120) / pillows
        px0, px1 = span(130, 520)
        pillow(px0, py0, px1, py0 + (w - 120) / pillows - 40)


def chair_top(cx, cy, facing, fill, back=CHAR):
    rrect(cx - 220, cy - 220, cx + 220, cy + 220, 80, fill)
    if facing == "down":
        rrect(cx - 220, cy - 220, cx + 220, cy - 140, 40, back)
    elif facing == "up":
        rrect(cx - 220, cy + 140, cx + 220, cy + 220, 40, back)
    elif facing == "right":
        rrect(cx - 220, cy - 220, cx - 140, cy + 220, 40, back)
    else:
        rrect(cx + 140, cy - 220, cx + 220, cy + 220, 40, back)


def office_chair(cx, cy, facing, fill=CHAR):
    circle((cx, cy), 260, fill)
    dx, dy = {"up": (0, 1), "down": (0, -1), "left": (1, 0), "right": (-1, 0)}[facing]
    rrect(cx + dx * 200 - (230 if dx == 0 else 60), cy + dy * 200 - (230 if dy == 0 else 60),
          cx + dx * 200 + (230 if dx == 0 else 60), cy + dy * 200 + (230 if dy == 0 else 60), 40, CHAR)


def lamp(c, rad=110):
    circle(c, rad, (1.0, 0.90, 0.60), (0.75, 0.62, 0.30), 0.1)
    circle(c, rad * 0.35, (1.0, 0.97, 0.85), (0.75, 0.62, 0.30), 0.08)


def books(x0, y0, x1, y1, vertical=True):
    cols = [(0.80, 0.30, 0.28), (0.25, 0.45, 0.70), (0.90, 0.72, 0.30), (0.35, 0.60, 0.45),
            (0.55, 0.40, 0.65), (0.85, 0.55, 0.35)]
    k = 0
    if vertical:
        y = y0 + 20
        while y < y1 - 60:
            h = 60 + (k * 37) % 50
            rect(x0 + 20, y, x1 - 20 - (k % 3) * 25, min(y + h, y1 - 20), cols[k % 6], (0.3, 0.3, 0.3), 0.05)
            y += h + 8
            k += 1
    else:
        x = x0 + 20
        while x < x1 - 60:
            w = 60 + (k * 37) % 50
            rect(x, y0 + 20, min(x + w, x1 - 20), y1 - 20 - (k % 3) * 25, cols[k % 6], (0.3, 0.3, 0.3), 0.05)
            x += w + 8
            k += 1


# ---------------------------------------------------------------------------------------
# 1. floors
# ---------------------------------------------------------------------------------------
RP = v3.RP
floor(RP["1"], STONE, STONE_LINE, "tile", 600)
floor(RP["2"], OAK, OAK_LINE, "plank-y", 180)
floor(RP["3"], TILE, TILE_LINE, "tile", 300)
floor(RP["4"], OAK, OAK_LINE, "plank-x", 180)
floor(RP["5"], STONE, STONE_LINE, "tile", 600)
floor(RP["6"], CARPET, CARPET_LINE, "tile", 500)
floor(RP["7"], OAK, OAK_LINE, "plank-y", 180)
floor(RP["7.1"], TILE, TILE_LINE, "tile", 300)
floor(RP["7.2"], OAK, OAK_LINE, "plank-y", 180)
floor(RP["8"], DECK, DECK_LINE, "plank-y", 140, 1500)
# door thresholds / openings between finishes: fill wall openings with the neighbouring floor
open_fill = unary_union(v3.openings[1:7]).difference(unary_union(v3.columns))
M.region(open_fill, "I-FLOOR", fill=OAK)

# ---------------------------------------------------------------------------------------
# 2. rugs
# ---------------------------------------------------------------------------------------
circle((2350, 1650), 600, (0.98, 0.84, 0.88), (0.85, 0.60, 0.68), 0.13, "I-RUG")
circle((2350, 1650), 470, None, (0.90, 0.70, 0.76), 0.1, "I-RUG")
circle((4650, 1900), 560, (0.78, 0.87, 0.97), (0.50, 0.66, 0.85), 0.13, "I-RUG")
circle((4650, 1900), 430, None, (0.60, 0.75, 0.90), 0.1, "I-RUG")
rrect(1000, 7550, 2350, 8950, 60, SAND, (0.66, 0.58, 0.46), 0.13, "I-RUG")
rrect(1080, 7630, 2270, 8870, 40, None, (0.72, 0.64, 0.52), 0.1, "I-RUG")
rect(3650, 8850, 5700, 11600, (0.80, 0.80, 0.78), (0.62, 0.62, 0.60), 0.13, "I-RUG")
rrect(350, 10950, 2550, 12500, 60, (0.40, 0.18, 0.22), (0.30, 0.10, 0.14), 0.13, "I-RUG")
rect(-3850, 450, -3350, 1150, (0.55, 0.55, 0.57), (0.4, 0.4, 0.42), 0.1, "I-RUG")       # door mat

# ---------------------------------------------------------------------------------------
# 3. furniture & fixtures
# ---------------------------------------------------------------------------------------
# hall
rect(-2900, 0, -1700, 380, WALNUT)                                  # shoe bench
rrect(-2850, 60, -1750, 330, 60, (0.80, 0.72, 0.60), (0.5, 0.45, 0.4), 0.1)
rect(-3880, 1500, -3820, 1950, (0.85, 0.90, 0.95), (0.5, 0.55, 0.6), 0.1)   # mirror
plant((-1300, 400), 260)

# bathroom (existing layout)
tray = box(-2100, 2200, -300, 2990).intersection(v3.RP["3"].buffer(-10))
M.region(tray, "I-FIXT", fill=(0.92, 0.94, 0.96))
circle((-1350, 2600), 45, STEEL, EDGE, 0.1, "I-FIXT")
rect(-1600, 4450, -1200, 4650, WHITE, EDGE, 0.13, "I-FIXT")
ellipse(-1400, 4230, 180, 260, WHITE)
ellipse(-1400, 4250, 120, 190, (0.93, 0.96, 0.98))
rect(-1000, 4170, -350, 4650, WALNUT, EDGE, 0.13, "I-FIXT")
ellipse(-675, 4420, 230, 160, WHITE)
circle((-675, 4600), 30, STEEL, EDGE, 0.08, "I-FIXT")
rect(-2090, 2480, -2040, 2620, STEEL, EDGE, 0.08, "I-FIXT")
plant((-450, 4050), 150)

# children's room: daughter (west) / son (east)
bed(1400, 40, 3400, 930, "left", PINK, throw=(0.98, 0.88, 0.60), pillows=1, board=(0.93, 0.90, 0.86))
bed(3900, 280, 5700, 1180, "right", BLUE, throw=(0.98, 0.80, 0.45), pillows=1, board=(0.93, 0.90, 0.86))
rect(3550, 0, 3750, 1900, (0.93, 0.90, 0.86))                       # shelving divider
for yb in range(0, 1900, 300):
    books(3550, yb, 3750, yb + 300, vertical=True)
rect(2300, 2400, 3500, 3000, WHITE)                                 # desk 1
rect(2400, 2850, 3400, 2920, (0.4, 0.4, 0.45), None, 0.05)
office_chair(2900, 2150, "up", (0.95, 0.60, 0.70))
lamp((3350, 2550), 70)
rect(5650, 1400, X_FAC, 2650, WHITE)                                # desk 2
rect(6100, 1550, 6170, 2500, (0.4, 0.4, 0.45), None, 0.05)
office_chair(5350, 2000, "left", (0.45, 0.62, 0.88))
lamp((5800, 1500), 70)
circle((1750, 1500), 300, (0.99, 0.82, 0.35), (0.80, 0.62, 0.20))   # bean bag
plant((5460, 2470), 150)
rect(1330, 1000, 1580, 1900, WHITE)                                  # low shelf (daughter)
books(1330, 1000, 1580, 1900, vertical=True)

# kitchen
rect(2700, 3200, 5500, 3800, (0.94, 0.93, 0.91))                    # cabinets
rect(2700, 3200, 4900, 3780, (0.32, 0.32, 0.34), EDGE, 0.13)        # dark worktop
rrect(3100, 3260, 3650, 3740, 50, STEEL)
rrect(3150, 3310, 3600, 3690, 60, (0.88, 0.90, 0.92))
circle((3375, 3500), 35, (0.6, 0.62, 0.65))
rect(4150, 3250, 4600, 3750, (0.08, 0.08, 0.09))
for cy in (3380, 3620):
    circle((4375, cy), 105, None, (0.55, 0.55, 0.58), 0.13)
rect(4900, 3200, 5500, 3850, STEEL)                                 # fridge
line((5200, 3200), (5200, 3850), (0.55, 0.57, 0.6))
rect(3200, 4300, 4300, 4900, WALNUT)                                # breakfast bar
for sx in (3450, 3750, 4050):
    circle((sx, 4130), 170, CHAR)
rect(5800, 2950, 5950, 4150, (0.85, 0.85, 0.85))                    # service niche grille
plant((2400, 4600), 180)

# studio: dining
rect(400, 5400, 1750, 6300, WOOD)
for cx in (750, 1400):
    chair_top(cx, 5160, "down", LINEN)
    chair_top(cx, 6540, "up", LINEN)
circle((1075, 5850), 180, (1.0, 0.92, 0.70), (0.8, 0.7, 0.4), 0.1)   # pendant light
plant((1425, 5850), 90)
# studio: lounge
rrect(0, 7300, 900, 9150, 120, TEAL)
rrect(0, 7300, 220, 9150, 60, (0.30, 0.44, 0.50))
for py in (7420, 8230):
    rrect(240, py, 840, py + 780, 80, (0.46, 0.62, 0.68), (0.30, 0.44, 0.50), 0.1)
rrect(560, 7700, 820, 7950, 60, MUSTARD, None, 0.05)
rrect(560, 8550, 820, 8800, 60, (0.95, 0.60, 0.50), None, 0.05)
ellipse(1500, 8250, 330, 420, WOOD, EDGE, 0.13, "I-FURN")
circle((1500, 8250), 90, (0.95, 0.95, 0.95))
rect(2500, 8100, X_PART, 9200, WALNUT)
rect(2830, 8250, 2880, 9050, (0.05, 0.05, 0.06), None, 0.05)
plant((300, 6950), 220)

# master suite
bed(3100, 9225, 5250, 11225, "left", LINEN, throw=(0.55, 0.63, 0.72), pillows=2)
rect(3100, 9225, 3190, 11225, (0.55, 0.58, 0.62))                   # upholstered headboard
for ny in (8775, 11275):
    rect(3100, ny, 3550, ny + 400, WALNUT)
    lamp((3325, ny + 200))
rrect(5350, 7300, 6100, 8050, 150, MUSTARD)
rrect(5350, 7300, 6100, 7450, 60, (0.75, 0.55, 0.20))
lamp((5250, 7250), 120)
rect(5750, 9000, X_FAC, 11000, WALNUT)                              # dresser / TV console
rect(6150, 9300, 6200, 10700, (0.05, 0.05, 0.06), None, 0.05)
plant((5950, 11800), 230)
plant((3450, 6750), 180)
# en-suite
rect(3100, 5300, 3300, 5900, WHITE, EDGE, 0.13, "I-FIXT")
ellipse(3550, 5700, 250, 170, WHITE)
rect(3300, 5100, 3800, 5500, WALNUT, EDGE, 0.13, "I-FIXT")
ellipse(3550, 5330, 170, 110, WHITE)
rect(3900, 5100, 4600, 5850, (0.92, 0.94, 0.96), EDGE, 0.13, "I-FIXT")
circle((4250, 5475), 40, STEEL)
# walk-in wardrobe
rect(4700, 5100, X_FAC, 5600, (0.93, 0.89, 0.83))
rect(4700, 5600, 5000, 6250, (0.93, 0.89, 0.83))
line((4750, 5350), (6200, 5350), (0.5, 0.45, 0.4))
cols = [(0.35, 0.45, 0.60), (0.85, 0.85, 0.82), (0.70, 0.40, 0.35), (0.25, 0.25, 0.28), (0.90, 0.75, 0.55)]
for k, hx in enumerate(range(4800, 6150, 90)):
    line((hx, 5180), (hx + 30, 5520), cols[k % 5], 0.35)
circle((5400, 6000), 180, (0.85, 0.72, 0.60))                        # ottoman

# secret PC & home-cinema room
rect(400, 9400, 2500, 9460, (0.95, 0.97, 1.0), (0.2, 0.2, 0.25), 0.13)      # screen
M.poly([(400, 9460), (2500, 9460), (1650, 12400), (1250, 12400)], "I-FIXT",
       fill=None, color=(0.55, 0.70, 0.95), lw=0.08)                        # projection cone
for sx in (250, 2650):
    rect(sx - 120, 9440, sx + 120, 9680, (0.08, 0.08, 0.1))
    circle((sx, 9560), 60, (0.3, 0.3, 0.35))
for cx in (750, 1450, 2150):
    rrect(cx - 330, 11300, cx + 330, 12200, 110, BURGUNDY)
    rrect(cx - 330, 11950, cx + 330, 12200, 60, (0.42, 0.08, 0.12))
    rrect(cx - 250, 11380, cx + 250, 11900, 80, (0.66, 0.20, 0.25), None, 0.05)
for sx in (390, 1100, 1800, 2500):
    circle((sx, 11750), 70, (0.12, 0.12, 0.14))                     # cup holders
rect(1300, 12400, 1600, 12600, WHITE)                                # projector
circle((1450, 12420), 40, (0.2, 0.2, 0.25))
rect(300, 13300, 1900, 13950, (0.12, 0.12, 0.14))                    # PC desk
for mx0 in (450, 1150):
    rect(mx0, 13760, mx0 + 550, 13830, (0.05, 0.05, 0.08), GLOW, 0.15)
rect(700, 13450, 1500, 13600, (0.25, 0.25, 0.3), None, 0.05)        # keyboard
rect(1650, 13400, 1850, 13850, (0.10, 0.10, 0.12), GLOW, 0.15)      # PC tower
office_chair(1100, 12950, "up", (0.12, 0.12, 0.14))
circle((1100, 12950), 150, (0.80, 0.10, 0.15), None, 0.05)
for a, b in (((60, 9480), (60, 13900)), ((60, 9480), (2830, 9480))):
    line(a, b, (0.62, 0.40, 1.0), 0.35)                             # LED strip

# loggia
rect(3100, 12500, 3450, 13950, WALNUT)                               # bookcase = hidden door
for yb in range(12500, 13950, 250):
    books(3100, yb, 3450, yb + 250, vertical=False)
rrect(4650, 13350, 5350, 13900, 120, (0.80, 0.68, 0.50))
rrect(4700, 13400, 5300, 13750, 80, LINEN, None, 0.05)
circle((4400, 13050), 220, (0.95, 0.95, 0.93))
plant((5800, 13500), 380)
plant((3800, 13700), 200)
plant((4000, 12600), 160)

# ---------------------------------------------------------------------------------------
# 4. walls (final state), shafts, columns, glazing, doors
# ---------------------------------------------------------------------------------------
M.region(v3.new_solid, "A-WALL-FILL", fill=CHAR, outline_layer="A-WALL")
ring = box(2050, 3200, 2700, 3700).difference(box(2120, 3270, 2630, 3630))
M.region(ring, "A-WALL-FILL", fill=CHAR, outline_layer="A-WALL")
M.items.extend(kept_items)

# ---------------------------------------------------------------------------------------
# 5. labels on white pills
# ---------------------------------------------------------------------------------------
bp.register_fonts()


def tw(s, h, style):
    return pdfmetrics.stringWidth(s, "plan-" + style, h / CAP * mm) / mm * SCALE


LABEL_AT = {"2": (1250, 4450), "4": (4450, 2620), "7": (4450, 8150), "5": (5150, 4580),
            "7.1": (3700, 6050), "7.2": (5500, 5850), "6": (1450, 10450), "8": (5050, 12850)}
for no, ru, en, before, pt in v3.ROOMS4:
    x, y = LABEL_AT.get(no, pt)
    small = no in ("7.1", "7.2")
    h1, h2 = (1.6, 1.6) if small else ((2.2, 2.0) if no in ("4", "5") else (2.6, 2.3))
    t1, t2 = f"{no}  {ru}", f"{v3.AREAS[no]:.1f} м²"
    w = max(tw(t1, h1, "bold"), tw(t2, h2, "regular")) + 260
    hh = (h1 + h2) * SCALE + 300
    M.poly(rpts(x - w / 2, y - hh / 2, x + w / 2, y + hh / 2, 90), "I-LABEL",
           fill=WHITE, color=(0.55, 0.55, 0.58), lw=0.13)
    M.text((x, y - (h1 * SCALE / 2 + 45)), t1, h1, style="bold", color=(0.15, 0.15, 0.18))
    M.text((x, y + (h2 * SCALE / 2 + 45)), t2, h2, color=(0.35, 0.35, 0.4))

LEGEND = [(OAK, "Паркет дуб / Oak parquet"), (STONE, "Керамогранит / Porcelain tile"),
          (TILE, "Плитка с/у / Bathroom tile"), (CARPET, "Ковролин / Carpet (cinema)"),
          (DECK, "Террасная доска / Decking")]
NOTES = [
    ("ПРИМЕЧАНИЯ / NOTES", "bold"),
    ("1. Дизайн-планировка варианта 3 (лист 4), М 1:50 при", "regular"),
    ("   печати A3 100 %. / Furnished layout of variant 3, 1:50.", "italic"),
    ("2. Стены, двери, размеры и площади - как на листе 4.", "regular"),
    ("   Walls, doors, sizes and areas as on sheet 4.", "italic"),
    ("3. Мебель и отделка - концепция, размеры условные.", "regular"),
    ("   Furniture and finishes are a concept, sizes indicative.", "italic"),
    ("4. Кинозал: затемняющие шторы на окнах.", "regular"),
    ("   Cinema room: blackout blinds on the glazing.", "italic"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    bp.check_dims()
    br.build_sheet(v3.ROOMS4, v3.AREAS, NOTES, sheet="5",
                   title_ru="Дизайн-планировка с мебелью (вариант 3)",
                   title_en="Furnished colour design layout (replanning variant 3)",
                   header="ДИЗАЙН-ПЛАНИРОВКА  /  FURNISHED DESIGN LAYOUT", legend=LEGEND)
    pdf_path = os.path.join(OUT, "design-v3_1-50_A3.pdf")
    w = bp.PdfWriter(pdf_path)
    w.c.setTitle("Furnished colour design layout 1:50 (A3)")
    w.draw(M, lambda p: bp.to_paper(*p))
    w.dims()
    w.draw(P, lambda p: p)
    w.save()
    dxf_path = os.path.join(OUT, "design-v3_1-50.dxf")
    bp.write_dxf(dxf_path)
    bp.verify_dxf(dxf_path)
    bp.verify_pdf(pdf_path)
    import pymupdf
    pymupdf.open(pdf_path)[0].get_pixmap(dpi=200).save(os.path.join(OUT, "design-v3_1-50_A3.png"))
    print("items:", len(M.items))


if __name__ == "__main__":
    main()
