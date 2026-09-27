#!/usr/bin/env python3
"""Replanning proposal, variant 2 (sheet 3), drawn at 1:50 on the same A3 setup.

Interior walls only, shell/columns/shafts/facade as on sheet 1:
  4  living room  -> children's rooms: 4.1 daughter, 4.2 son, separate rooms and doors
  3  bathroom     -> bathroom (3.1) with a square north-east corner + separate WC (3.2)
  6  bedroom      -> hidden PC & home-cinema room (~12.4 m²), door only from the loggia (8)
  5  kitchen      -> glazed west wall; the south wall now stops at bedroom 7's west wall
  7  bedroom      -> master bedroom; its west wall runs straight up to the kitchen wall,
                    door moved onto that wall (entered from the studio)
  2  corridor     -> studio with dining zone + lounge zone (with the north part of room 6)

Outputs: output/replan-v2_1-50.dxf, output/replan-v2_1-50_A3.pdf, output/replan-v2_1-50_A3.png
"""

import math
import os

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

import build_plan as bp
import build_replan as br
from build_plan import (DIMS, LAYERS, M, P, T, X_FAC, X_HALL, X_BATH_W, X_KIT, X_PART,
                        Y_B1, Y_BATH_N, Y_BATH_S, Y_FAC, Y_HALL, Y_KB, Y_LG, Y_LK, COL_W_FACE, GLZ,
                        bed, chair, dim, door, ellipse, glazing_band, nightstand,
                        office_chair, r, rrect, shaft, wardrobe)
from build_replan import clean, polys

OUT = bp.OUT
X_KW = 900           # children's block west wall, passage face (passage 0..900 = 900 clear)
X_KP = 4400          # partition daughter | son (west face)
Y_KP = 2000          # partition daughter | son's entry strip (north face)
WC = (-2100, 1000, -1100, Y_HALL)
Y_SECRET = 9450
T_P = 150
KIT_GLASS = [(3200, 3925), (4825, 7350)]

walls = [
    r(X_HALL - T, -T, X_FAC, 0),                              # north wall
    r(X_HALL - T, -T, X_HALL, Y_BATH_N),                      # hall west wall
    r(X_HALL - T, Y_HALL, 0, Y_BATH_N),                       # hall south wall, now straight to x = 0
    r(-T, Y_HALL, 0, Y_FAC),                                  # bathroom east / corridor west wall, straight
    r(X_BATH_W - 435, Y_BATH_N, X_BATH_W - 235, 3700),        # bathroom west walls (existing)
    r(X_BATH_W - 235, 3600, X_BATH_W, 3700),
    r(X_BATH_W - 120, 3600, X_BATH_W, Y_BATH_S),
    r(X_BATH_W - 435, Y_BATH_S, 0, Y_BATH_S + T),              # bathroom south wall (existing)
    r(WC[0] - 100, WC[1] - 100, WC[0], WC[3]),                # WC partitions
    r(WC[0] - 100, WC[1] - 100, WC[2] + 100, WC[1]),
    r(WC[2], WC[1] - 100, WC[2] + 100, WC[3]),
    r(X_KW, 0, X_KW + T, Y_LK + T),                           # children's block west wall
    r(X_KW, Y_LK, 5500, Y_LK + T),                            # children | kitchen / corridor
    r(X_KP, 0, X_KP + 100, Y_KP + 100),                       # daughter | son
    r(X_KW + T, Y_KP, X_KP + 100, Y_KP + 100),                # daughter | son's entry strip
    r(X_KIT, Y_LK, X_KIT + T, Y_B1),                          # kitchen west wall (glazed)
    r(X_PART, Y_KB, X_FAC, Y_KB + T),                         # kitchen south wall, from bedroom 7 wall only
    r(X_PART, Y_KB, X_PART + T, Y_FAC),                       # bedroom 7 west wall, straight to kitchen
    r(X_KIT, Y_B1, X_PART, Y_B1 + T),                         # kitchen nook | studio
    r(0, Y_SECRET, X_PART, Y_SECRET + T_P),                   # studio | PC & cinema room
    r(X_PART + T, Y_LG, 4300, Y_LG + T),                      # bedroom 7 | loggia (existing)
    r(5500, 2700, X_FAC, 2700 + T),                           # service niche (existing)
    r(5500, 2700, 5700, 4250),
]
openings = [
    r(X_HALL - T, 300, X_HALL, 1300),                  # entrance door
    r(-T, 3300, 0, 4000),                              # bathroom door 700 (existing position)
    r(WC[2], 1050, WC[2] + 100, 1700),                 # WC door 650
    r(X_KW, 300, X_KW + T, 1100),                      # daughter's door 800
    r(X_KW, 2150, X_KW + T, 2950),                     # son's door 800
    r(X_KIT, 3925, X_KIT + T, 4825),                   # kitchen glass door 900
    r(X_PART, 7750, X_PART + T, 8550),                 # master bedroom door 800 (from the studio)
    r(X_PART, 12700, X_PART + T, 13500),               # hidden bookcase door, loggia -> room 6
    r(-T, 12400, 0, 13750),                            # corner glazing (existing)
] + [r(X_KIT, a, X_KIT + T, b) for a, b in KIT_GLASS]

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

