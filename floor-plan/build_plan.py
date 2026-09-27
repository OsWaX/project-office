#!/usr/bin/env python3
"""Rebuild the apartment floor plan (source/original-plan.jpg) as a 1:50 drawing.

Outputs (in ./output):
    flat-plan_1-50.dxf        CAD file, model space in millimetres (1 unit = 1 mm),
                              plus a paper-space layout "A3 1-50" with a 1:50 viewport
    flat-plan_1-50_A3.pdf     print-ready A3 sheet, plan at exactly 1:50
    flat-plan_1-50_A3.png     raster preview of the PDF

Every dimension printed on the source plan is used as an exact input; everything the
source does not dimension (wall thickness, columns, openings, furniture) was scaled off
a perspective-corrected copy of the source image. Run:  python3 build_plan.py
"""

import math
import os
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")

SCALE = 50                   # drawing scale 1:50
SHEET_W, SHEET_H = 297, 420  # A3 portrait, mm

# --------------------------------------------------------------------------------------
# 1. Inputs: the dimensions printed on the source plan (clear internal sizes, mm)
# --------------------------------------------------------------------------------------
HALL_TO_COLUMN = 3600   # Прихожая: west wall -> face of column
HALL_DEPTH = 2000       # Прихожая
LIVING_W = 4970         # Гостиная
LIVING_D = 3000         # Гостиная
BATH_D = 2450           # С/У
BATH_W = 1665           # С/У
CORR_W = 1850           # Коридор
CORR_L = 4350           # Коридор: corner of living-room wall -> bedroom wall
KITCHEN_D = 2900        # Кухня
KITCHEN_W = 4200        # Кухня
BED2_D = 5850           # Спальня 19.7
BED2_W = 3150           # Спальня 19.7
BED1_D = 6300           # Спальня 17.8
BED1_W = 2900           # Спальня 17.8
LOGGIA_D = 1650         # Лоджия

ROOMS = [  # (no., name RU, name EN, area m² as printed on the source)
    (1, "Прихожая", "Entrance hall", 5.8),
    (2, "Коридор", "Corridor", 14.1),
    (3, "С/У", "Bathroom / WC", 4.1),
    (4, "Гостиная", "Living / dining room", 14.4),
    (5, "Кухня", "Kitchen", 11.0),
    (6, "Спальня", "Bedroom", 17.8),
    (7, "Спальня", "Bedroom", 19.7),
    (8, "Лоджия", "Loggia", 5.3),
]

# Not dimensioned on the source -> measured from the rectified image
T = 200                 # wall thickness (all walls read as ~200 mm)
COL_W_FACE = -300       # west face of the column the 3600 dimension runs to

# --------------------------------------------------------------------------------------
# 2. Grid derived from the inputs
#    Working frame: x to the right, y DOWN the sheet (as the source is read),
#    x = 0 on the inner face of the corridor / bedroom-1 west wall,
#    y = 0 on the inner face of the north wall.
# --------------------------------------------------------------------------------------
X_KIT = CORR_W                      # 1850  kitchen west wall, corridor face
X_FAC = X_KIT + T + KITCHEN_W       # 6250  inner line of the glazed facade
assert X_FAC == BED1_W + T + BED2_W, "kitchen chain and bedroom chain disagree"
X_PART = BED1_W                     # 2900  bedroom partition, west face
X_LIV = X_FAC - LIVING_W            # 1280  living-room west wall, room face
X_HALL = COL_W_FACE - HALL_TO_COLUMN  # -3900 hall west wall, room face
X_BATH_E = -T                       # -200  bathroom east wall, room face
X_BATH_W = X_BATH_E - BATH_W        # -1865 bathroom west (thin) wall, room face

Y_LK = LIVING_D                     # 3000  living / kitchen partition, living face
Y_KB = Y_LK + T + KITCHEN_D         # 6100  kitchen / bedroom-2 wall, kitchen face
Y_LG = Y_KB + T + BED2_D            # 12150 bedroom-2 / loggia wall, bedroom face
Y_FAC = Y_LG + T + LOGGIA_D         # 14000 inner line of the south facade
Y_B1 = Y_FAC - BED1_D - T           # 7500  bedroom-1 north wall, corridor face
Y_CORNER = Y_B1 - CORR_L            # 3150  corner the 4350 dimension starts from
Y_HALL = HALL_DEPTH                 # 2000  hall south wall, hall face
Y_BATH_N = Y_HALL + T               # 2200  bathroom north face
Y_BATH_S = Y_BATH_N + BATH_D        # 4650  bathroom south face

# 45° chamfer walls. Living room: outer face passes through the 4350 corner.
LIV_OUT_C = Y_CORNER - X_KIT        # outer face: y = x + 1300
LIV_IN_C = LIV_OUT_C - T * math.sqrt(2)  # inner face: y = x + 1017
HALL_UP_C = Y_HALL - (X_HALL + 2900)     # hall zone 2900 wide (5.8 m² / 2.0 m): y = x + 3000
HALL_LO_C = HALL_UP_C + T * math.sqrt(2)  # y = x + 3283

GLZ = 150                           # depth of the curtain-wall band drawn outside the facade line


def r(x0, y0, x1, y1):
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


# --------------------------------------------------------------------------------------
# 3. Primitive collector (shared by the DXF and PDF writers)
# --------------------------------------------------------------------------------------
LAYERS = {
    #  name          colour (r,g,b 0..1)    lineweight mm
    "A-WALL":       ((0.0, 0.0, 0.0), 0.50),
    "A-WALL-FILL":  ((0.60, 0.60, 0.60), 0.0),
    "A-COLS":       ((0.0, 0.0, 0.0), 0.50),
    "A-GLAZ":       ((0.10, 0.42, 0.78), 0.18),
    "A-GLAZ-FRAME": ((0.0, 0.0, 0.0), 0.25),
    "A-DOOR":       ((0.0, 0.0, 0.0), 0.35),
    "A-DOOR-SWING": ((0.25, 0.25, 0.25), 0.13),
    "A-SHAFT":      ((0.0, 0.0, 0.0), 0.25),
    "A-FIXT":       ((0.15, 0.15, 0.15), 0.18),
    "A-FURN":       ((0.42, 0.42, 0.42), 0.13),
    "A-DIMS":       ((0.0, 0.0, 0.0), 0.13),
    "A-TEXT":       ((0.0, 0.0, 0.0), 0.18),
    "A-SHEET":      ((0.0, 0.0, 0.0), 0.25),
}
TEXT_STYLES = {"regular": "arial.ttf", "bold": "arialbd.ttf", "italic": "ariali.ttf"}
GLASS_FILL = (0.75, 0.87, 0.97)


