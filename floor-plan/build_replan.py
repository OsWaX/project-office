#!/usr/bin/env python3
"""Replanning proposal for the apartment, drawn at 1:50 on the same A3 sheet setup.

Builds on build_plan.py (same shell, columns, facade, scale and writers) and changes
interior walls only:
  4   living room  -> two children's rooms (4.1, 4.2), each with its own door; the block's
                      west wall moves west to the column (C1)
  3   bathroom     -> bathroom (3.1, larger) and separate WC (3.2), separate doors
  6   bedroom      -> secret room (~12 m²) reachable only through a hidden bookcase door
                      from the loggia (8); its north part joins the studio
  5   kitchen      -> west wall becomes a glazed partition
  2   corridor     -> studio with a lounge zone and a dining zone

Outputs: output/replan_1-50.dxf, output/replan_1-50_A3.pdf, output/replan_1-50_A3.png
"""

import math
import os

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import build_plan as bp
from build_plan import (DIMS, LAYERS, M, P, SCALE, T, X_FAC, X_HALL, X_BATH_W, X_KIT, X_PART,
                        Y_B1, Y_BATH_N, Y_BATH_S, Y_FAC, Y_HALL, Y_KB, Y_LG, Y_LK, COL_W_FACE,
                        HALL_LO_C, HALL_UP_C, LIV_IN_C, LIV_OUT_C, GLZ,
                        bed, chair, dim, door, ellipse, glazing_band, nightstand,
                        office_chair, r, rrect, shaft, wardrobe)

OUT = bp.OUT
LAYERS["A-WALL-NEW"] = ((0.0, 0.0, 0.0), 0.50)
LAYERS["A-WALL-NEW-FILL"] = ((0.93, 0.55, 0.25), 0.0)
LAYERS["A-WALL-DEMO"] = ((0.35, 0.35, 0.35), 0.25)

# --------------------------------------------------------------------------------------
# 1. New interior layout (same working frame as build_plan.py: x right, y down, mm)
# --------------------------------------------------------------------------------------
X_KIDS_W = 250            # children's block west wall, outer face = east face of column C1
X_KIDS_P = 4100           # partition between the two children's rooms (west face)
Y_KIDS_P = 2000           # partition north face of the passage strip into room 4.2
X_BATH_E = 400            # bathroom east wall, room face (was -200)
WC = (-2100, 1000, -1100, Y_HALL)      # WC clear size 1000 x 1000, taken from the hall corner
Y_SECRET = 9450           # studio / secret-room partition (150 thick)
T_P = 150

walls = [
    r(X_HALL - T, -T, X_FAC, 0),                                   # north wall (existing)
    r(X_HALL - T, -T, X_HALL, Y_BATH_N),                           # hall west wall (existing)
    r(X_HALL - T, Y_HALL, X_HALL + 2900, Y_BATH_N),                # hall south wall (existing)
    Polygon([(X_HALL + 2900, Y_HALL), (X_BATH_E + T, X_BATH_E + T + HALL_UP_C),
             (X_BATH_E + T, X_BATH_E + T + HALL_LO_C), (Y_HALL - HALL_LO_C, Y_HALL)]),  # 45° wall, extended
    r(-T, Y_BATH_S + T, 0, Y_FAC),                                 # west wall below the bathroom (existing)
    r(X_BATH_W - 435, Y_BATH_N, X_BATH_W - 235, 3700),             # bathroom west walls (existing)
    r(X_BATH_W - 235, 3600, X_BATH_W, 3700),
    r(X_BATH_W - 120, 3600, X_BATH_W, Y_BATH_S),
    r(X_BATH_W - 435, Y_BATH_S, X_BATH_E + T, Y_BATH_S + T),        # bathroom south wall, extended east
    r(X_BATH_E, X_BATH_E + T + HALL_UP_C, X_BATH_E + T, Y_BATH_S + T),  # bathroom east wall (new)
    r(WC[0] - 100, WC[1] - 100, WC[0], WC[3]),                     # WC partitions (new)
    r(WC[0] - 100, WC[1] - 100, WC[2] + 100, WC[1]),
    r(WC[2], WC[1] - 100, WC[2] + 100, WC[3]),
    r(X_KIDS_W, 0, X_KIDS_W + T, X_KIDS_W + LIV_OUT_C),            # children's block west wall (new)
    Polygon([(X_KIDS_W, X_KIDS_W + LIV_IN_C), (Y_LK - LIV_IN_C, Y_LK),
             (X_KIT, X_KIT + LIV_OUT_C), (X_KIDS_W, X_KIDS_W + LIV_OUT_C)]),  # 45° wall, extended
    r(X_KIDS_P, 0, X_KIDS_P + 100, Y_KIDS_P + 100),                # partition between the rooms (new)
    r(900, Y_KIDS_P, X_KIDS_P + 100, Y_KIDS_P + 100),
    r(X_KIT, Y_LK, 5500, Y_LK + T),                                # living/kitchen partition (existing)
    r(X_KIT, Y_LK, X_KIT + T, Y_B1),                               # kitchen west wall (glazed below)
    r(X_KIT, Y_KB, X_FAC, Y_KB + T),                               # kitchen / bedroom-7 wall (existing)
    r(X_KIT, Y_B1, X_PART + T, Y_B1 + T),                          # bedroom-7 vestibule south wall
    r(X_PART, Y_B1, X_PART + T, Y_FAC),                            # bedroom partition (existing)
    r(0, Y_SECRET, X_PART, Y_SECRET + T_P),                        # studio / secret-room partition (new)
    r(X_PART + T, Y_LG, 4300, Y_LG + T),                           # bedroom-7 / loggia wall (existing)
    r(5500, 2700, X_FAC, 2700 + T),                                # service niche (existing)
    r(5500, 2700, 5700, 4250),
]