# --- facade and existing glazing (unchanged) --------------------------------------------------
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

# kitchen west wall: glazed partition ("window wall")
for a, b in KIT_GLASS:
    for gx in (X_KIT, X_KIT + T):
        M.line((gx, a), (gx, b), "A-GLAZ-FRAME")
    for gx in (X_KIT + 80, X_KIT + 120):
        M.line((gx, a), (gx, b), "A-GLAZ")
    M.line((X_KIT, a), (X_KIT + T, a), "A-GLAZ-FRAME")
    M.line((X_KIT, b), (X_KIT + T, b), "A-GLAZ-FRAME")

# --- doors ------------------------------------------------------------------------------------
GLASS = LAYERS["A-GLAZ"][0]
door((X_HALL - T, 300), (X_HALL - T, 1300), (X_HALL - T - 1000, 300))        # entrance
door((-T, 3300), (-T, 4000), (-T - 700, 3300))                              # bathroom
door((WC[2] + 100, 1700), (WC[2] + 100, 1050), (WC[2] + 750, 1700))         # WC, opens out
door((X_KW + T, 1100), (X_KW + T, 300), (X_KW + T + 800, 1100))             # daughter
door((X_KW + T, 2150), (X_KW + T, 2950), (X_KW + T + 800, 2150))            # son
door((X_KIT + T, 3925), (X_KIT + T, 4825), (X_KIT + T + 900, 3925), color=GLASS)  # kitchen
door((X_PART + T, 8550), (X_PART + T, 7750), (X_PART + T + 800, 8550))      # master bedroom
door((X_PART, 13500), (X_PART, 12700), (X_PART - 800, 13500))               # hidden door
door((6100, 4250), (5700, 4250), (6100, 4650))                              # service niche
door((5750, Y_LG + T), (5000, Y_LG + T), (5750, Y_LG + T + 750), color=GLASS)
M.line((5700, 4250), (6100, 4250), "A-FIXT")

shaft(X_BATH_W - 435, 3700, X_BATH_W - 120, Y_BATH_S)
shaft(X_KIT + T, Y_LK + T, 2700, 3700, wall=70)

# --- 1 hall, 3.2 WC -----------------------------------------------------------------------
wardrobe(X_HALL, Y_HALL - 500, WC[0] - 100, Y_HALL)
M.rect(WC[0], 1300, WC[0] + 200, 1700, "A-FIXT")
ellipse(WC[0] + 450, 1500, 260, 180)
ellipse(WC[0] + 470, 1500, 180, 120)
M.rect(-1450, WC[3] - 230, WC[2], WC[3], "A-FIXT")
ellipse(-1275, WC[3] - 110, 120, 80)