class Space:
    """A list of drawing primitives in one coordinate space (model mm or paper mm)."""

    def __init__(self):
        self.items = []

    def line(self, a, b, layer, lw=None, color=None, dash=False):
        self.items.append(("line", layer, dict(a=a, b=b, lw=lw, color=color, dash=dash)))

    def poly(self, pts, layer, closed=True, lw=None, color=None, fill=None, dash=False):
        self.items.append(("poly", layer, dict(pts=list(pts), closed=closed, lw=lw,
                                               color=color, fill=fill, dash=dash)))

    def rect(self, x0, y0, x1, y1, layer, **kw):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, **kw)

    def region(self, geom, layer, fill, outline_layer=None, lw=None):
        """Filled (multi)polygon with holes; outline drawn on outline_layer."""
        polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
        for p in polys:
            rings = [list(p.exterior.coords)[:-1]] + [list(i.coords)[:-1] for i in p.interiors]
            self.items.append(("region", layer, dict(rings=rings, fill=fill)))
            if outline_layer:
                for ring in rings:
                    self.poly(ring, outline_layer, lw=lw)

    def arc(self, c, rad, a0, a1, layer, lw=None, color=None):
        """Arc sweeping from angle a0 to a1 (degrees, a1 > a0) in the space's own axes."""
        self.items.append(("arc", layer, dict(c=c, r=rad, a0=a0, a1=a1, lw=lw, color=color)))

    def circle(self, c, rad, layer, lw=None, fill=None, color=None):
        self.items.append(("circle", layer, dict(c=c, r=rad, lw=lw, fill=fill, color=color)))

    def text(self, p, s, h, layer="A-TEXT", align="mc", rot=0, style="regular", color=None):
        """h = cap height in PAPER mm; rot in degrees counter-clockwise as seen on the sheet."""
        self.items.append(("text", layer, dict(p=p, s=s, h=h, align=align, rot=rot,
                                               style=style, color=color)))


M = Space()   # model space, working frame (x right, y down), mm
P = Space()   # paper space, sheet frame (x right, y down from sheet top), mm
DIMS = []     # (p1, p2, orient, pos, expected)


def dim(p1, p2, orient, pos, expected, ext_from=None, text_at=None):
    """Linear dimension. orient 'h' or 'v'; pos = y (h) or x (v) of the dimension line;
    text_at = optional position of the text along the line (model mm)."""
    DIMS.append(dict(p1=p1, p2=p2, orient=orient, pos=pos, expected=expected,
                     ext_from=ext_from, text_at=text_at))


# --------------------------------------------------------------------------------------
# 4. Building elements
# --------------------------------------------------------------------------------------
walls = [
    r(X_HALL - T, -T, X_FAC, 0),                         # north wall
    r(X_HALL - T, -T, X_HALL, Y_BATH_N),                 # hall west wall
    r(X_HALL - T, Y_HALL, X_HALL + 2900, Y_BATH_N),      # hall south wall
    Polygon([(X_HALL + 2900, Y_HALL), (0, HALL_UP_C), (0, HALL_LO_C),
             (Y_HALL - HALL_LO_C, Y_HALL)]),               # 45° wall hall -> corridor
    r(X_BATH_E, HALL_UP_C, 0, Y_FAC),                    # corridor / bathroom / bedroom-1 west wall
    r(X_BATH_W - 435, Y_BATH_N, X_BATH_W - 235, 3700),   # bathroom west wall (upper, 200)
    r(X_BATH_W - 235, 3600, X_BATH_W, 3700),             # bathroom: step to the thin wall
    r(X_BATH_W - 120, 3600, X_BATH_W, Y_BATH_S),         # bathroom west wall (lower, 120)
    r(X_BATH_W - 435, Y_BATH_S, 0, Y_BATH_S + T),        # bathroom south wall
    r(X_LIV - T, 0, X_LIV, LIV_OUT_C + X_LIV - T),       # living-room west wall
    Polygon([(X_LIV - T, X_LIV - T + LIV_IN_C), (Y_LK - LIV_IN_C, Y_LK),
             (X_KIT, Y_CORNER), (X_LIV - T, X_LIV - T + LIV_OUT_C)]),  # 45° chamfer
    r(X_KIT, Y_LK, 5500, Y_LK + T),                      # living / kitchen partition
    r(X_KIT, Y_LK, X_KIT + T, 6450),                     # kitchen west wall
    r(X_KIT, Y_KB, X_FAC, Y_KB + T),                     # kitchen / bedroom-2 wall
    r(X_KIT, 7350, X_KIT + T, Y_B1),                     # bedroom-2 door jamb
    r(0, Y_B1, X_PART + T, Y_B1 + T),                    # bedroom-1 north wall
    r(X_PART, Y_B1, X_PART + T, Y_FAC),                  # bedroom partition
    r(X_PART + T, Y_LG, 4300, Y_LG + T),                 # bedroom-2 / loggia wall (solid part)
    r(5500, 2700, X_FAC, 2700 + T),                      # service niche north wall
    r(5500, 2700, 5700, 4250),                           # service niche west wall
]
columns = [
    r(COL_W_FACE, -T, 250, 250),        # C1 - the 3600 dimension ends on its west face
    r(5750, -T, X_FAC, 250),            # C2
    r(-T, 5800, 275, 6350),             # C3
    r(5750, 5800, X_FAC, 6350),         # C4
    r(-T, 11850, 275, 12400),           # C5
    r(5750, 11850, X_FAC, 12400),       # C6
    r(-T, 13750, 250, Y_FAC),           # C7
    r(6100, 3700, X_FAC, 4250),         # pier at the service niche
    r(2250, 13850, 3350, Y_FAC),        # facade pier between the bedrooms
]
openings = [
    r(X_HALL - T, 300, X_HALL, 1300),       # entrance door 1000
    r(X_BATH_E, 3300, 0, 4000),             # bathroom door 700
    r(X_LIV - T, 650, X_LIV, 1850),         # living-room double door 1200
    r(X_KIT, 3925, X_KIT + T, 4825),        # kitchen door 900
    r(300, Y_B1, 1200, Y_B1 + T),           # bedroom-1 door 900
    r(-T, 12400, 0, 13750),                 # corner glazing in bedroom-1 west wall
]
col_union = unary_union(columns)
wall_geom = unary_union(walls).difference(unary_union(openings)).difference(col_union)
M.region(wall_geom, "A-WALL-FILL", fill="wall", outline_layer="A-WALL")
M.region(col_union, "A-COLS", fill="solid", outline_layer="A-COLS")


# --- glazing -----------------------------------------------------------------------------
def glazing_band(x0, y0, x1, y1, vertical):
    """Curtain-wall band: frame lines on both faces, double glass line in the middle."""
    if vertical:
        M.line((x0, y0), (x0, y1), "A-GLAZ-FRAME")
        M.line((x1, y0), (x1, y1), "A-GLAZ-FRAME")
        for gx in (x0 + (x1 - x0) * 0.4, x0 + (x1 - x0) * 0.6):
            M.line((gx, y0), (gx, y1), "A-GLAZ")
    else:
        M.line((x0, y0), (x1, y0), "A-GLAZ-FRAME")
        M.line((x0, y1), (x1, y1), "A-GLAZ-FRAME")
        for gy in (y0 + (y1 - y0) * 0.4, y0 + (y1 - y0) * 0.6):
            M.line((x0, gy), (x1, gy), "A-GLAZ")


