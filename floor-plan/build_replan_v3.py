#!/usr/bin/env python3
"""Replanning variant 3 (sheet 4): the layout sketched by the client over sheet 1.

Walls were read off the client's sketch (drawn on output/flat-plan_1-50_A3.png, so every
sketch pixel maps to 0.21 mm on paper = 10.5 mm at 1:50) and snapped to 50 mm.
Page 1: plan at 1:50 with room dimensions. Page 2: calculation of rooms and walls.

Outputs: output/replan-v3_1-50_A3.pdf (2 pages), output/replan-v3_1-50.dxf,
         output/replan-v3_1-50_A3.png, output/replan-v3_calculation.csv
"""

import csv
import math
import os

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import build_plan as bp
import build_replan as br
from build_plan import (DIMS, LAYERS, M, P, SCALE, T, X_FAC, X_HALL, X_BATH_E, X_BATH_W, X_KIT,
                        X_LIV, X_PART, Y_B1, Y_BATH_N, Y_BATH_S, Y_FAC, Y_HALL, Y_LG, Y_LK,
                        COL_W_FACE, GLZ, HALL_UP_C, HALL_LO_C, LIV_IN_C, LIV_OUT_C, Y_CORNER,
                        bed, chair, dim, door, ellipse, glazing_band, nightstand, office_chair,
                        r, rrect, shaft, Space)
from build_replan import clean, polys

OUT = bp.OUT
Y_KS = 4900          # new kitchen south wall (north face), 200 thick
Y_EN = 6250          # ensuite / wardrobe south partition (north face), 100 thick
X_EW = 4600          # ensuite | wardrobe partition (west face), 100 thick
Y_SEC = 9200         # studio | secret room wall (north face), 200 thick
Y_KSTUB = 3930       # remaining stub of the kitchen west wall ends here

walls = [
    r(X_HALL - T, -T, X_FAC, 0),                                    # north wall
    r(X_HALL - T, -T, X_HALL, Y_BATH_N),                            # hall west wall
    r(X_HALL - T, Y_HALL, X_HALL + 2900, Y_BATH_N),                 # hall south wall
    Polygon([(X_HALL + 2900, Y_HALL), (0, HALL_UP_C), (0, HALL_LO_C),
             (Y_HALL - HALL_LO_C, Y_HALL)]),                         # 45° wall hall -> corridor
    r(X_BATH_E, HALL_UP_C, 0, Y_FAC),                               # west wall
    r(X_BATH_W - 435, Y_BATH_N, X_BATH_W - 235, 3700),              # bathroom (unchanged)
    r(X_BATH_W - 235, 3600, X_BATH_W, 3700),
    r(X_BATH_W - 120, 3600, X_BATH_W, Y_BATH_S),
    r(X_BATH_W - 435, Y_BATH_S, 0, Y_BATH_S + T),
    r(X_LIV - T, 0, X_LIV, LIV_OUT_C + X_LIV - T),                  # living west wall, now closed
    Polygon([(X_LIV - T, X_LIV - T + LIV_IN_C), (Y_LK - LIV_IN_C, Y_LK),
             (X_KIT, Y_CORNER), (X_LIV - T, X_LIV - T + LIV_OUT_C)]),  # 45° wall (door cut in it)
    r(X_KIT, Y_LK, 5500, Y_LK + T),                                 # children | kitchen
    r(X_KIT, Y_LK, X_KIT + T, Y_KSTUB),                             # stub of kitchen west wall
    r(X_PART, Y_KS, X_FAC, Y_KS + T),                               # new kitchen south wall
    r(X_PART, Y_KS, X_PART + T, Y_FAC),                             # bedroom west wall, straight up
    r(X_EW, Y_KS + T, X_EW + 100, Y_EN),                            # ensuite | wardrobe
    r(X_PART + T, Y_EN, 5750, Y_EN + 100),                          # ensuite + wardrobe | bedroom
    r(0, Y_SEC, X_PART, Y_SEC + T),                                 # studio | secret room
    r(X_PART + T, Y_LG, 4300, Y_LG + T),                            # bedroom | loggia (existing)
    r(5500, 2700, X_FAC, 2700 + T),                                 # service niche (existing)
    r(5500, 2700, 5700, 4250),
]