# --- 3.1 bathroom (rectangular now) -----------------------------------------------------------
rrect(X_BATH_W - 235, Y_BATH_N, X_BATH_W - 235 + 1700, Y_BATH_N + 750, 120, "A-FIXT")   # tub
rrect(X_BATH_W - 155, Y_BATH_N + 80, X_BATH_W - 235 + 1620, Y_BATH_N + 670, 250, "A-FIXT")
M.circle((X_BATH_W - 235 + 1450, Y_BATH_N + 375), 35, "A-FIXT")
M.rect(X_BATH_W - 235 + 1550, Y_BATH_N + 250, X_BATH_W - 235 + 1650, Y_BATH_N + 350, "A-FIXT")
M.rect(X_BATH_W, 3800, X_BATH_W + 480, 4400, "A-FIXT")                               # vanity
ellipse(X_BATH_W + 250, 4100, 150, 210)
M.rect(-800, Y_BATH_S - 600, -T, Y_BATH_S, "A-FIXT")                                 # washer
M.circle((-500, Y_BATH_S - 300), 220, "A-FIXT")

# --- 4.1 daughter / 4.2 son ------------------------------------------------------------------
rrect(X_KP - 900, 30, X_KP, Y_KP - 30, 50)              # daughter: bed along the partition
rrect(X_KP - 850, 80, X_KP - 50, 480, 60)
M.line((X_KP - 900, 700), (X_KP, 700), "A-FURN")
wardrobe(2000, 0, 3400, 600)                           # wardrobe on the north wall
M.rect(1400, Y_KP - 550, 2800, Y_KP, "A-FURN")         # desk on the south partition
office_chair(2100, 1200, 90)

rrect(X_KP + 100, 300, X_KP + 1000, 2300, 50)          # son: bed along the partition
rrect(X_KP + 150, 350, X_KP + 950, 750, 60)
M.line((X_KP + 100, 980), (X_KP + 1000, 980), "A-FURN")
M.rect(5650, 700, X_FAC, 1900, "A-FURN")               # desk at the window
office_chair(5350, 1300, 0)
wardrobe(4550, 2450, 5450, Y_LK)

# --- 5 kitchen -------------------------------------------------------------------------------
M.rect(2700, Y_LK + T, 5500, 3800, "A-FIXT")
rrect(3100, 3260, 3650, 3740, 40, "A-FIXT")
rrect(3150, 3310, 3600, 3690, 60, "A-FIXT")
M.circle((3375, 3500), 35, "A-FIXT")
M.rect(4150, 3250, 4600, 3750, "A-FIXT")
M.circle((4375, 3380), 105, "A-FIXT")
M.circle((4375, 3620), 105, "A-FIXT")
M.rect(2250, 6100, X_PART, 6800, "A-FIXT")             # tall pantry in the new nook
M.line((2250, 6100), (X_PART, 6800), "A-FIXT")
M.rect(2250, 6800, X_PART, Y_B1, "A-FIXT")             # fridge
for a in (0, 60, 120):
    t = math.radians(a)
    M.line((2575 - 120 * math.cos(t), 7150 - 120 * math.sin(t)),
           (2575 + 120 * math.cos(t), 7150 + 120 * math.sin(t)), "A-FIXT")
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

# --- 2 studio: dining + lounge ---------------------------------------------------------------
M.rect(1100, 6550, X_KIT, 7650, "A-FURN")
chair(875, 6850, "right")
chair(875, 7350, "right")
chair(1475, 6310, "down")
chair(1475, 7890, "up")
rrect(0, 8050, 850, 9450, 120)                          # sofa
M.line((200, 8150), (200, 9350), "A-FURN")
M.line((0, 8250), (850, 8250), "A-FURN")
M.line((0, 9250), (850, 9250), "A-FURN")
rrect(1150, 8550, 1700, 9150, 60)                      # coffee table
M.rect(2500, 8700, X_PART, 9400, "A-FURN")             # TV unit
M.line((2850, 8780), (2850, 9320), "A-FIXT")

# --- 6 hidden PC & home-cinema room ----------------------------------------------------------
M.rect(400, Y_SECRET + T_P, 2500, Y_SECRET + T_P + 60, "A-FIXT")      # projection screen
for sx in (250, 2650):
    M.rect(sx - 120, Y_SECRET + T_P + 40, sx + 120, Y_SECRET + T_P + 280, "A-FIXT")  # speakers
for k, cx in enumerate((750, 1450, 2150)):             # three recliners facing the screen
    rrect(cx - 330, 11350, cx + 330, 12250, 100)
    M.line((cx - 330, 12050), (cx + 330, 12050), "A-FURN")