# door of room 4.2 in the 45° wall: 800 mm, measured along the room face
U = (1 / math.sqrt(2), 1 / math.sqrt(2))             # along the wall, towards south-east
N_OUT = (-1 / math.sqrt(2), 1 / math.sqrt(2))        # room face -> corridor face
KD_A = (1233, 1233 + LIV_IN_C)                        # on the room face
KD_B = (KD_A[0] + 800 * U[0], KD_A[1] + 800 * U[1])
DEPTH = T * 1.2
kids2_opening = Polygon([(KD_A[0] - 30 * N_OUT[0], KD_A[1] - 30 * N_OUT[1]),
                         (KD_B[0] - 30 * N_OUT[0], KD_B[1] - 30 * N_OUT[1]),
                         (KD_B[0] + DEPTH * N_OUT[0], KD_B[1] + DEPTH * N_OUT[1]),
                         (KD_A[0] + DEPTH * N_OUT[0], KD_A[1] + DEPTH * N_OUT[1])])

KIT_GLASS = [(3200, 3925), (4825, 6100)]              # glazed parts of the kitchen west wall
openings = [
    r(X_HALL - T, 300, X_HALL, 1300),                  # entrance door (existing)
    r(X_BATH_E, 3950, X_BATH_E + T, Y_BATH_S),         # bathroom door 700
    r(WC[2], 1050, WC[2] + 100, 1700),                 # WC door 650
    r(X_KIDS_W, 500, X_KIDS_W + T, 1300),              # room 4.1 door 800
    kids2_opening,                                     # room 4.2 door 800
    r(X_KIT, 3925, X_KIT + T, 4825),                   # kitchen door 900
    r(2100, Y_B1, X_PART, Y_B1 + T),                   # bedroom-7 door 800 (moved)
    r(X_PART, 12700, X_PART + T, 13500),               # hidden door 800, loggia -> secret room
    r(-T, 12400, 0, 13750),                            # corner glazing (existing)
] + [r(X_KIT, a, X_KIT + T, b) for a, b in KIT_GLASS]

columns = bp.columns
col_union = unary_union(columns)
new_solid = unary_union(walls).difference(unary_union(openings)).difference(col_union)
old_solid = bp.wall_geom


def clean(g, tol=2):
    return g.buffer(-tol, join_style=2).buffer(tol, join_style=2)


kept = clean(new_solid.intersection(old_solid))
added = clean(new_solid.difference(old_solid))
removed = clean(old_solid.difference(new_solid.buffer(1)).difference(unary_union(openings)))