# door in the 45° wall of the children's room, 800 clear, centred on the room face
U = (1 / math.sqrt(2), 1 / math.sqrt(2))
N_OUT = (-1 / math.sqrt(2), 1 / math.sqrt(2))
KD_A = (1355, 1355 + LIV_IN_C)
KD_B = (KD_A[0] + 800 * U[0], KD_A[1] + 800 * U[1])
kids_opening = Polygon([(KD_A[0] - 30 * N_OUT[0], KD_A[1] - 30 * N_OUT[1]),
                        (KD_B[0] - 30 * N_OUT[0], KD_B[1] - 30 * N_OUT[1]),
                        (KD_B[0] + 240 * N_OUT[0], KD_B[1] + 240 * N_OUT[1]),
                        (KD_A[0] + 240 * N_OUT[0], KD_A[1] + 240 * N_OUT[1])])
openings = [
    r(X_HALL - T, 300, X_HALL, 1300),                  # entrance door
    r(X_BATH_E, 3300, 0, 4000),                        # bathroom door (existing)
    kids_opening,                                      # children's room door 800
    r(X_PART, 7100, X_PART + T, 7900),                 # master bedroom door 800
    r(3650, Y_EN, 4350, Y_EN + 100),                   # ensuite door 700
    r(5000, Y_EN, 5700, Y_EN + 100),                   # wardrobe door 700
    r(X_PART, 12750, X_PART + T, 13550),               # hidden door loggia -> secret room
    r(-T, 12400, 0, 13750),                            # corner glazing (existing)
]

columns = bp.columns
col_union = unary_union(columns)
new_solid = unary_union(walls).difference(unary_union(openings)).difference(col_union)
old_solid = bp.wall_geom
kept = clean(new_solid.intersection(old_solid))
added = clean(new_solid.difference(old_solid))
removed = clean(old_solid.difference(new_solid.buffer(1)).difference(unary_union(openings)))

M.items.clear()
P.items.clear()
DIMS.clear()

for p in polys(removed):
    if p.area > 5000:
        M.poly(list(p.exterior.coords)[:-1], "A-WALL-DEMO", dash=True)
M.region(kept, "A-WALL-FILL", fill="wall", outline_layer="A-WALL")
M.region(added, "A-WALL-NEW-FILL", fill="solid", outline_layer="A-WALL-NEW")
M.region(col_union, "A-COLS", fill="solid", outline_layer="A-COLS")

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

GLASS = LAYERS["A-GLAZ"][0]
door((X_HALL - T, 300), (X_HALL - T, 1300), (X_HALL - T - 1000, 300))           # entrance
door((X_BATH_E, 3300), (X_BATH_E, 4000), (X_BATH_E - 700, 3300))               # bathroom
door(KD_B, KD_A, (KD_B[0] - 800 * N_OUT[0], KD_B[1] - 800 * N_OUT[1]))         # children's room
door((X_PART + T, 7900), (X_PART + T, 7100), (X_PART + T + 800, 7900))         # master bedroom
door((4350, Y_EN + 100), (3650, Y_EN + 100), (4350, Y_EN + 800))               # ensuite, opens out
door((5700, Y_EN + 100), (5000, Y_EN + 100), (5700, Y_EN + 800))               # wardrobe, opens out
door((X_PART, 13550), (X_PART, 12750), (X_PART - 800, 13550))                  # hidden door
door((6100, 4250), (5700, 4250), (6100, 4650))                                 # service niche
door((5750, Y_LG + T), (5000, Y_LG + T), (5750, Y_LG + T + 750), color=GLASS)  # loggia
M.line((5700, 4250), (6100, 4250), "A-FIXT")

shaft(X_BATH_W - 435, 3700, X_BATH_W - 120, Y_BATH_S)
shaft(X_KIT + T, Y_LK + T, 2700, 3700, wall=70)