M.rect(1300, 12450, 1600, 12650, "A-FIXT")             # projector
M.poly([(1350, 12450), (1450, 12300), (1550, 12450)], "A-FIXT")
M.rect(300, 13300, 1900, Y_FAC - 50, "A-FURN")         # PC desk at the facade
for mx0 in (500, 1150):
    M.line((mx0, 13820), (mx0 + 500, 13820), "A-FIXT")
office_chair(1100, 12950, 90)

# --- 7 master bedroom, 8 loggia ----------------------------------------------------------------
wardrobe(4300, 6350, X_FAC, 6950)
bed(X_PART + T, 9225, 5250, 11225, "left")
nightstand(X_PART + T, 8775, 3550, 9175)
nightstand(X_PART + T, 11275, 3550, 11675)
rrect(5350, 7400, 6100, 8150, 150)                     # armchair by the window
M.rect(X_PART + T, 12450, 3450, 13950, "A-FURN")       # bookcase with the hidden door
for yb in range(12450, 13950, 250):
    M.line((X_PART + T, yb), (3450, yb), "A-FURN")
M.circle((5800, 13500), 330, "A-FURN")
for k in range(8):
    t = math.radians(22.5 + 45 * k)
    M.line((5800, 13500), (5800 + 330 * math.cos(t), 13500 + 330 * math.sin(t)), "A-FURN")
M.rect(4650, 13350, 5350, 13900, "A-FURN")

# --- rooms & areas ---------------------------------------------------------------------------
ROOMS3 = [
    ("1", "Прихожая", "Hall + passage", 5.8, (-2950, 900)),
    ("2", "Гостиная-студия", "Studio", 14.1, (925, 5200)),
    ("3.1", "Ванная", "Bathroom", 4.1, (-1200, 3550)),
    ("3.2", "Туалет", "WC", None, (-1520, 1130)),
    ("4.1", "Детская (дочь)", "Daughter's room", 14.4, (2350, 900)),
    ("4.2", "Детская (сын)", "Son's room", None, (3000, 2550)),
    ("5", "Кухня", "Kitchen", 11.0, (4150, 4500)),
    ("6", "ПК и кинозал", "PC + home cinema", 17.8, (1450, 10650)),
    ("7", "Мастер-спальня", "Master bedroom", 19.7, (4550, 10250)),
    ("8", "Лоджия", "Loggia", 5.3, (5050, 12850)),
]


def room_areas():
    closed = unary_union(walls + columns + [
        LineString([(-10, Y_LK + T), (X_KW + 10, Y_LK + T)]).buffer(2),   # hall | studio
        r(4300, Y_LG, 5750, Y_LG + T),
        r(5700, 4240, 6100, 4260),
        r(X_KIT + T, Y_LK + T, 2700, 3700),
    ])
    free = box(X_HALL - T, -T, X_FAC, Y_FAC).difference(closed)
    return {no: next(g for g in polys(free) if g.contains(Point(pt))).area / 1e6
            for no, _, _, _, pt in ROOMS3}


AREAS = room_areas()
SIZES = {"2": 2.6, "3.1": 2.4, "4.1": 2.5, "4.2": 2.5, "6": 2.6, "7": 2.6}
for no, ru, en, before, (x, y) in ROOMS3:
    if no == "3.2":
        M.text((x, y), f"{no} {ru} {AREAS[no]:.1f} м²", 1.6, style="italic")
        continue
    h = SIZES.get(no, 3.0)
    M.text((x, y - 160), f"{no}  {ru}", h, style="italic")
    M.text((x, y + 160), f"{AREAS[no]:.1f} м²", h)
M.text((650, 6450), "обеденная зона", 1.8, style="italic")
M.text((1450, 9330), "мягкая зона", 1.8, style="italic")
M.text((1450, Y_SECRET + T_P + 180), "экран / screen", 1.6, style="italic")
M.text((3280, 13200), "потайная дверь", 1.6, style="italic", rot=90)
M.text((2150, 5450), "витраж / glazed wall", 1.6, style="italic", rot=90)