# --------------------------------------------------------------------------------------
# 2. Drawing
# --------------------------------------------------------------------------------------
M.items.clear()
P.items.clear()
DIMS.clear()


def polys(g):
    if g.is_empty:
        return []
    return [g] if g.geom_type == "Polygon" else [p for p in g.geoms if p.geom_type == "Polygon"]


for p in polys(removed):
    if p.area > 5000:
        M.poly(list(p.exterior.coords)[:-1], "A-WALL-DEMO", dash=True)
M.region(kept, "A-WALL-FILL", fill="wall", outline_layer="A-WALL")
M.region(added, "A-WALL-NEW-FILL", fill="solid", outline_layer="A-WALL-NEW")
M.region(col_union, "A-COLS", fill="solid", outline_layer="A-COLS")

# facade and existing glazing (unchanged)
glazing_band(X_FAC, -T, X_FAC + GLZ, Y_FAC + GLZ, vertical=True)
glazing_band(-T, Y_FAC, X_FAC + GLZ, Y_FAC + GLZ, vertical=False)
M.line((X_FAC, -T), (X_FAC + GLZ, -T), "A-GLAZ-FRAME")
M.line((-T, Y_FAC), (-T, Y_FAC + GLZ), "A-GLAZ-FRAME")
for my in (700, 1725, 2750, 3750, 4775, 6800, 7800, 8800, 9825, 10825, 12900):
    M.rect(X_FAC, my - 30, X_FAC + GLZ, my + 30, "A-GLAZ-FRAME", fill="solid")
for mx in (1250, 4300, 5300):
    M.rect(mx - 30, Y_FAC, mx + 30, Y_FAC + GLZ, "A-GLAZ-FRAME", fill="solid")
for gx in (-T, 0):
    M.line((gx, 12400), (gx, 13750), "A-GLAZ-FRAME")
for gx in (-120, -80):
    M.line((gx, 12400), (gx, 13750), "A-GLAZ")
for gy in (Y_LG, Y_LG + T):
    M.line((4300, gy), (5000, gy), "A-GLAZ-FRAME")
for gy in (Y_LG + 80, Y_LG + 120):
    M.line((4300, gy), (5000, gy), "A-GLAZ")
M.line((5000, Y_LG), (5000, Y_LG + T), "A-GLAZ-FRAME")

# (4) kitchen west wall: glazed partition
for a, b in KIT_GLASS:
    for gx in (X_KIT, X_KIT + T):
        M.line((gx, a), (gx, b), "A-GLAZ-FRAME")
    for gx in (X_KIT + 80, X_KIT + 120):
        M.line((gx, a), (gx, b), "A-GLAZ")
    M.line((X_KIT, a), (X_KIT + T, a), "A-GLAZ-FRAME")
    M.line((X_KIT, b), (X_KIT + T, b), "A-GLAZ-FRAME")

# doors
door((X_HALL - T, 300), (X_HALL - T, 1300), (X_HALL - T - 1000, 300))           # entrance
door((X_BATH_E + T, 3950), (X_BATH_E + T, Y_BATH_S), (X_BATH_E + T + 700, 3950))  # bathroom, opens out
door((WC[2] + 100, 1700), (WC[2] + 100, 1050), (WC[2] + 750, 1700))             # WC, opens out
door((X_KIDS_W + T, 1300), (X_KIDS_W + T, 500), (X_KIDS_W + T + 800, 1300))     # room 4.1
door(KD_B, KD_A, (KD_B[0] + 800 * -N_OUT[0], KD_B[1] + 800 * -N_OUT[1]))       # room 4.2
door((X_KIT + T, 3925), (X_KIT + T, 4825), (X_KIT + T + 900, 3925),
     color=LAYERS["A-GLAZ"][0])                                                 # kitchen (glass)
door((2100, Y_B1), (X_PART, Y_B1), (2100, Y_B1 - 800))                          # bedroom 7 (moved)
door((X_PART, 13500), (X_PART, 12700), (X_PART - 800, 13500))                   # hidden bookcase door
door((6100, 4250), (5700, 4250), (6100, 4650))                                  # service niche
door((5750, Y_LG + T), (5000, Y_LG + T), (5750, Y_LG + T + 750), color=LAYERS["A-GLAZ"][0])
M.line((5700, 4250), (6100, 4250), "A-FIXT")