# --- 3 bathroom (unchanged) -----------------------------------------------------------------
M.rect(X_BATH_W - 235, 2990, -1300, 3010, "A-GLAZ", fill="glass")
M.rect(-1350, 3025, 3025 - HALL_LO_C, 3040, "A-GLAZ")
M.rect(X_BATH_W - 235, 2500, X_BATH_W - 175, 2600, "A-FIXT")
M.line((X_BATH_W - 175, 2550), (-1900, 2550), "A-FIXT")
M.circle((-1850, 2550), 60, "A-FIXT")
M.rect(-1600, Y_BATH_S - 200, -1200, Y_BATH_S, "A-FIXT")
ellipse(-1400, 4230, 180, 260)
ellipse(-1400, 4250, 120, 190)
M.rect(-1000, Y_BATH_S - 480, -350, Y_BATH_S, "A-FIXT")
ellipse(-675, Y_BATH_S - 230, 230, 160)

# --- 4 children's room for two: two zones divided by a shelving unit ---------------------------
rrect(1400, 30, 3400, 930, 50)                        # bed 1 (north wall)
rrect(1430, 80, 1830, 880, 60)
M.line((2050, 30), (2050, 930), "A-FURN")
rrect(3900, 280, 5700, 1180, 50)                      # bed 2
rrect(5250, 330, 5650, 1130, 60)
M.line((5050, 280), (5050, 1180), "A-FURN")
M.rect(3550, 0, 3750, 1900, "A-FURN")                 # open shelving as zone divider
for yb in range(200, 1900, 300):
    M.line((3550, yb), (3750, yb), "A-FURN")
M.rect(2300, Y_LK - 600, 3500, Y_LK, "A-FURN")        # desk 1
office_chair(2900, 2150, 90)
M.rect(5650, 1400, X_FAC, 2650, "A-FURN")             # desk 2 at the window
office_chair(5350, 2000, 0)

# --- 5 kitchen (open to the studio) ---------------------------------------------------------
M.rect(2700, Y_LK + T, 5500, 3800, "A-FIXT")
rrect(3100, 3260, 3650, 3740, 40, "A-FIXT")
rrect(3150, 3310, 3600, 3690, 60, "A-FIXT")
M.circle((3375, 3500), 35, "A-FIXT")
M.rect(4150, 3250, 4600, 3750, "A-FIXT")
M.circle((4375, 3380), 105, "A-FIXT")
M.circle((4375, 3620), 105, "A-FIXT")
M.rect(4900, Y_LK + T, 5500, 3850, "A-FIXT")          # fridge
for a in (0, 60, 120):
    t = math.radians(a)
    M.line((5200 - 120 * math.cos(t), 3525 - 120 * math.sin(t)),
           (5200 + 120 * math.cos(t), 3525 + 120 * math.sin(t)), "A-FIXT")
M.rect(3200, 4300, 4300, 4900, "A-FIXT")              # breakfast bar on the new wall
M.rect(5800, 2950, 5950, 4150, "A-FIXT")
yy = 3000
while yy < 4100:
    M.line((5800, yy), (5950, yy + 60), "A-FIXT")
    yy += 100

# --- 2 studio: dining zone + lounge zone ------------------------------------------------------
M.rect(400, 5400, 1750, 6300, "A-FURN")               # dining table 1350 x 900, 4-6 seats
for cx in (750, 1400):
    chair(cx, 5160, "down")
    chair(cx, 6540, "up")
rrect(0, 7300, 900, 9150, 120)                         # sofa on the west wall
M.line((200, 7400), (200, 9050), "A-FURN")
M.line((0, 7500), (900, 7500), "A-FURN")
M.line((0, 8950), (900, 8950), "A-FURN")
rrect(1200, 7900, 1800, 8600, 60)                      # coffee table
M.rect(2500, 8100, X_PART, Y_SEC, "A-FURN")            # TV unit
M.line((2850, 8200), (2850, 9100), "A-FIXT")