glazing_band(X_FAC, -T, X_FAC + GLZ, Y_FAC + GLZ, vertical=True)
glazing_band(-T, Y_FAC, X_FAC + GLZ, Y_FAC + GLZ, vertical=False)
M.line((X_FAC, -T), (X_FAC + GLZ, -T), "A-GLAZ-FRAME")
M.line((-T, Y_FAC), (-T, Y_FAC + GLZ), "A-GLAZ-FRAME")
for my in (700, 1725, 2750, 3750, 4775, 6800, 7800, 8800, 9825, 10825, 12900):
    M.rect(X_FAC, my - 30, X_FAC + GLZ, my + 30, "A-GLAZ-FRAME", fill="solid")
for mx in (1250, 4300, 5300):
    M.rect(mx - 30, Y_FAC, mx + 30, Y_FAC + GLZ, "A-GLAZ-FRAME", fill="solid")
# corner glazing in the bedroom-1 west wall
for gx in (-T, 0):
    M.line((gx, 12400), (gx, 13750), "A-GLAZ-FRAME")
for gx in (-120, -80):
    M.line((gx, 12400), (gx, 13750), "A-GLAZ")
# fixed glass between bedroom 2 and the loggia
for gy in (Y_LG, Y_LG + T):
    M.line((4300, gy), (5000, gy), "A-GLAZ-FRAME")
for gy in (Y_LG + 80, Y_LG + 120):
    M.line((4300, gy), (5000, gy), "A-GLAZ")
M.line((5000, Y_LG), (5000, Y_LG + T), "A-GLAZ-FRAME")


# --- doors -------------------------------------------------------------------------------
def door(hinge, closed_tip, open_tip, layer="A-DOOR", color=None):
    """Leaf drawn open at 90°, swing arc from the open tip to the closed position."""
    M.line(hinge, open_tip, layer, color=color)
    rad = math.dist(hinge, open_tip)
    a_open = math.degrees(math.atan2(open_tip[1] - hinge[1], open_tip[0] - hinge[0]))
    a_closed = math.degrees(math.atan2(closed_tip[1] - hinge[1], closed_tip[0] - hinge[0]))
    d = (a_closed - a_open + 180) % 360 - 180
    a0, a1 = (a_open, a_open + d) if d > 0 else (a_closed, a_closed - d)
    M.arc(hinge, rad, a0, a1, "A-DOOR-SWING")


door((X_HALL - T, 300), (X_HALL - T, 1300), (X_HALL - T - 1000, 300))      # entrance
door((X_BATH_E, 3300), (X_BATH_E, 4000), (X_BATH_E - 700, 3300))           # bathroom
door((X_LIV - T, 650), (X_LIV - T, 1250), (X_LIV - T - 600, 650))          # living, leaf 1
door((X_LIV - T, 1850), (X_LIV - T, 1250), (X_LIV - T - 600, 1850))        # living, leaf 2
door((X_KIT + T, 3925), (X_KIT + T, 4825), (X_KIT + T + 900, 3925))        # kitchen
door((X_KIT + T, 7350), (X_KIT + T, 6450), (X_KIT + T + 900, 7350))        # bedroom 2
door((300, Y_B1), (1200, Y_B1), (300, Y_B1 - 900))                         # bedroom 1
door((6100, 4250), (5700, 4250), (6100, 4650))                             # service niche
door((5750, Y_LG + T), (5000, Y_LG + T), (5750, Y_LG + T + 750),
     color=LAYERS["A-GLAZ"][0])                                            # loggia (glass)
M.line((5700, 4250), (6100, 4250), "A-FIXT")                               # niche threshold


# --- shafts ------------------------------------------------------------------------------
def shaft(x0, y0, x1, y1, wall=0):
    if wall:
        ring = r(x0, y0, x1, y1).difference(r(x0 + wall, y0 + wall, x1 - wall, y1 - wall))
        M.region(ring, "A-WALL-FILL", fill="wall", outline_layer="A-WALL")
        x0, y0, x1, y1 = x0 + wall, y0 + wall, x1 - wall, y1 - wall
    else:
        M.rect(x0, y0, x1, y1, "A-SHAFT")
    M.line((x0, y0), (x1, y1), "A-SHAFT")
    M.line((x0, y1), (x1, y0), "A-SHAFT")


shaft(X_BATH_W - 435, 3700, X_BATH_W - 120, Y_BATH_S)   # ventilation shaft by the bathroom
shaft(X_KIT + T, Y_LK + T, 2700, 3700, wall=70)         # ventilation shaft in the kitchen


# --- furniture & fixtures helpers ------------------------------------------------------------
def rrect(x0, y0, x1, y1, rad, layer="A-FURN", fill=None):
    pts = []
    for cx, cy, a in ((x1 - rad, y0 + rad, -90), (x1 - rad, y1 - rad, 0),
                      (x0 + rad, y1 - rad, 90), (x0 + rad, y0 + rad, 180)):
        for k in range(7):
            t = math.radians(a + 15 * k)
            pts.append((cx + rad * math.cos(t), cy + rad * math.sin(t)))
    M.poly(pts, layer, fill=fill)


def ellipse(cx, cy, rx, ry, layer="A-FIXT", n=48):
    M.poly([(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n))
            for k in range(n)], layer)


def rotated_rect(cx, cy, w, h, ang, layer="A-FURN"):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    M.poly([(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)
            for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))],
           layer)


def chair(cx, cy, facing):
    """Dining chair 480x480, facing = direction the sitter looks: 'up','down','left','right'."""
    w, d = 480, 480
    if facing in ("up", "down"):
        rrect(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2, 90)
        by = cy + d / 2 - 70 if facing == "up" else cy - d / 2 + 70
        M.line((cx - w / 2 + 40, by), (cx + w / 2 - 40, by), "A-FURN")
    else:
        rrect(cx - d / 2, cy - w / 2, cx + d / 2, cy + w / 2, 90)
        bx = cx + d / 2 - 70 if facing == "left" else cx - d / 2 + 70
        M.line((bx, cy - w / 2 + 40), (bx, cy + w / 2 - 40), "A-FURN")


def wardrobe(x0, y0, x1, y1, along_x=True):
    M.rect(x0, y0, x1, y1, "A-FURN")
    if along_x:
        ym = (y0 + y1) / 2
        M.line((x0 + 50, ym), (x1 - 50, ym), "A-FURN")
        x = x0 + 120
        while x < x1 - 80:
            M.line((x - 40, ym - (y1 - y0) * 0.35), (x + 40, ym + (y1 - y0) * 0.35), "A-FURN")
            x += 160