# shafts (unchanged)
shaft(X_BATH_W - 435, 3700, X_BATH_W - 120, Y_BATH_S)
shaft(X_KIT + T, Y_LK + T, 2700, 3700, wall=70)

# --- 1 hall + 3.2 WC -----------------------------------------------------------------------
wardrobe(X_HALL, Y_HALL - 500, WC[0] - 100, Y_HALL)
M.rect(WC[0], 1300, WC[0] + 200, 1700, "A-FIXT")          # WC: cistern on the west partition
ellipse(WC[0] + 450, 1500, 260, 180)
ellipse(WC[0] + 470, 1500, 180, 120)
M.rect(-1450, WC[3] - 230, WC[2], WC[3], "A-FIXT")          # hand basin
ellipse(-1275, WC[3] - 110, 120, 80)

# --- 3.1 bathroom ---------------------------------------------------------------------------
M.rect(X_BATH_W - 235, 2990, -1300, 3010, "A-GLAZ", fill="glass")        # shower screen
M.rect(-1350, 3025, 3025 - HALL_LO_C, 3040, "A-GLAZ")
M.rect(X_BATH_W - 235, 2500, X_BATH_W - 175, 2600, "A-FIXT")
M.line((X_BATH_W - 175, 2550), (-1900, 2550), "A-FIXT")
M.circle((-1850, 2550), 60, "A-FIXT")
M.rect(-1400, 2550, -1300, 2650, "A-FIXT")
M.line((-1400, 2550), (-1300, 2650), "A-FIXT")
M.line((-1400, 2650), (-1300, 2550), "A-FIXT")
M.rect(X_BATH_W - 235, 3100, X_BATH_W - 235 + 480, 3650, "A-FIXT")      # vanity + basin
ellipse(X_BATH_W - 235 + 250, 3375, 150, 210)
rrect(X_BATH_W, Y_BATH_S - 750, X_BATH_W + 1700, Y_BATH_S, 120, "A-FIXT")  # bath tub 1700x750
rrect(X_BATH_W + 80, Y_BATH_S - 670, X_BATH_W + 1620, Y_BATH_S - 80, 250, "A-FIXT")
M.circle((X_BATH_W + 250, Y_BATH_S - 375), 35, "A-FIXT")

# --- 4.1 / 4.2 children's rooms ------------------------------------------------------------------
rrect(1450, 30, 3450, 930, 50)                         # 4.1 single bed 900x2000 along north wall
rrect(1480, 80, 1880, 880, 60)
M.line((2100, 30), (2100, 930), "A-FURN")
wardrobe(X_KIDS_P - 600, 1100, X_KIDS_P, Y_KIDS_P, along_x=False)
M.line((X_KIDS_P - 300, 1150), (X_KIDS_P - 300, Y_KIDS_P - 50), "A-FURN")
M.rect(1500, Y_KIDS_P - 600, 2800, Y_KIDS_P, "A-FURN")    # desk
office_chair(2150, 1150, 90)

rrect(X_KIDS_P + 100, 300, X_KIDS_P + 1000, 2300, 50)  # 4.2 single bed along the partition
rrect(X_KIDS_P + 150, 350, X_KIDS_P + 950, 750, 60)
M.line((X_KIDS_P + 100, 980), (X_KIDS_P + 1000, 980), "A-FURN")
M.rect(5650, 700, X_FAC, 1900, "A-FURN")               # desk at the window
office_chair(5350, 1300, 0)
wardrobe(4400, 2400, 5450, Y_LK)

# --- 5 kitchen (fridge moved off the new glass wall) -----------------------------------------------
M.rect(2700, Y_LK + T, 4900, 3800, "A-FIXT")
rrect(3100, 3260, 3650, 3740, 40, "A-FIXT")
rrect(3150, 3310, 3600, 3690, 60, "A-FIXT")
M.circle((3375, 3500), 35, "A-FIXT")
M.rect(4150, 3250, 4600, 3750, "A-FIXT")
M.circle((4375, 3380), 105, "A-FIXT")
M.circle((4375, 3620), 105, "A-FIXT")
M.rect(4900, Y_LK + T, 5500, 3850, "A-FIXT")           # fridge
for a in (0, 60, 120):
    t = math.radians(a)
    M.line((5200 - 120 * math.cos(t), 3525 - 120 * math.sin(t)),
           (5200 + 120 * math.cos(t), 3525 + 120 * math.sin(t)), "A-FIXT")