# --- 7 master suite ------------------------------------------------------------------------
bed(X_PART + T, 9225, 5250, 11225, "left")
nightstand(X_PART + T, 8775, 3550, 9175)
nightstand(X_PART + T, 11275, 3550, 11675)
rrect(5350, 7300, 6100, 8050, 150)                     # armchair
M.rect(5750, 9000, X_FAC, 11000, "A-FURN")             # dresser / TV at the window
M.rect(X_PART + T, Y_KS + T, 3300, 5900, "A-FIXT")     # ensuite: WC on the west wall
ellipse(3550, 5700, 250, 170)
M.rect(3300, Y_KS + T, 3800, 5500, "A-FIXT")           # basin
ellipse(3550, 5330, 170, 110)
M.rect(3900, Y_KS + T, X_EW, 5850, "A-GLAZ")           # shower 700 x 650
M.line((3900, 5850), (X_EW, Y_KS + T), "A-FIXT")
M.rect(X_EW + 100, Y_KS + T, X_FAC, 5600, "A-FURN")    # wardrobe: shelving north + west
M.rect(X_EW + 100, 5600, 5000, Y_EN, "A-FURN")
M.line((X_EW + 150, 5350), (X_FAC - 50, 5350), "A-FURN")

# --- 6 secret PC & cinema room, 8 loggia --------------------------------------------------------
M.rect(400, Y_SEC + T, 2500, Y_SEC + T + 60, "A-FIXT")   # screen
for sx in (250, 2650):
    M.rect(sx - 120, Y_SEC + T + 40, sx + 120, Y_SEC + T + 280, "A-FIXT")
for cx in (750, 1450, 2150):
    rrect(cx - 330, 11300, cx + 330, 12200, 100)
    M.line((cx - 330, 12000), (cx + 330, 12000), "A-FURN")
M.rect(1300, 12400, 1600, 12600, "A-FIXT")              # projector
M.rect(300, 13300, 1900, Y_FAC - 50, "A-FURN")          # PC desk
for mx0 in (500, 1150):
    M.line((mx0, 13820), (mx0 + 500, 13820), "A-FIXT")
office_chair(1100, 12950, 90)
M.rect(X_PART + T, 12500, 3450, 13950, "A-FURN")        # bookcase = hidden door on the loggia side
for yb in range(12500, 13950, 250):
    M.line((X_PART + T, yb), (3450, yb), "A-FURN")
M.circle((5800, 13500), 330, "A-FURN")
M.rect(4650, 13350, 5350, 13900, "A-FURN")

# --- rooms --------------------------------------------------------------------------------
ROOMS4 = [  # no, RU, EN, before (source), label point
    ("1", "Прихожая", "Entrance hall", 5.8, (-2450, 1000)),
    ("2", "Студия", "Studio (lounge + dining)", 14.1, (1250, 4450)),
    ("3", "С/У", "Bathroom / WC", 4.1, (-1250, 3550)),
    ("4", "Детская для двоих", "Children's room (two)", 14.4, (4550, 2050)),
    ("5", "Кухня (открытая)", "Kitchen (open plan)", 11.0, (5000, 4480)),
    ("6", "ПК и кинотеатр", "PC + home cinema (hidden)", 17.8, (1450, 10500)),
    ("7", "Мастер-спальня", "Master bedroom", 19.7, (4750, 8350)),
    ("7.1", "Санузел", "En-suite shower room", None, (3700, 6000)),
    ("7.2", "Гардероб", "Walk-in wardrobe", None, (5380, 5870)),
    ("8", "Лоджия", "Loggia", 5.3, (5050, 12850)),
]


def room_polys():
    closed = unary_union(walls + columns + [
        LineString([(X_HALL + 2900, -10), (X_HALL + 2900, Y_HALL + 10)]).buffer(2),  # hall | studio
        LineString([(X_KIT + T, Y_KSTUB - 10), (X_KIT + T, Y_KS),
                    (X_PART + 10, Y_KS)]).buffer(2),                                # kitchen | studio
        r(4300, Y_LG, 5750, Y_LG + T),
        r(5700, 4240, 6100, 4260),
        r(X_KIT + T, Y_LK + T, 2700, 3700),
    ])
    free = box(X_HALL - T, -T, X_FAC, Y_FAC).difference(closed)
    return {no: next(g for g in polys(free) if g.contains(Point(pt))) for no, *_, pt in ROOMS4}