# --- dimensions --------------------------------------------------------------------------------
dim((X_HALL, 250), (COL_W_FACE, 250), "h", 250, 3600)
dim((-3700, 0), (-3700, Y_HALL), "v", -3700, 2000)
dim((X_BATH_W - 235, 3100), (-T, 3100), "h", 3100, -T - X_BATH_W + 235)
dim((X_BATH_W, 4380), (-T, 4380), "h", 4380, 1665)
dim((-1700, Y_BATH_N), (-1700, Y_BATH_S), "v", -1700, 2450, text_at=4200)
dim((0, 2600), (X_KW, 2600), "h", 2600, X_KW)
dim((X_KW + T, 1350), (X_KP, 1350), "h", 1350, X_KP - X_KW - T, text_at=2300)
dim((3300, 0), (3300, Y_KP), "v", 3300, Y_KP, text_at=1150)
dim((X_KP + 100, 280), (X_FAC, 280), "h", 280, X_FAC - X_KP - 100, text_at=5600)
dim((5400, 0), (5400, Y_LK), "v", 5400, 3000, text_at=2250)
dim((0, 5750), (X_KIT, 5750), "h", 5750, 1850)
dim((3200, Y_LK + T), (3200, Y_KB), "v", 3200, 2900)
dim((X_KIT + T, 5750), (X_FAC, 5750), "h", 5750, 4200)
dim((1975, Y_B1 + T), (1975, Y_SECRET), "v", 1975, Y_SECRET - Y_B1 - T)
dim((3600, Y_KB + T), (3600, Y_LG), "v", 3600, 5850, text_at=7250)
dim((X_PART + T, 11750), (X_FAC, 11750), "h", 11750, 3150)
dim((0, 10300), (X_PART, 10300), "h", 10300, 2900)
dim((2750, Y_SECRET + T_P), (2750, Y_FAC), "v", 2750, Y_FAC - Y_SECRET - T_P, text_at=11000)
dim((4550, Y_LG + T), (4550, Y_FAC), "v", 4550, 1650)

NOTES = [
    ("ПРИМЕЧАНИЯ / NOTES", "bold"),
    ("1. Размеры в мм, М 1:50 при печати A3 100 %.", "regular"),
    ("   Dimensions in mm; 1:50 when printed on A3 at 100 %.", "italic"),
    ("2. Меняются только внутренние перегородки; наружные", "regular"),
    ("   стены, колонны, шахты и фасад - без изменений.", "regular"),
    ("   Interior partitions only; shell, columns, shafts unchanged.", "italic"),
    ("3. «Было» - площади исходного плана, «стало» - по чертежу", "regular"),
    ("   (за вычетом колонн и шахт). / 'Before' = source plan,", "regular"),
    ("   'after' = measured on this drawing, net of columns.", "italic"),
    ("4. Детская дочери без окна: фрамуга / свет с севера.", "regular"),
    ("   Daughter's room 4.1 has no window of its own.", "italic"),
    ("5. Проект согласовать до начала работ.", "regular"),
    ("   Approve with the authorities before building.", "italic"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    bp.check_dims()
    br.build_sheet(ROOMS3, AREAS, NOTES, sheet="3",
                   title_ru="План квартиры - вариант перепланировки 2",
                   title_en="Apartment floor plan - replanning proposal, variant 2",
                   header="ПЕРЕПЛАНИРОВКА, ВАРИАНТ 2  /  REPLANNING, VARIANT 2")
    bp.register_fonts()
    pdf_path = os.path.join(OUT, "replan-v2_1-50_A3.pdf")
    w = bp.PdfWriter(pdf_path)
    w.c.setTitle("Apartment replanning proposal, variant 2, 1:50 (A3)")
    w.draw(M, lambda p: bp.to_paper(*p))
    w.dims()
    w.draw(P, lambda p: p)
    w.save()
    dxf_path = os.path.join(OUT, "replan-v2_1-50.dxf")
    bp.write_dxf(dxf_path)
    bp.verify_dxf(dxf_path)
    bp.verify_pdf(pdf_path)
    import pymupdf
    pymupdf.open(pdf_path)[0].get_pixmap(dpi=150).save(os.path.join(OUT, "replan-v2_1-50_A3.png"))
    for no, ru, en, before, _ in ROOMS3:
        print(f"  {no:4s} {en:18s} {'' if before is None else before:>5} -> {AREAS[no]:.2f} m²")
    print(f"  total {sum(AREAS.values()):.2f} m²")


if __name__ == "__main__":
    main()