M.rect(3750, 5350, 4900, 5950, "A-FURN")
chair(4040, 5110, "down")
chair(4610, 5110, "down")
chair(3500, 5650, "right")
chair(5150, 5650, "left")
M.rect(5800, 2950, 5950, 4150, "A-FIXT")
yy = 3000
while yy < 4100:
    M.line((5800, yy), (5950, yy + 60), "A-FIXT")
    yy += 100

# --- 2 studio: dining zone + lounge zone ---------------------------------------------------------
M.rect(1100, 6550, X_KIT, 7650, "A-FURN")              # dining table 1100 x 750 at the wall
chair(875, 6850, "right")
chair(875, 7350, "right")
chair(1475, 6310, "down")
chair(1475, 7890, "up")
rrect(0, 8050, 850, 9450, 120)                          # sofa along the west wall
M.line((200, 8150), (200, 9350), "A-FURN")
M.line((0, 8250), (850, 8250), "A-FURN")
M.line((0, 9250), (850, 9250), "A-FURN")
rrect(1150, 8450, 1700, 9050, 60)                      # coffee table
M.rect(2500, 8400, X_PART, 9250, "A-FURN")             # TV unit
M.line((2850, 8500), (2850, 9150), "A-FIXT")

# --- 6 secret room ----------------------------------------------------------------------------
M.rect(300, Y_SECRET + T_P, 1700, Y_SECRET + T_P + 700, "A-FURN")    # desk
office_chair(1000, 10700, -90)
rrect(2050, 10300, X_PART, 12300, 90)                 # sofa bed
M.line((2750, 10400), (2750, 12200), "A-FURN")
rrect(600, 12900, 1250, 13550, 120)                   # armchair + side table
M.circle((1600, 13600), 200, "A-FURN")

# --- 7 bedroom (unchanged except door), 8 loggia -------------------------------------------------
wardrobe(4300, 6350, X_FAC, 6950)
bed(X_PART + T, 9225, 5250, 11225, "left")
nightstand(X_PART + T, 8775, 3550, 9175)
nightstand(X_PART + T, 11275, 3550, 11675)
M.rect(X_PART + T, 12450, 3450, 13950, "A-FURN")      # bookcase; its middle part is the hidden door
for yb in range(12450, 13950, 250):
    M.line((X_PART + T, yb), (3450, yb), "A-FURN")
M.circle((5800, 13500), 330, "A-FURN")
for k in range(8):
    t = math.radians(22.5 + 45 * k)
    M.line((5800, 13500), (5800 + 330 * math.cos(t), 13500 + 330 * math.sin(t)), "A-FURN")
M.rect(4650, 13350, 5350, 13900, "A-FURN")            # lounge chair on the loggia

# --------------------------------------------------------------------------------------
# 3. Rooms: areas computed from the drawn geometry
# --------------------------------------------------------------------------------------
ROOMS2 = [  # no, RU, EN, area before (source), label point
    ("1", "Прихожая", "Hall + passage", 5.8, (-2950, 900)),
    ("2", "Гостиная-студия", "Studio", 14.1, (925, 5200)),
    ("3.1", "Ванная", "Bathroom", 4.1, (-750, 3300)),
    ("3.2", "Туалет", "WC", None, (-1520, 1130)),
    ("4.1", "Детская 1", "Child room 1", 14.4, (2300, 1100)),
    ("4.2", "Детская 2", "Child room 2", None, (4800, 1500)),
    ("5", "Кухня", "Kitchen", 11.0, (4150, 4500)),
    ("6", "Секретная комната", "Secret room", 17.8, (1150, 11200)),
    ("7", "Спальня", "Bedroom", 19.7, (4350, 10000)),
    ("8", "Лоджия", "Loggia", 5.3, (5050, 12850)),
]