RP = room_polys()
AREAS = {k: v.area / 1e6 for k, v in RP.items()}
SIZE = {"2": 2.8, "4": 2.6, "5": 2.3, "6": 2.6, "7": 2.6, "7.2": 1.6, "3": 2.6}
for no, ru, en, before, (x, y) in ROOMS4:
    if no == "7.1":
        M.text((x, y), f"{no} {ru} {AREAS[no]:.1f} м²", 1.6, style="italic")
        continue
    h = SIZE.get(no, 3.0)
    M.text((x, y - 160 * h / 3), f"{no}  {ru}", h, style="italic")
    M.text((x, y + 160 * h / 3), f"{AREAS[no]:.1f} м²", h)
M.text((2400, 5600), "обеденная", 1.6, style="italic")
M.text((2400, 5750), "зона", 1.6, style="italic")
M.text((1450, 9050), "мягкая зона", 1.8, style="italic")
M.text((1450, Y_SEC + T + 180), "экран / screen", 1.6, style="italic")
M.text((3280, 13250), "потайная дверь", 1.6, style="italic", rot=90)

# --- dimensions ------------------------------------------------------------------------------
dim((X_HALL, 250), (COL_W_FACE, 250), "h", 250, 3600)
dim((X_HALL + 2900, 0), (X_HALL + 2900, Y_HALL), "v", X_HALL + 2900, 2000)
dim((X_LIV, 375), (X_FAC, 375), "h", 375, 4970)
dim((5400, 0), (5400, Y_LK), "v", 5400, 3000, text_at=2250)
dim((-1700, Y_BATH_N), (-1700, Y_BATH_S), "v", -1700, 2450)
dim((X_BATH_W, 4380), (X_BATH_E, 4380), "h", 4380, 1665)
dim((0, 3500), (X_KIT, 3500), "h", 3500, 1850)
dim((0, 6900), (X_PART, 6900), "h", 6900, X_PART)
dim((X_KIT + T, 3900), (5500, 3900), "h", 3900, 5500 - X_KIT - T, text_at=2700)
dim((3050 + 150, Y_LK + T), (3200, Y_KS), "v", 3200, Y_KS - Y_LK - T, text_at=4550)
dim((X_PART + T, 5250), (X_EW, 5250), "h", 5250, X_EW - X_PART - T, text_at=3550)
dim((4450, Y_KS + T), (4450, Y_EN), "v", 4450, Y_EN - Y_KS - T, text_at=5980)
dim((X_EW + 100, 5650), (X_FAC, 5650), "h", 5650, X_FAC - X_EW - 100, text_at=5400)
dim((X_PART + T, 11750), (X_FAC, 11750), "h", 11750, 3150)
dim((3600, Y_EN + 100), (3600, Y_LG), "v", 3600, Y_LG - Y_EN - 100, text_at=8400)
dim((0, 10300), (X_PART, 10300), "h", 10300, 2900)
dim((2750, Y_SEC + T), (2750, Y_FAC), "v", 2750, Y_FAC - Y_SEC - T, text_at=10900)
dim((4550, Y_LG + T), (4550, Y_FAC), "v", 4550, 1650)