def bed(x0, y0, x1, y1, head):
    """Double bed; head = 'left' or 'right' (side against the wall)."""
    rrect(x0, y0, x1, y1, 60)
    w = y1 - y0
    sign = 1 if head == "left" else -1
    hx = x0 if head == "left" else x1
    M.line((hx + sign * 80, y0), (hx + sign * 80, y1), "A-FURN")            # headboard
    for py in (y0 + 0.08 * w, y0 + 0.54 * w):                                # pillows
        px0, px1 = sorted((hx + sign * 130, hx + sign * 530))
        rrect(px0, py, px1, py + 0.38 * w, 60)
    fx = hx + sign * 650                                                     # blanket fold
    M.line((fx, y0), (fx, y1), "A-FURN")
    M.poly([(fx, y1), (fx + sign * 380, y1), (fx, y1 - 380)], "A-FURN", closed=True)


def nightstand(x0, y0, x1, y1):
    M.rect(x0, y0, x1, y1, "A-FURN")
    M.circle(((x0 + x1) / 2, (y0 + y1) / 2), 120, "A-FURN")


def desk(x0, y0, x1, y1, screen_side):
    M.rect(x0, y0, x1, y1, "A-FURN")
    sx = x1 - 90 if screen_side == "right" else x0 + 90
    M.line((sx, y0 + 350), (sx, y1 - 550), "A-FURN")
    M.line((sx - 20, y0 + 350), (sx - 20, y1 - 550), "A-FURN")


def office_chair(cx, cy, ang):
    rotated_rect(cx, cy, 520, 480, ang)
    a = math.radians(ang)
    ox, oy = -240 * math.cos(a), -240 * math.sin(a)
    rotated_rect(cx + ox, cy + oy, 90, 480, ang)


# --- hall, bathroom ------------------------------------------------------------------------
wardrobe(X_HALL, Y_HALL - 500, X_HALL + 2900, Y_HALL)
# shower: glass screen, mixer, drain
M.rect(X_BATH_W - 235, 2990, -1300, 3010, "A-GLAZ", fill="glass")
M.rect(-1350, 3025, 3025 - HALL_LO_C, 3040, "A-GLAZ")                    # sliding panel
M.rect(X_BATH_W - 235, 2500, X_BATH_W - 175, 2600, "A-FIXT")
M.line((X_BATH_W - 175, 2550), (-1900, 2550), "A-FIXT")
M.circle((-1850, 2550), 60, "A-FIXT")
M.rect(-1400, 2550, -1300, 2650, "A-FIXT")
M.line((-1400, 2550), (-1300, 2650), "A-FIXT")
M.line((-1400, 2650), (-1300, 2550), "A-FIXT")
# WC
M.rect(-1600, Y_BATH_S - 200, -1200, Y_BATH_S, "A-FIXT")
ellipse(-1400, 4230, 180, 260)
ellipse(-1400, 4250, 120, 190)
# wash basin on a vanity
M.rect(-1000, Y_BATH_S - 480, -350, Y_BATH_S, "A-FIXT")
ellipse(-675, Y_BATH_S - 230, 230, 160)
M.circle((-675, Y_BATH_S - 60), 30, "A-FIXT")

# --- living / dining -----------------------------------------------------------------------
M.rect(2300, 950, 5200, 2050, "A-FURN")
for cx in (2775, 3425, 4100, 4750):
    chair(cx, 720, "down")
    chair(cx, 2280, "up")
chair(2060, 1500, "right")
chair(5440, 1500, "left")

# --- kitchen -------------------------------------------------------------------------------
M.rect(2700, Y_LK + T, 5500, 3800, "A-FIXT")                  # worktop 600
rrect(3300, 3260, 3850, 3740, 40, "A-FIXT")                   # sink
rrect(3350, 3310, 3800, 3690, 60, "A-FIXT")
M.circle((3575, 3500), 35, "A-FIXT")
M.circle((3575, 3290), 25, "A-FIXT")
M.rect(4450, 3250, 4900, 3750, "A-FIXT")                      # hob
M.circle((4675, 3380), 105, "A-FIXT")
M.circle((4675, 3620), 105, "A-FIXT")
M.rect(X_KIT + T, 5500, 2700, Y_KB, "A-FIXT")                  # fridge
for a in (0, 60, 120):
    t = math.radians(a)
    M.line((2375 - 120 * math.cos(t), 5800 - 120 * math.sin(t)),
           (2375 + 120 * math.cos(t), 5800 + 120 * math.sin(t)), "A-FIXT")
M.arc((X_KIT + T, 5500), 650, 270, 360, "A-DOOR-SWING")        # fridge door swing
M.rect(3750, 5350, 4900, 5950, "A-FURN")                       # table
chair(4040, 5110, "down")
chair(4610, 5110, "down")
chair(3500, 5650, "right")
chair(5150, 5650, "left")
# service niche: louvred grille
M.rect(5800, 2950, 5950, 4150, "A-FIXT")
yy = 3000
while yy < 4100:
    M.line((5800, yy), (5950, yy + 60), "A-FIXT")
    yy += 100

# --- bedrooms, loggia ----------------------------------------------------------------------
wardrobe(1300, Y_B1 + T, X_PART, Y_B1 + T + 500)
bed(750, 9425, X_PART, 11425, "right")
nightstand(2450, 8975, X_PART, 9375)
nightstand(2450, 11475, X_PART, 11875)
desk(2200, 12450, X_PART, 13850, "right")
office_chair(1900, 13150, 15)

wardrobe(4300, 6350, X_FAC, 6950)
bed(X_PART + T, 9225, 5250, 11225, "left")
nightstand(X_PART + T, 8775, 3550, 9175)
nightstand(X_PART + T, 11275, 3550, 11675)
desk(X_PART + T, 12450, 3800, 13850, "left")
office_chair(4000, 13150, 165)
M.circle((5800, 13500), 330, "A-FURN")                          # plant
for k in range(8):
    t = math.radians(22.5 + 45 * k)
    M.line((5800, 13500), (5800 + 330 * math.cos(t), 13500 + 330 * math.sin(t)), "A-FURN")

# --- room labels -------------------------------------------------------------------------
LABELS = {1: (-2400, 1000), 2: (750, 4700), 3: (-1300, 3680), 4: (3750, 1500),
          5: (4150, 4500), 6: (1500, 10425), 7: (4350, 10000), 8: (5050, 13400)}
for no, ru, en, area in ROOMS:
    x, y = LABELS[no]
    M.circle((x, y - 480), 140, "A-TEXT")
    M.text((x, y - 480), str(no), 2.0, style="bold")
    M.text((x, y - 150), ru, 3.0, style="italic")
    M.text((x, y + 150), f"{area:.1f} м²", 3.0)