def room_areas():
    closed = unary_union(walls + columns + [
        LineString([(100, 3150), (1900, 3150)]).buffer(2),     # hall | studio (zone line)
        r(4300, Y_LG, 5750, Y_LG + T),                          # loggia glazing + door
        r(5700, 4240, 6100, 4260),                              # service niche door
        r(X_KIT + T, Y_LK + T, 2700, 3700),                     # kitchen vent shaft
    ])
    free = box(X_HALL - T, -T, X_FAC, Y_FAC).difference(closed)
    areas = {}
    for no, _, _, _, pt in ROOMS2:
        comp = next(g for g in polys(free) if g.contains(Point(pt)))
        areas[no] = comp.area / 1e6
    return areas


AREAS = room_areas()

for no, ru, en, before, (x, y) in ROOMS2:
    if no == "3.2":        # WC is too small for two lines
        M.text((x, y), f"{no} {ru} {AREAS[no]:.1f} м²", 1.6, style="italic")
        continue
    h = {"4.2": 2.2, "2": 2.6, "6": 2.6}.get(no, 3.0)
    M.text((x, y - 160), f"{no}  {ru}", h, style="italic")
    M.text((x, y + 160), f"{AREAS[no]:.1f} м²", h)
M.text((650, 6450), "обеденная зона", 1.8, style="italic")
M.text((1450, 9380), "мягкая зона", 1.8, style="italic")
M.text((3280, 13200), "потайная дверь", 1.6, style="italic", rot=90)
M.text((2180, 5450), "витраж / glazed wall", 1.6, style="italic", rot=90)

# --- dimensions: source values that still apply + new ones --------------------------------------
dim((X_HALL, 250), (COL_W_FACE, 250), "h", 250, 3600)
dim((-3700, 0), (-3700, Y_HALL), "v", -3700, 2000)
dim((X_KIDS_W + T, 1400), (X_KIDS_P, 1400), "h", 1400, X_KIDS_P - X_KIDS_W - T, text_at=3800)
dim((3300, 0), (3300, Y_KIDS_P), "v", 3300, Y_KIDS_P)
dim((X_KIDS_P + 100, 280), (X_FAC, 280), "h", 280, X_FAC - X_KIDS_P - 100, text_at=5600)
dim((5400, 0), (5400, Y_LK), "v", 5400, 3000, text_at=2250)
dim((-1700, Y_BATH_N), (-1700, Y_BATH_S), "v", -1700, 2450)
dim((X_BATH_W, 3850), (X_BATH_E, 3850), "h", 3850, X_BATH_E - X_BATH_W)
dim((0, 5750), (X_KIT, 5750), "h", 5750, 1850)
dim((3025, Y_LK + T), (3025, Y_KB), "v", 3025, 2900)
dim((X_KIT + T, 5750), (X_FAC, 5750), "h", 5750, 4200)
dim((1975, Y_B1 + T), (1975, Y_SECRET), "v", 1975, Y_SECRET - Y_B1 - T)
dim((3600, Y_KB + T), (3600, Y_LG), "v", 3600, 5850, text_at=8200)
dim((X_PART + T, 11750), (X_FAC, 11750), "h", 11750, 3150)
dim((1950, Y_SECRET + T_P), (1950, Y_FAC), "v", 1950, Y_FAC - Y_SECRET - T_P)
dim((0, 11750), (X_PART, 11750), "h", 11750, 2900)
dim((4550, Y_LG + T), (4550, Y_FAC), "v", 4550, 1650)