# --------------------------------------------------------------------------------------
# Calculation: rooms and walls
# --------------------------------------------------------------------------------------
# explicit wall lists (length, thickness in mm), taken from the geometry above
NEW_WALLS = [
    ("Заделка двери гостиной / infill of old living-room door", 1850 - 650, T),
    ("Южная стена кухни / kitchen south wall", X_FAC - X_PART, T),
    ("Западная стена спальни (новые участки) / master-bedroom west wall (new parts)",
     (6100 - (Y_KS + T)) + (7100 - 6300), T),
    ("Санузел | гардероб / en-suite | wardrobe", Y_EN - Y_KS - T, 100),
    ("Санузел, гардероб | спальня (без 2 дверей) / en-suite + wardrobe | bedroom (less 2 doors)",
     5750 - X_PART - T - 700 - 700, 100),
    ("Студия | секретная комната / studio | secret room", X_PART, T),
]
DEMO_WALLS = [
    ("Западная стена кухни (ниже проёма) / kitchen west wall below the door", 6450 - 4825, T),
    ("Кухня | спальня 7, западная часть / kitchen | bedroom 7, west part", X_PART - X_KIT - T, T),
    ("Кухня | спальня 7, восточная часть / kitchen | bedroom 7, east part", 5750 - X_PART - T, T),
    ("Откос бывшей двери спальни 7 / jamb of old bedroom-7 door", Y_B1 - 7350, T),
    ("Коридор | спальня 6 / corridor | bedroom 6", 300 + (X_PART - 1200), T),
    ("Проём в стене у новой двери спальни / cut for new bedroom door", 7900 - Y_B1, T),
    ("Проём в 45° стене детской / cut for children's-room door", 800, T),
]


def perimeter_m(p):
    return p.exterior.length / 1000