# --- dimensions (all from the source) -------------------------------------------------------
dim((X_HALL, 250), (COL_W_FACE, 250), "h", 250, HALL_TO_COLUMN)
dim((X_HALL + 2900, 0), (X_HALL + 2900, Y_HALL), "v", X_HALL + 2900, HALL_DEPTH)
dim((X_LIV, 375), (X_FAC, 375), "h", 375, LIVING_W)
dim((5400, 0), (5400, Y_LK), "v", 5400, LIVING_D)
dim((-1700, Y_BATH_N), (-1700, Y_BATH_S), "v", -1700, BATH_D)
dim((X_BATH_W, 4380), (X_BATH_E, 4380), "h", 4380, BATH_W)
dim((0, 5750), (X_KIT, 5750), "h", 5750, CORR_W)
dim((X_KIT, Y_CORNER), (1675, Y_B1), "v", 1675, CORR_L, ext_from=(X_KIT, Y_CORNER))
dim((3025, Y_LK + T), (3025, Y_KB), "v", 3025, KITCHEN_D)
dim((X_KIT + T, 5750), (X_FAC, 5750), "h", 5750, KITCHEN_W)
dim((3600, Y_KB + T), (3600, Y_LG), "v", 3600, BED2_D, text_at=8200)
dim((X_PART + T, 11750), (X_FAC, 11750), "h", 11750, BED2_W)
dim((575, Y_B1 + T), (575, Y_FAC), "v", 575, BED1_D)
dim((0, 11750), (X_PART, 11750), "h", 11750, BED1_W)
dim((4550, Y_LG + T), (4550, Y_FAC), "v", 4550, LOGGIA_D)


def dim_endpoints(d):
    if d["orient"] == "h":
        return (d["p1"][0], d["pos"]), (d["p2"][0], d["pos"])
    return (d["pos"], d["p1"][1]), (d["pos"], d["p2"][1])


def check_dims():
    bad = []
    for d in DIMS:
        a, b = dim_endpoints(d)
        L = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if round(L, 6) != d["expected"]:
            bad.append((d["expected"], L))
    if bad:
        sys.exit(f"dimension mismatch: {bad}")
    print(f"geometry check: all {len(DIMS)} source dimensions reproduced exactly")


# --------------------------------------------------------------------------------------
# 5. Sheet layout (paper mm, y down from the top edge of the sheet)
# --------------------------------------------------------------------------------------
XMIN, XMAX = X_HALL - T - 1000, X_FAC + GLZ     # plan extents incl. the open entrance leaf
YMIN, YMAX = -T, Y_FAC + GLZ
PLAN_W, PLAN_H = (XMAX - XMIN) / SCALE, (YMAX - YMIN) / SCALE
FRAME = (20, 5, SHEET_W - 5, SHEET_H - 5)       # x0, y0, x1, y1 (GOST margins)
OX = FRAME[0] + (FRAME[2] - FRAME[0] - PLAN_W) / 2
OY = 40


def to_paper(x, y):
    return OX + (x - XMIN) / SCALE, OY + (y - YMIN) / SCALE


def build_sheet():
    x0, y0, x1, y1 = FRAME
    P.rect(x0, y0, x1, y1, "A-SHEET", lw=0.7)
    P.text((OX, OY - 9), "ПЛАН КВАРТИРЫ  /  APARTMENT FLOOR PLAN", 4.0, align="ml", style="bold")
    P.text((OX, OY - 4), "М 1:50", 3.0, align="ml")

    # room schedule (explication) in the free area west of bedroom 1
    sx, sy = to_paper(XMIN, 5400)
    sx += 3
    cols = [0, 8, 30, 64, 84]
    row_h = 6.5
    P.text((sx, sy - 3), "ЭКСПЛИКАЦИЯ ПОМЕЩЕНИЙ / ROOM SCHEDULE", 2.5, align="ml", style="bold")
    rows = [("№", "Помещение", "Room", "м²")] + \
           [(str(n), ru, en, f"{a:.1f}") for n, ru, en, a in ROOMS] + \
           [("", "Итого", "Total", f"{sum(a for *_, a in ROOMS):.1f}")]
    for i, row in enumerate(rows):
        ty = sy + i * row_h
        P.line((sx, ty), (sx + cols[-1], ty), "A-SHEET", lw=0.5 if i in (0, 1, len(rows) - 1) else 0.18)
        for j, cell in enumerate(row):
            if j == 3:
                P.text((sx + cols[4] - 2, ty + row_h / 2), cell, 2.2, align="mr",
                       style="bold" if i in (0, len(rows) - 1) else "regular")
            elif j == 0:
                P.text((sx + (cols[0] + cols[1]) / 2, ty + row_h / 2), cell, 2.2,
                       style="bold" if i == 0 else "regular")
            else:
                P.text((sx + cols[j] + 1.5, ty + row_h / 2), cell, 2.2, align="ml",
                       style="bold" if i in (0, len(rows) - 1) else "regular")
    bottom = sy + len(rows) * row_h
    P.line((sx, bottom), (sx + cols[-1], bottom), "A-SHEET", lw=0.5)
    for c in cols:
        P.line((sx + c, sy), (sx + c, bottom), "A-SHEET", lw=0.5 if c in (0, cols[-1]) else 0.18)

    # notes
    ny = bottom + 10
    notes = [
        ("ПРИМЕЧАНИЯ / NOTES", "bold"),
        ("1. Размеры в мм. Масштаб 1:50 при печати A3 100%.", "regular"),
        ("   Dimensions in mm. 1:50 when printed on A3 at 100 %.", "italic"),
        ("2. Размеры помещений и площади - по исходному плану.", "regular"),
        ("   Room dimensions and areas as given on the source plan.", "italic"),
        ("3. Толщина стен 200 мм, колонны, проёмы и мебель", "regular"),
        ("   сняты с исходного изображения - уточнить на месте.", "regular"),
        ("   Walls (200 mm), columns, openings and furniture scaled", "italic"),
        ("   from the source image - verify on site.", "italic"),
    ]
    for k, (s, st) in enumerate(notes):
        P.text((sx, ny + k * 4.6), s, 2.0, align="ml", style=st)

    # legend
    ly = ny + len(notes) * 4.6 + 6
    P.text((sx, ly), "УСЛОВНЫЕ ОБОЗНАЧЕНИЯ / LEGEND", 2.2, align="ml", style="bold")
    items = [("wall", "Стена / Wall"), ("col", "Колонна / Column"),
             ("glass", "Остекление / Glazing"), ("shaft", "Вентшахта / Vent shaft")]
    for k, (kind, label) in enumerate(items):
        yy = ly + 6 + k * 6
        bx0, by0, bx1, by1 = sx, yy - 1.8, sx + 10, yy + 1.8
        if kind == "wall":
            P.rect(bx0, by0, bx1, by1, "A-WALL", fill="wall", lw=0.35)
        elif kind == "col":
            P.rect(bx0, by0, bx1, by1, "A-COLS", fill="solid", lw=0.35)
        elif kind == "glass":
            P.line((bx0, by0), (bx1, by0), "A-GLAZ-FRAME")
            P.line((bx0, by1), (bx1, by1), "A-GLAZ-FRAME")
            P.line((bx0, yy - 0.4), (bx1, yy - 0.4), "A-GLAZ")
            P.line((bx0, yy + 0.4), (bx1, yy + 0.4), "A-GLAZ")
        else:
            P.rect(bx0, by0, bx1, by1, "A-SHAFT")
            P.line((bx0, by0), (bx1, by1), "A-SHAFT")
            P.line((bx0, by1), (bx1, by0), "A-SHAFT")
        P.text((bx1 + 3, yy), label, 2.0, align="ml")

    # scale bar 0-5 m (1 m = 20 mm at 1:50)
    bx, by = OX, OY + PLAN_H + 8
    P.text((bx, by - 3.5), "Масштабная линейка / Scale bar 1:50 (м / m)", 2.0, align="ml")
    for k in range(5):
        P.rect(bx + k * 1000 / SCALE, by, bx + (k + 1) * 1000 / SCALE, by + 1.6, "A-SHEET",
               lw=0.25, fill="solid" if k % 2 == 0 else None)
    for k in range(6):
        P.text((bx + k * 1000 / SCALE, by + 4.5), str(k), 2.0)

    # title block (bottom right, 185 x 40)
    tx0, ty0, tx1, ty1 = x1 - 185, y1 - 40, x1, y1
    P.rect(tx0, ty0, tx1, ty1, "A-SHEET", lw=0.7)
    P.line((tx0, ty0 + 14), (tx1, ty0 + 14), "A-SHEET", lw=0.5)
    P.line((tx0, ty0 + 27), (tx1, ty0 + 27), "A-SHEET", lw=0.5)
    for cx in (tx0 + 120, tx0 + 150):
        P.line((cx, ty0 + 14), (cx, ty1), "A-SHEET", lw=0.5)
    P.text((tx0 + 4, ty0 + 5), "План квартиры (перечерчен по исходному плану)", 3.2, align="ml", style="bold")
    P.text((tx0 + 4, ty0 + 10), "Apartment floor plan - redrawn to scale from the source plan", 2.4, align="ml", style="italic")
    P.text((tx0 + 4, ty0 + 18.5), "Общая площадь / Total area:", 2.2, align="ml")
    P.text((tx0 + 4, ty0 + 23), f"{sum(a for *_, a in ROOMS):.1f} м² (в т.ч. лоджия / incl. loggia 5.3 м²)", 2.2, align="ml", style="bold")
    P.text((tx0 + 135, ty0 + 17.5), "Масштаб / Scale", 1.8)
    P.text((tx0 + 135, ty0 + 23), "1:50", 3.5, style="bold")
    P.text((tx0 + 167.5, ty0 + 17.5), "Формат / Size", 1.8)
    P.text((tx0 + 167.5, ty0 + 23), "A3", 3.5, style="bold")
    P.text((tx0 + 4, ty0 + 31.5), "Размеры в мм / Dimensions in mm", 2.2, align="ml")
    P.text((tx0 + 4, ty0 + 36), "Исходник / Source: floor-plan/source/original-plan.jpg", 1.8, align="ml")
    P.text((tx0 + 135, ty0 + 30.5), "Лист / Sheet", 1.8)
    P.text((tx0 + 135, ty0 + 35.5), "1", 3.0, style="bold")
    P.text((tx0 + 167.5, ty0 + 30.5), "Дата / Date", 1.8)
    P.text((tx0 + 167.5, ty0 + 35.5), "27.09.2026", 2.4)