# --------------------------------------------------------------------------------------
# 4. Sheet
# --------------------------------------------------------------------------------------
def build_sheet():
    x0, y0, x1, y1 = bp.FRAME
    OX, OY = bp.OX, bp.OY
    P.rect(x0, y0, x1, y1, "A-SHEET", lw=0.7)
    P.text((OX, OY - 9), "ПЛАН ПЕРЕПЛАНИРОВКИ  /  REPLANNING PROPOSAL", 4.0, align="ml", style="bold")
    P.text((OX, OY - 4), "М 1:50", 3.0, align="ml")

    sx, sy = bp.to_paper(bp.XMIN, 5400)
    sx += 1
    cols = [0, 8, 34, 58, 72, 86]
    row_h = 6.0
    P.text((sx, sy - 3), "ЭКСПЛИКАЦИЯ / ROOM SCHEDULE", 2.5, align="ml", style="bold")
    total_new = sum(AREAS.values())
    rows = [("№", "Помещение", "Room", "было", "стало")]
    for no, ru, en, before, _ in ROOMS2:
        rows.append((no, ru, en, f"{before:.1f}" if before else "—", f"{AREAS[no]:.1f}"))
    rows.append(("", "Итого", "Total", "92.2", f"{total_new:.1f}"))
    for i, row in enumerate(rows):
        ty = sy + i * row_h
        heavy = i in (0, 1, len(rows) - 1)
        P.line((sx, ty), (sx + cols[-1], ty), "A-SHEET", lw=0.5 if heavy else 0.18)
        bold = i in (0, len(rows) - 1)
        for j, cell in enumerate(row):
            st = "bold" if bold else "regular"
            if j == 0:
                P.text((sx + (cols[0] + cols[1]) / 2, ty + row_h / 2), cell, 1.9, style=st)
            elif j in (3, 4):
                P.text((sx + cols[j + 1] - 1.5, ty + row_h / 2), cell, 1.9, align="mr", style=st)
            else:
                P.text((sx + cols[j] + 1.2, ty + row_h / 2), cell, 1.7 if j == 2 else 1.9,
                       align="ml", style=st)
    bottom = sy + len(rows) * row_h
    P.line((sx, bottom), (sx + cols[-1], bottom), "A-SHEET", lw=0.5)
    for c in cols:
        P.line((sx + c, sy), (sx + c, bottom), "A-SHEET", lw=0.5 if c in (0, cols[-1]) else 0.18)

    notes = [
        ("ПРИМЕЧАНИЯ / NOTES", "bold"),
        ("1. Размеры в мм, М 1:50 при печати A3 100 %.", "regular"),
        ("   Dimensions in mm; 1:50 when printed on A3 at 100 %.", "italic"),
        ("2. Меняются только внутренние перегородки; наружные", "regular"),
        ("   стены, колонны, шахты и фасад - без изменений.", "regular"),
        ("   Interior partitions only; shell, columns, shafts unchanged.", "italic"),
        ("3. «Было» - площади исходного плана, «стало» - по чертежу", "regular"),
        ("   (за вычетом колонн и шахт). / 'Before' = source plan,", "regular"),
        ("   'after' = measured on this drawing, net of columns.", "italic"),
        ("4. Детская 1 без окна: нужен свет с севера или", "regular"),
        ("   стеклянная фрамуга. / Room 4.1 has no window.", "italic"),
        ("5. Проект согласовать до начала работ.", "regular"),
        ("   Approve with the authorities before building.", "italic"),
    ]
    ny = bottom + 8
    for k, (s, st) in enumerate(notes):
        P.text((sx, ny + k * 4.2), s, 1.9, align="ml", style=st)

    ly = ny + len(notes) * 4.2 + 4
    P.text((sx, ly), "УСЛОВНЫЕ ОБОЗНАЧЕНИЯ / LEGEND", 2.1, align="ml", style="bold")
    items = [("wall", "Стена сущ. / Existing wall"), ("new", "Новая перегородка / New partition"),
             ("demo", "Демонтаж / Demolished"), ("col", "Колонна / Column"),
             ("glass", "Остекление / Glazing")]
    for k, (kind, label) in enumerate(items):
        yy = ly + 5 + k * 5
        bx0, by0, bx1, by1 = sx, yy - 1.6, sx + 10, yy + 1.6
        if kind == "wall":
            P.rect(bx0, by0, bx1, by1, "A-WALL", fill="wall", lw=0.35)
        elif kind == "new":
            P.rect(bx0, by0, bx1, by1, "A-WALL-NEW-FILL", fill="solid", lw=0.35, color=(0, 0, 0))
            P.rect(bx0, by0, bx1, by1, "A-WALL-NEW", lw=0.35)
        elif kind == "demo":
            P.rect(bx0, by0, bx1, by1, "A-WALL-DEMO", dash=True)
        elif kind == "col":
            P.rect(bx0, by0, bx1, by1, "A-COLS", fill="solid", lw=0.35)
        else:
            P.line((bx0, by0), (bx1, by0), "A-GLAZ-FRAME")
            P.line((bx0, by1), (bx1, by1), "A-GLAZ-FRAME")
            P.line((bx0, yy - 0.4), (bx1, yy - 0.4), "A-GLAZ")
            P.line((bx0, yy + 0.4), (bx1, yy + 0.4), "A-GLAZ")
        P.text((bx1 + 3, yy), label, 1.9, align="ml")

    bx, by = OX, OY + bp.PLAN_H + 8
    P.text((bx, by - 3.5), "Масштабная линейка / Scale bar 1:50 (м / m)", 2.0, align="ml")
    for k in range(5):
        P.rect(bx + k * 20, by, bx + (k + 1) * 20, by + 1.6, "A-SHEET", lw=0.25,
               fill="solid" if k % 2 == 0 else None)
    for k in range(6):
        P.text((bx + k * 20, by + 4.5), str(k), 2.0)

    tx0, ty0, tx1, ty1 = x1 - 185, y1 - 40, x1, y1
    P.rect(tx0, ty0, tx1, ty1, "A-SHEET", lw=0.7)
    P.line((tx0, ty0 + 14), (tx1, ty0 + 14), "A-SHEET", lw=0.5)
    P.line((tx0, ty0 + 27), (tx1, ty0 + 27), "A-SHEET", lw=0.5)
    for cx in (tx0 + 120, tx0 + 150):
        P.line((cx, ty0 + 14), (cx, ty1), "A-SHEET", lw=0.5)
    P.text((tx0 + 4, ty0 + 5), "План квартиры - вариант перепланировки", 3.2, align="ml", style="bold")
    P.text((tx0 + 4, ty0 + 10), "Apartment floor plan - replanning proposal (interior walls only)",
           2.4, align="ml", style="italic")
    P.text((tx0 + 4, ty0 + 18.5), "Общая площадь / Total area (по чертежу / measured):", 2.2, align="ml")
    P.text((tx0 + 4, ty0 + 23), f"{total_new:.1f} м² (в т.ч. лоджия / incl. loggia {AREAS['8']:.1f} м²)",
           2.2, align="ml", style="bold")
    P.text((tx0 + 135, ty0 + 17.5), "Масштаб / Scale", 1.8)
    P.text((tx0 + 135, ty0 + 23), "1:50", 3.5, style="bold")
    P.text((tx0 + 167.5, ty0 + 17.5), "Формат / Size", 1.8)
    P.text((tx0 + 167.5, ty0 + 23), "A3", 3.5, style="bold")
    P.text((tx0 + 4, ty0 + 31.5), "Размеры в мм / Dimensions in mm", 2.2, align="ml")
    P.text((tx0 + 4, ty0 + 36), "Основа / Base: output/flat-plan_1-50_A3.pdf", 1.8, align="ml")
    P.text((tx0 + 135, ty0 + 30.5), "Лист / Sheet", 1.8)
    P.text((tx0 + 135, ty0 + 35.5), "2", 3.0, style="bold")
    P.text((tx0 + 167.5, ty0 + 30.5), "Дата / Date", 1.8)
    P.text((tx0 + 167.5, ty0 + 35.5), "27.09.2026", 2.4)


def main():
    os.makedirs(OUT, exist_ok=True)
    bp.check_dims()
    build_sheet()
    bp.register_fonts()
    pdf_path = os.path.join(OUT, "replan_1-50_A3.pdf")
    w = bp.PdfWriter(pdf_path)
    w.c.setTitle("Apartment replanning proposal 1:50 (A3)")
    w.draw(M, lambda p: bp.to_paper(*p))
    w.dims()
    w.draw(P, lambda p: p)
    w.save()
    dxf_path = os.path.join(OUT, "replan_1-50.dxf")
    bp.write_dxf(dxf_path)
    bp.verify_dxf(dxf_path)
    bp.verify_pdf(pdf_path)
    import pymupdf
    pymupdf.open(pdf_path)[0].get_pixmap(dpi=150).save(os.path.join(OUT, "replan_1-50_A3.png"))
    for no, ru, en, before, _ in ROOMS2:
        print(f"  {no:4s} {en:26s} {'' if before is None else before:>5} -> {AREAS[no]:.2f} m²")
    print(f"  total {sum(AREAS.values()):.2f} m²")


if __name__ == "__main__":
    main()