def page2(S):
    x0, y0, x1, y1 = bp.FRAME
    S.rect(x0, y0, x1, y1, "A-SHEET", lw=0.7)
    S.text((x0 + 8, 18), "КАЛЬКУЛЯЦИЯ ПОМЕЩЕНИЙ И СТЕН  /  ROOMS & WALLS CALCULATION", 4.0,
           align="ml", style="bold")
    S.text((x0 + 8, 24), "Вариант 3 (по эскизу заказчика), лист 4 - все размеры сняты с плана М 1:50, мм",
           2.4, align="ml", style="italic")

    def table(ty, title, head, cols, rows, total=None, fs=2.1):
        S.text((x0 + 8, ty - 3.5), title, 2.8, align="ml", style="bold")
        tx = x0 + 8
        allrows = [head] + rows + ([total] if total else [])
        rh = 6.2
        for i, row in enumerate(allrows):
            yy = ty + i * rh
            heavy = i in (0, 1) or (total and i == len(allrows) - 1)
            S.line((tx, yy), (tx + cols[-1], yy), "A-SHEET", lw=0.5 if heavy else 0.15)
            bold = i == 0 or (total and i == len(allrows) - 1)
            for j, cell in enumerate(row):
                num = j > 0 and isinstance(cell, str) and cell.replace(".", "").replace("×", "").replace(" ", "").replace("—", "").isdigit()
                if num and j >= 3:
                    S.text((tx + cols[j + 1] - 1.5, yy + rh / 2), cell, fs, align="mr",
                           style="bold" if bold else "regular")
                else:
                    S.text((tx + cols[j] + 1.2, yy + rh / 2), cell, fs, align="ml",
                           style="bold" if bold else "regular")
        yb = ty + len(allrows) * rh
        S.line((tx, yb), (tx + cols[-1], yb), "A-SHEET", lw=0.5)
        for c in cols:
            S.line((tx + c, ty), (tx + c, yb), "A-SHEET", lw=0.5 if c in (0, cols[-1]) else 0.15)
        return yb

    # rooms
    rows = []
    for no, ru, en, before, _ in ROOMS4:
        p = RP[no]
        bx0, by0, bx1, by1 = p.bounds
        rows.append([no, ru, en, f"{round((bx1 - bx0) / 10) * 10:.0f} × {round((by1 - by0) / 10) * 10:.0f}",
                     f"{AREAS[no]:.2f}", f"{perimeter_m(p):.2f}",
                     f"{before:.1f}" if before else "—"])
    tot = sum(AREAS.values())
    yb = table(38, "1. Помещения / Rooms",
               ["№", "Помещение", "Room", "Габарит, мм", "S, м²", "P, м", "Было, м²"],
               [0, 9, 49, 99, 131, 150, 167, 186 + 0], rows,
               ["", "Итого / Total", "", "", f"{tot:.2f}", "", "92.2"])
    S.text((x0 + 8, yb + 4), "Габарит - наибольшие размеры помещения в свету; S - площадь пола по чертежу "
           "(без колонн, шахт, стен); P - периметр пола (для плинтуса).", 1.9, align="ml", style="italic")
    S.text((x0 + 8, yb + 8), "Width x length = clear overall size; S = floor area on this drawing (net of "
           "columns, shafts, walls); P = floor perimeter (skirting).", 1.9, align="ml", style="italic")

    # new walls
    rows = []
    for k, (n, L, t) in enumerate(NEW_WALLS, 1):
        rows.append([str(k), n, f"{L:.0f}", f"{t:.0f}", f"{L * t / 1e6:.3f}", f"{L / 1000:.2f}"])
    totL = sum(w[1] for w in NEW_WALLS) / 1000
    yb2 = table(yb + 20, "2. Новые стены и перегородки / New walls & partitions",
                ["№", "Элемент / Element", "Длина, мм", "Толщ., мм", "S сеч., м²", "п.м"],
                [0, 9, 150, 176, 198, 222, 244], rows,
                ["", "Итого / Total", "", "", f"{sum(w[1] * w[2] for w in NEW_WALLS) / 1e6:.3f}", f"{totL:.2f}"])
    S.text((x0 + 8, yb2 + 4), "Площадь стены под отделку/кладку = длина × высота потолка (с каждой стороны). "
           "Wall face area = length × ceiling height (per side).", 1.9, align="ml", style="italic")

    rows = []
    for k, (n, L, t) in enumerate(DEMO_WALLS, 1):
        rows.append([str(k), n, f"{L:.0f}", f"{t:.0f}", f"{L * t / 1e6:.3f}", f"{L / 1000:.2f}"])
    totD = sum(w[1] for w in DEMO_WALLS) / 1000
    yb3 = table(yb2 + 18, "3. Демонтаж / Demolition",
                ["№", "Элемент / Element", "Длина, мм", "Толщ., мм", "S сеч., м²", "п.м"],
                [0, 9, 150, 176, 198, 222, 244], rows,
                ["", "Итого / Total", "", "", f"{sum(w[1] * w[2] for w in DEMO_WALLS) / 1e6:.3f}", f"{totD:.2f}"])

    doors = [("Детская (в 45° стене)", "Children's room (45° wall)", 800),
             ("Мастер-спальня (из студии)", "Master bedroom (from studio)", 800),
             ("Санузел при спальне", "En-suite", 700),
             ("Гардероб", "Walk-in wardrobe", 700),
             ("Потайная дверь-стеллаж (из лоджии)", "Hidden bookcase door (from loggia)", 800)]
    rows = [[str(k), ru, en, str(w)] for k, (ru, en, w) in enumerate(doors, 1)]
    yb4 = table(yb3 + 18, "4. Новые дверные проёмы / New door openings (ширина в свету / clear width, мм)",
                ["№", "Проём", "Opening", "Ширина"], [0, 9, 99, 199, 222], rows)
    notes = [
        "Стены сняты с эскиза заказчика (1 px эскиза = 10,5 мм) и округлены до 50 мм; толщина новых стен 200/100 мм.",
        "Walls read from the client's sketch (1 sketch px = 10.5 mm) and rounded to 50 mm; new walls 200 / 100 mm.",
        "Санузел 7.1 далеко от стояков - нужен трап/насос и согласование. / En-suite is far from the risers: pump + approval.",
        "Перепланировку согласовать до начала работ. / Approve the replanning with the authorities before building.",
    ]
    for k, s in enumerate(notes):
        S.text((x0 + 8, yb4 + 6 + k * 4.5), s, 2.0, align="ml", style="italic" if k % 2 else "regular")

    tx0, ty0, tx1, ty1 = x1 - 185, y1 - 20, x1, y1
    S.rect(tx0, ty0, tx1, ty1, "A-SHEET", lw=0.7)
    S.text((tx0 + 4, ty0 + 6), "Калькуляция к листу 4 (перепланировка, вариант 3)", 3.0, align="ml", style="bold")
    S.text((tx0 + 4, ty0 + 13), "Calculation for sheet 4 (replanning, variant 3) - 27.09.2026", 2.2,
           align="ml", style="italic")