# --------------------------------------------------------------------------------------
# 6. PDF writer
# --------------------------------------------------------------------------------------
FONT_FILES = {
    "regular": ["LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
    "bold": ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
    "italic": ["LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf"],
}
FONT_DIRS = ["/usr/share/fonts/truetype/liberation", "/usr/share/fonts/truetype/dejavu",
             "/usr/share/fonts/TTF", "C:/Windows/Fonts", "/Library/Fonts"]
CAP = 0.716   # cap height / em for Liberation Sans (Arial metrics)


def register_fonts():
    try:
        import matplotlib
        FONT_DIRS.append(os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data/fonts/ttf"))
    except ImportError:
        pass
    for style, names in FONT_FILES.items():
        for name in names:
            path = next((os.path.join(d, name) for d in FONT_DIRS
                         if os.path.exists(os.path.join(d, name))), None)
            if path:
                pdfmetrics.registerFont(TTFont("plan-" + style, path))
                break
        else:
            sys.exit(f"no TrueType font with Cyrillic found for style {style}")


class PdfWriter:
    def __init__(self, path):
        self.c = rl_canvas.Canvas(path, pagesize=(SHEET_W * mm, SHEET_H * mm))
        self.c.setTitle("Apartment floor plan 1:50 (A3)")
        self.c.setLineCap(0)
        self.c.setLineJoin(0)

    @staticmethod
    def pt(p):  # paper mm (y down) -> PDF points (y up)
        return p[0] * mm, (SHEET_H - p[1]) * mm

    def style(self, layer, lw=None, color=None):
        col, w = LAYERS[layer]
        col = color or col
        self.c.setStrokeColorRGB(*col)
        self.c.setFillColorRGB(*col)
        self.c.setLineWidth((lw if lw is not None else w) * mm)
        self.c.setDash([])

    @staticmethod
    def fillcolor(fill, layer):
        return fill_rgb(fill, layer)

    def draw(self, space, xf):
        c = self.c
        for kind, layer, d in space.items:
            if kind == "region":
                path = c.beginPath()
                for ring in d["rings"]:
                    pts = [self.pt(xf(p)) for p in ring]
                    path.moveTo(*pts[0])
                    for q in pts[1:]:
                        path.lineTo(*q)
                    path.close()
                c.setFillColorRGB(*self.fillcolor(d["fill"], layer))
                c.drawPath(path, stroke=0, fill=1, fillMode=0)
            elif kind in ("poly", "line"):
                pts = d["pts"] if kind == "poly" else [d["a"], d["b"]]
                self.style(layer, d["lw"], d["color"])
                c.setDash([1.5 * mm, 0.8 * mm] if d.get("dash") else [])
                path = c.beginPath()
                q = [self.pt(xf(p)) for p in pts]
                path.moveTo(*q[0])
                for p in q[1:]:
                    path.lineTo(*p)
                if kind == "poly" and d["closed"]:
                    path.close()
                fill = d.get("fill")
                if fill:
                    c.setFillColorRGB(*self.fillcolor(fill, layer))
                c.drawPath(path, stroke=1, fill=1 if fill else 0)
            elif kind == "arc":
                self.style(layer, d["lw"], d["color"])
                n = max(8, int(d["a1"] - d["a0"]))
                pts = [xf((d["c"][0] + d["r"] * math.cos(math.radians(d["a0"] + (d["a1"] - d["a0"]) * k / n)),
                           d["c"][1] + d["r"] * math.sin(math.radians(d["a0"] + (d["a1"] - d["a0"]) * k / n))))
                       for k in range(n + 1)]
                path = c.beginPath()
                q = [self.pt(p) for p in pts]
                path.moveTo(*q[0])
                for p in q[1:]:
                    path.lineTo(*p)
                c.drawPath(path, stroke=1, fill=0)
            elif kind == "circle":
                self.style(layer, d["lw"], d["color"])
                cx, cy = self.pt(xf(d["c"]))
                rad = abs(xf((d["c"][0] + d["r"], d["c"][1]))[0] - xf(d["c"])[0]) * mm
                if d["fill"]:
                    c.setFillColorRGB(*self.fillcolor(d["fill"], layer))
                c.circle(cx, cy, rad, stroke=1, fill=1 if d["fill"] else 0)
            elif kind == "text":
                self.text(xf(d["p"]), d)

    def text(self, p, d):
        c = self.c
        size = d["h"] / CAP * mm
        font = "plan-" + d["style"]
        w = pdfmetrics.stringWidth(d["s"], font, size)
        h = d["h"] * mm
        dx = {"l": 0, "c": -w / 2, "r": -w}[d["align"][1]]
        dy = {"t": -h, "m": -h / 2, "b": 0}[d["align"][0]]
        x, y = self.pt(p)
        c.saveState()
        c.translate(x, y)
        c.rotate(d["rot"])
        c.setFillColorRGB(*(d["color"] or (0, 0, 0)))
        c.setFont(font, size)
        c.drawString(dx, dy, d["s"])
        c.restoreState()

    def dims(self):
        c = self.c
        for d in DIMS:
            a, b = dim_endpoints(d)
            pa, pb = to_paper(*a), to_paper(*b)
            self.style("A-DIMS")
            for p1, p2 in ((pa, pb),):
                path = c.beginPath()
                path.moveTo(*self.pt(p1))
                path.lineTo(*self.pt(p2))
                c.drawPath(path, stroke=1)
            # 1 mm overshoot beyond each tick (architectural style)
            ux, uy = (pb[0] - pa[0]), (pb[1] - pa[1])
            L = math.hypot(ux, uy)
            ux, uy = ux / L, uy / L
            for p, s in ((pa, -1), (pb, 1)):
                path = c.beginPath()
                path.moveTo(*self.pt(p))
                path.lineTo(*self.pt((p[0] + s * ux * 1.0, p[1] + s * uy * 1.0)))
                c.drawPath(path, stroke=1)
            if d["ext_from"]:
                e = to_paper(*d["ext_from"])
                path = c.beginPath()
                path.moveTo(*self.pt(e))
                path.lineTo(*self.pt((pa[0] - 1.0 if pa[0] < e[0] else pa[0] + 1.0, pa[1])))
                c.drawPath(path, stroke=1)
            # 45° ticks, 2.2 mm long, heavier pen
            self.style("A-DIMS", lw=0.35)
            for p in (pa, pb):
                t = 0.78
                path = c.beginPath()
                path.moveTo(*self.pt((p[0] - t, p[1] + t)))
                path.lineTo(*self.pt((p[0] + t, p[1] - t)))
                c.drawPath(path, stroke=1)
            mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            if d["text_at"] is not None:
                a2, _ = dim_endpoints(dict(d, p1=(d["text_at"], d["text_at"])))
                mid = to_paper(*a2)
            txt = str(int(round(L * SCALE)))
            tw = pdfmetrics.stringWidth(txt, "plan-regular", 2.5 / CAP * mm) / mm
            c.setFillColorRGB(1, 1, 1)
            if d["orient"] == "h":
                c.rect(*self.pt((mid[0] - tw / 2 - 0.5, mid[1] - 0.35)), (tw + 1) * mm, 3.3 * mm,
                       stroke=0, fill=1)
                self.text((mid[0], mid[1] - 0.8), dict(s=txt, h=2.5, align="bc", rot=0,
                                                        style="regular", color=None))
            else:
                c.rect(*self.pt((mid[0] - 3.65, mid[1] + tw / 2 + 0.5)), 3.3 * mm, (tw + 1) * mm,
                       stroke=0, fill=1)
                self.text((mid[0] - 0.8, mid[1]), dict(s=txt, h=2.5, align="bc", rot=90,
                                                        style="regular", color=None))

    def save(self):
        self.c.showPage()
        self.c.save()


# --------------------------------------------------------------------------------------
# 7. DXF writer (model space in mm, y up; paper-space layout at 1:50)
# --------------------------------------------------------------------------------------
DXF_OX, DXF_OY = -XMIN, YMAX   # shift so the drawing sits in the positive quadrant


def dxf_xy(p):
    return (p[0] + DXF_OX, DXF_OY - p[1])


def rgb255(col):
    return tuple(int(round(v * 255)) for v in col)


def write_dxf(path):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    for key, font in TEXT_STYLES.items():
        doc.styles.new("PLAN-" + key.upper(), dxfattribs={"font": font})
    for name, (col, lw) in LAYERS.items():
        layer = doc.layers.add(name)
        layer.rgb = rgb255(col)
        layer.dxf.lineweight = int(round(lw * 100)) if lw else 13
    ds = doc.dimstyles.new("PLAN-1-50")
    ds.dxf.dimtxsty = "PLAN-REGULAR"
    ds.dxf.dimscale = SCALE
    ds.dxf.dimtxt = 2.5
    ds.dxf.dimtsz = 1.1          # architectural tick
    ds.dxf.dimdle = 1.0
    ds.dxf.dimexe = 1.0
    ds.dxf.dimexo = 0.0
    ds.dxf.dimgap = 0.8
    ds.dxf.dimtad = 1
    ds.dxf.dimtih = 0
    ds.dxf.dimtoh = 0
    ds.dxf.dimdec = 0
    ds.dxf.dimlunit = 2
    ds.dxf.dimzin = 8
    ds.dxf.dimlwd = 13
    ds.dxf.dimlwe = 13
    ds.dxf.dimtfill = 1          # text background = drawing background

    msp = doc.modelspace()
    write_space(msp, M.items, dxf_xy, SCALE)

    for d in DIMS:
        a, b = dim_endpoints(d)
        base = dxf_xy(a)
        e1 = dxf_xy(d["ext_from"]) if d["ext_from"] else dxf_xy(a)
        e2 = dxf_xy(b)
        ang = 0 if d["orient"] == "h" else 90
        override = {"dimse2": 1} if d["ext_from"] else {"dimse1": 1, "dimse2": 1}
        if d["text_at"] is not None:
            a2, _ = dim_endpoints(dict(d, p1=(d["text_at"], d["text_at"])))
            t = dxf_xy(a2)
            ofs = 0.8 * SCALE + 2.5 * SCALE / 2
            override["dimtmove"] = 2
            text_loc = (t[0], t[1] + ofs) if d["orient"] == "h" else (t[0] - ofs, t[1])
        else:
            text_loc = None
        dim_ent = msp.add_linear_dim(base=base, p1=e1, p2=e2, angle=ang, dimstyle="PLAN-1-50",
                                     override=override, location=text_loc,
                                     dxfattribs={"layer": "A-DIMS"})
        dim_ent.render()

    # paper-space layout "A3 1-50"
    lay = doc.layouts.new("A3 1-50")
    lay.page_setup(size=(SHEET_W, SHEET_H), margins=(0, 0, 0, 0), units="mm", scale=1)
    write_space(lay, P.items, lambda p: (p[0], SHEET_H - p[1]), 1)
    cx, cy = OX + PLAN_W / 2, OY + PLAN_H / 2
    mcx, mcy = (XMIN + XMAX) / 2, (YMIN + YMAX) / 2
    vp = lay.add_viewport(center=(cx, SHEET_H - cy), size=(PLAN_W + 2, PLAN_H + 2),
                          view_center_point=dxf_xy((mcx, mcy)), view_height=(PLAN_H + 2) * SCALE)
    vp_layer = doc.layers.add("A-VPORT")
    vp_layer.dxf.plot = 0
    vp.dxf.layer = "A-VPORT"
    vp.dxf.flags |= 16384  # display locked
    doc.set_modelspace_vport(height=(YMAX - YMIN) * 1.05, center=dxf_xy((mcx, mcy)))
    doc.saveas(path)
    return doc


def fill_rgb(fill, layer):
    if isinstance(fill, tuple):
        return fill
    if fill == "wall":
        return LAYERS["A-WALL-FILL"][0]
    if fill == "glass":
        return GLASS_FILL
    return LAYERS[layer][0]


def solid_hatch(space_obj, layer, fill):
    h = space_obj.add_hatch(dxfattribs={"layer": layer})
    h.set_solid_fill(color=7, rgb=rgb255(fill_rgb(fill, layer)))
    return h


def write_space(space_obj, items, xf, text_scale):
    for kind, layer, d in items:
        attrs = {"layer": layer}
        if d.get("dash"):
            attrs["linetype"] = "DASHED"
            attrs["ltscale"] = 0.06 * text_scale
        if d.get("color") is not None:
            attrs["true_color"] = ezdxf.colors.rgb2int(rgb255(d["color"]))
        if d.get("lw") is not None:
            attrs["lineweight"] = int(round(d["lw"] * 100))
        if kind == "region":
            h = solid_hatch(space_obj, layer, d["fill"])
            for i, ring in enumerate(d["rings"]):
                flags = ezdxf.const.BOUNDARY_PATH_EXTERNAL if i == 0 else ezdxf.const.BOUNDARY_PATH_DEFAULT
                h.paths.add_polyline_path([xf(p) for p in ring], is_closed=True, flags=flags)
        elif kind == "poly":
            space_obj.add_lwpolyline([xf(p) for p in d["pts"]], close=d["closed"], dxfattribs=attrs)
            if d.get("fill"):
                h = solid_hatch(space_obj, layer, d["fill"])
                h.paths.add_polyline_path([xf(p) for p in d["pts"]], is_closed=True)
        elif kind == "line":
            space_obj.add_line(xf(d["a"]), xf(d["b"]), dxfattribs=attrs)
        elif kind == "arc":
            # the working frame has y down: mirror the angles when flipping to y up
            space_obj.add_arc(xf(d["c"]), d["r"], start_angle=-d["a1"], end_angle=-d["a0"],
                              dxfattribs=attrs)
        elif kind == "circle":
            space_obj.add_circle(xf(d["c"]), d["r"], dxfattribs=attrs)
            if d.get("fill"):
                h = solid_hatch(space_obj, layer, d["fill"])
                h.paths.add_edge_path().add_arc(xf(d["c"]), d["r"], 0, 360)
        elif kind == "text":
            align = {"tl": TextEntityAlignment.TOP_LEFT, "tc": TextEntityAlignment.TOP_CENTER,
                     "tr": TextEntityAlignment.TOP_RIGHT, "ml": TextEntityAlignment.MIDDLE_LEFT,
                     "mc": TextEntityAlignment.MIDDLE_CENTER, "mr": TextEntityAlignment.MIDDLE_RIGHT,
                     "bl": TextEntityAlignment.LEFT, "bc": TextEntityAlignment.CENTER,
                     "br": TextEntityAlignment.RIGHT}[d["align"]]
            t = space_obj.add_text(d["s"], height=d["h"] * text_scale, rotation=d["rot"],
                                   dxfattribs={"layer": layer, "style": "PLAN-" + d["style"].upper()})
            t.set_placement(xf(d["p"]), align=align)


# --------------------------------------------------------------------------------------
# 8. Verification of the written files
# --------------------------------------------------------------------------------------
def verify_dxf(path):
    doc = ezdxf.readfile(path)
    got = sorted(round(e.get_measurement()) for e in doc.modelspace().query("DIMENSION"))
    want = sorted(d["expected"] for d in DIMS)
    assert got == want, (got, want)
    print(f"DXF check: {len(got)} DIMENSION entities measure {got}")


def verify_pdf(path):
    import pymupdf as fitz
    pdf = fitz.open(path)
    page = pdf[0]
    w_mm, h_mm = page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4
    assert abs(w_mm - SHEET_W) < 0.01 and abs(h_mm - SHEET_H) < 0.01, (w_mm, h_mm)
    seg = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l":
                a, b = it[1], it[2]
                seg.append(math.hypot(b.x - a.x, b.y - a.y) / 72 * 25.4)
    for d in DIMS:
        target = d["expected"] / SCALE
        assert any(abs(s - target) < 0.005 for s in seg), f"no {target} mm line for {d['expected']}"
    print(f"PDF check: page {w_mm:.2f} x {h_mm:.2f} mm; every dimension line = value / {SCALE} "
          f"on paper (e.g. 4970 mm -> {4970 / SCALE:.2f} mm)")


def main():
    os.makedirs(OUT, exist_ok=True)
    check_dims()
    build_sheet()
    register_fonts()
    pdf_path = os.path.join(OUT, "flat-plan_1-50_A3.pdf")
    w = PdfWriter(pdf_path)
    w.draw(M, lambda p: to_paper(*p))
    w.dims()
    w.draw(P, lambda p: p)
    w.save()
    dxf_path = os.path.join(OUT, "flat-plan_1-50.dxf")
    write_dxf(dxf_path)
    verify_dxf(dxf_path)
    verify_pdf(pdf_path)
    try:
        import pymupdf as fitz
        pix = fitz.open(pdf_path)[0].get_pixmap(dpi=150)
        pix.save(os.path.join(OUT, "flat-plan_1-50_A3.png"))
    except ImportError:
        print("pymupdf not installed - PNG preview skipped")
    print("written:", *sorted(os.listdir(OUT)), sep="\n  ")


if __name__ == "__main__":
    main()