def write_csv(path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Помещения / Rooms"])
        w.writerow(["№", "Помещение", "Room", "Ширина, мм", "Длина, мм", "S, м²", "P, м", "Было, м²"])
        for no, ru, en, before, _ in ROOMS4:
            bx0, by0, bx1, by1 = RP[no].bounds
            w.writerow([no, ru, en, round((bx1 - bx0) / 10) * 10, round((by1 - by0) / 10) * 10, f"{AREAS[no]:.2f}",
                        f"{perimeter_m(RP[no]):.2f}", before if before else ""])
        w.writerow([])
        w.writerow(["Новые стены / New walls"])
        w.writerow(["№", "Элемент", "Длина, мм", "Толщина, мм", "S сечения, м²"])
        for k, (n, L, t) in enumerate(NEW_WALLS, 1):
            w.writerow([k, n, round(L), round(t), f"{L * t / 1e6:.3f}"])
        w.writerow([])
        w.writerow(["Демонтаж / Demolition"])
        w.writerow(["№", "Элемент", "Длина, мм", "Толщина, мм", "S сечения, м²"])
        for k, (n, L, t) in enumerate(DEMO_WALLS, 1):
            w.writerow([k, n, round(L), round(t), f"{L * t / 1e6:.3f}"])


NOTES = [
    ("ПРИМЕЧАНИЯ / NOTES", "bold"),
    ("1. Размеры в мм, М 1:50 при печати A3 100 %.", "regular"),
    ("   Dimensions in mm; 1:50 when printed on A3 at 100 %.", "italic"),
    ("2. Планировка по эскизу заказчика; меняются только", "regular"),
    ("   внутренние стены. / Client's sketch; interior walls only.", "italic"),
    ("3. «Стало» - площади по чертежу (без колонн и шахт).", "regular"),
    ("   'After' = measured on this drawing, net of columns.", "italic"),
    ("4. Калькуляция помещений и стен - лист 2 этого PDF.", "regular"),
    ("   Room & wall calculation: page 2 of this PDF.", "italic"),
    ("5. Проект согласовать до начала работ.", "regular"),
    ("   Approve with the authorities before building.", "italic"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    bp.check_dims()
    br.build_sheet(ROOMS4, AREAS, NOTES, sheet="4",
                   title_ru="План квартиры - перепланировка, вариант 3",
                   title_en="Apartment floor plan - replanning variant 3 (client's sketch)",
                   header="ПЕРЕПЛАНИРОВКА, ВАРИАНТ 3  /  REPLANNING, VARIANT 3")
    bp.register_fonts()
    pdf_path = os.path.join(OUT, "replan-v3_1-50_A3.pdf")
    w = bp.PdfWriter(pdf_path)
    w.c.setTitle("Apartment replanning variant 3, 1:50 (A3) + calculation")
    w.draw(M, lambda p: bp.to_paper(*p))
    w.dims()
    w.draw(P, lambda p: p)
    w.c.showPage()
    S = Space()
    page2(S)
    w.draw(S, lambda p: p)
    w.save()
    dxf_path = os.path.join(OUT, "replan-v3_1-50.dxf")
    bp.write_dxf(dxf_path)
    bp.verify_dxf(dxf_path)
    bp.verify_pdf(pdf_path)
    write_csv(os.path.join(OUT, "replan-v3_calculation.csv"))
    import pymupdf
    doc = pymupdf.open(pdf_path)
    doc[0].get_pixmap(dpi=150).save(os.path.join(OUT, "replan-v3_1-50_A3.png"))
    doc[1].get_pixmap(dpi=150).save(os.path.join(OUT, "replan-v3_calculation.png"))
    for no, ru, en, before, _ in ROOMS4:
        print(f"  {no:4s} {en:28s} {AREAS[no]:6.2f} m²  P {perimeter_m(RP[no]):.2f} m")
    print("new walls:", [(n[:25], L, t) for n, L, t in NEW_WALLS], sum(w[1] for w in NEW_WALLS))
    print("demolition:", [(n[:25], L, t) for n, L, t in DEMO_WALLS], sum(w[1] for w in DEMO_WALLS))


if __name__ == "__main__":
    main()
