"""Қайта режалаштириш: ички деворлар, эшиклар ва хоналар, М 1:50.

Ташқи деворлар, шахталар ва координаталар generate_plan.py дан олинади.
Ишга тушириш:  python3 plans/generate_layout.py
"""
import math

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from shapely.geometry import box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

import generate_plan as G
from generate_plan import (BALCONY, DIMS, DOORS, FONT, LW_MED, LW_THIN, LW_WALL, MM_PT, OUT, OX, OY,
                           PAPER_H, PAPER_W, SCALE, SHAFTS, WALLS, WINDOWS, D, P, draw_dim, draw_door,
                           draw_window, label, leader, line, poly_patch)

T = 100  # ички девор қалинлиги

# Ички девор ўқлари (қизил чизиқлар бўйича)
X_V1 = (-550, -450)    # ванна | туалет
X_V2 = (650, 750)      # туалет | ошхона
X_V3 = (4640, 4740)    # ошхона | катталар ётоқхонаси (шахта юзаси билан бир чизиқда)
X_V4 = (5830, 5930)    # даҳлиз, меҳмонхона | ётоқхона, болалар хонаси
Y_H1 = (2600, 2700)    # ванна, туалет, ошхона, ётоқхона | даҳлиз (даҳлиз кенглиги 1000)
Y_H2 = (2750, 2850)    # катталар ётоқхонаси | болалар хонаси (балкон ости девори билан бир чизиқда)
Y_H3 = (3700, 3800)    # даҳлиз | меҳмонхона
X_V5 = (-100, 0)       # даҳлиз | меҳмонхона (кириш ёнидаги)

part_raw = [
    box(G.X_L_IN, Y_H1[0], X_V4[0], Y_H1[1]),
    box(X_V1[0], 0, X_V1[1], Y_H1[0]),
    box(X_V2[0], 0, X_V2[1], Y_H1[0]),
    box(X_V3[0], 0, X_V3[1], Y_H1[0]),
    box(X_V4[0], Y_H1[0], X_V4[1], G.Y_DEPTH),
    box(X_V4[1], Y_H2[0], G.X_KITCHEN_END, Y_H2[1]),
    box(X_V5[0], Y_H3[0], X_V4[0], Y_H3[1]),
    box(X_V5[0], Y_H3[1], X_V5[1], G.Y_HALL),
]

# Эшик ўринлари (девордаги тешиклар)
OP_BATH = (-1300, -600)
OP_WC = (-300, 400)
OP_KITCHEN = (1300, 2100)
OP_BED = (4840, 5640)
OP_KIDS = (2900, 3700)        # Y бўйича, V4 деворида
OP_LIVING = (1000, 2200)      # икки табақали

part_openings = [
    box(OP_BATH[0], Y_H1[0], OP_BATH[1], Y_H1[1]),
    box(OP_WC[0], Y_H1[0], OP_WC[1], Y_H1[1]),
    box(OP_KITCHEN[0], Y_H1[0], OP_KITCHEN[1], Y_H1[1]),
    box(OP_BED[0], Y_H1[0], OP_BED[1], Y_H1[1]),
    box(X_V4[0], OP_KIDS[0], X_V4[1], OP_KIDS[1]),
    box(OP_LIVING[0], Y_H3[0], OP_LIVING[1], Y_H3[1]),
]
PARTITIONS = unary_union(part_raw).difference(unary_union(part_openings)).difference(WALLS)

hh, ht = Y_H1[1], Y_H3[1]
NEW_DOORS = [
    # ванна ва туалет: даҳлизга очилади
    dict(hinge=(OP_BATH[1], hh), leaf_end=(OP_BATH[1], hh + 700), arc_start=(OP_BATH[0], hh), r=700),
    dict(hinge=(OP_WC[0], hh), leaf_end=(OP_WC[0], hh + 700), arc_start=(OP_WC[1], hh), r=700),
    # ошхона ва ётоқхона: хона ичига очилади
    dict(hinge=(OP_KITCHEN[0], Y_H1[0]), leaf_end=(OP_KITCHEN[0], Y_H1[0] - 800),
         arc_start=(OP_KITCHEN[1], Y_H1[0]), r=800),
    dict(hinge=(OP_BED[1], Y_H1[0]), leaf_end=(OP_BED[1], Y_H1[0] - 800),
         arc_start=(OP_BED[0], Y_H1[0]), r=800),
    # болалар хонаси: хона ичига
    dict(hinge=(X_V4[1], OP_KIDS[0]), leaf_end=(X_V4[1] + 800, OP_KIDS[0]),
         arc_start=(X_V4[1], OP_KIDS[1]), r=800),
    # меҳмонхона: икки табақа, хона ичига
    dict(hinge=(OP_LIVING[0], ht), leaf_end=(OP_LIVING[0], ht + 600),
         arc_start=((OP_LIVING[0] + OP_LIVING[1]) / 2, ht), r=600),
    dict(hinge=(OP_LIVING[1], ht), leaf_end=(OP_LIVING[1], ht + 600),
         arc_start=((OP_LIVING[0] + OP_LIVING[1]) / 2, ht), r=600),
]

SOLIDS = unary_union([WALLS, PARTITIONS] + [o for o, _ in SHAFTS.values()])


def room(*rects):
    return unary_union([box(*r) for r in rects]).difference(SOLIDS)


ROOMS = [
    # номи, полигон, ёзув нуқтаси
    ("Ванна", room((G.X_L_IN, 0, X_V1[0], Y_H1[0])), (-1050, 900)),
    ("Туалет", room((X_V1[1], 0, X_V2[0], Y_H1[0])), (100, 900)),
    ("Ошхона", room((X_V2[1], 0, X_V3[0], Y_H1[0])), (2200, 1300)),
    ("Катталар ётоқхонаси", room((X_V3[1], 0, G.X_KITCHEN_END, Y_H1[0]),
                                  (X_V4[1], Y_H1[0], G.X_KITCHEN_END, Y_H2[0])), (7300, 1250)),
    ("Болалар хонаси", room((X_V4[1], Y_H2[1], G.X_R_IN, G.Y_DEPTH)), (7700, 4600)),
    ("Меҳмонхона", room((0, Y_H3[1], X_V4[0], G.Y_DEPTH)), (2100, 4850)),
    ("Даҳлиз", room((G.X_L_IN, Y_H1[1], X_V4[0], Y_H3[0]),
                    (G.X_L_IN, Y_H3[0], X_V5[0], G.Y_HALL)), (2000, 2950)),
]

EXT_DIMS = DIMS[:9]
INT_DIMS = [
    # ички девор ва хоналар занжири (ванна → ётоқхона)
    ("h", [G.X_L_IN, G.X_L_IN + 250, X_V1[0], X_V1[1], X_V2[0], X_V2[1], X_V3[0], X_V3[1], G.X_KITCHEN_END], 2300, None),
    # вертикал: ошхона → даҳлиз → меҳмонхона
    ("v", [0, Y_H1[0], Y_H1[1], Y_H3[0], Y_H3[1], G.Y_DEPTH], 3000, None),
    # вертикал: ётоқхона → болалар хонаси
    ("v", [0, Y_H2[0], Y_H2[1], G.Y_DEPTH], 9000, None),
    # горизонтал: меҳмонхона → болалар хонаси
    ("h", [0, X_V4[0], X_V4[1], G.X_R_IN], 5700, None),
    # даҳлиз томондан эшиклар боғланиши
    ("h", [G.X_L_IN, OP_BATH[0], OP_BATH[1], OP_WC[0], OP_WC[1], OP_KITCHEN[0], OP_KITCHEN[1],
           OP_BED[0], OP_BED[1], X_V4[0]], 3500, Y_H1[1]),
    # меҳмонхона эшиги
    ("h", [0, OP_LIVING[0], OP_LIVING[1]], 4350, None),
    # болалар хонаси эшиги
    ("v", [Y_H2[1], OP_KIDS[0], OP_KIDS[1]], 7000, None),
    # балкон блоки
    ("v", [0, G.PIER_WIN[0], G.PIER_WIN[1], G.PIER_DOOR[1]], G.X_KITCHEN_END - 1100, None),
    # шахталар
    ("h", [X_V2[1], 3900, 4640], 800, None),
    ("v", [0, 520], 5100, None),
    ("v", [0, 1500], -1650, None),
]

NAME = "plan_qayta_rejalashtirish_1-50"


def render_sheet():
    plt.rcParams["hatch.linewidth"] = 0.35
    fig = plt.figure(figsize=(PAPER_W / 25.4, PAPER_H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, PAPER_W)
    ax.set_ylim(0, PAPER_H)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((20, 5), PAPER_W - 25, PAPER_H - 10, fill=False, lw=0.7 * MM_PT))

    ax.add_patch(poly_patch(BALCONY, facecolor="#eef3f7", edgecolor="none"))
    for name, poly, _ in ROOMS:
        if name in ("Ванна", "Туалет"):
            ax.add_patch(poly_patch(poly, facecolor="#eaf4fb", edgecolor="none"))

    ax.add_patch(poly_patch(WALLS, facecolor="#d9d9d9", edgecolor="none", hatch="//////"))
    ax.add_patch(poly_patch(WALLS, facecolor="none", edgecolor="black", lw=LW_WALL))
    ax.add_patch(poly_patch(PARTITIONS, facecolor="#9e9e9e", edgecolor="black", lw=LW_MED))

    for outer, void in SHAFTS.values():
        ax.add_patch(poly_patch(outer.difference(void), facecolor="#6e6e6e", edgecolor="black", lw=LW_MED))
        ax.add_patch(poly_patch(void, facecolor="white", edgecolor="black", lw=LW_MED))
        x0, y0, x1, y1 = void.bounds
        line(ax, (x0, y0), (x1, y1))
        line(ax, (x0, y1), (x1, y0))

    for w in WINDOWS:
        draw_window(ax, *w)
    for d in DOORS + NEW_DOORS:
        draw_door(ax, d)
    for dim in EXT_DIMS + INT_DIMS:
        draw_dim(ax, *dim)

    for name, poly, (x, y) in ROOMS:
        label(ax, x, y, name, fs=8.5 if len(name) < 12 else 8, weight="bold")
        label(ax, x, y + 330, f"{poly.area / 1e6:.2f} м²", fs=7.5)
    bx = (G.X_KITCHEN_END + G.T_PIER + G.X_R_IN) / 2
    label(ax, bx, 900, "Балкон", fs=8, weight="bold")
    label(ax, bx, 1230, f"{BALCONY.area / 1e6:.2f} м²", fs=7.5)
    leader(ax, (G.X_L_IN + 85, 700), (-900, 450), "Шахта", fs=7)
    leader(ax, (4270, 210), (6000, 450), "Шахта", fs=7)
    label(ax, -1650, G.Y_HALL + G.T_COR + 2000, "Кириш (подъезд йўлагидан)", fs=7.5)

    ax.text(OX + G.X_L_OUT / SCALE, 282, "КВАРТИРАНИ ҚАЙТА РЕЖАЛАШТИРИШ РЕЖАСИ",
            fontsize=12, family=FONT, weight="bold", va="center")
    ax.text(OX + G.X_L_OUT / SCALE, 274, "М 1:50", fontsize=11, family=FONT, va="center")

    # Хоналар экспликацияси
    ex, ey, cw = 25, 66, (10, 58, 22)
    rows = [("№", "Хона номи", "Майдон, м²")]
    living = 0
    for i, (name, poly, _) in enumerate(ROOMS, 1):
        rows.append((str(i), name, f"{poly.area / 1e6:.2f}"))
        living += poly.area / 1e6
    rows.append(("", "Жами (балконсиз)", f"{living:.2f}"))
    rows.append((str(len(ROOMS) + 1), "Балкон", f"{BALCONY.area / 1e6:.2f}"))
    rh = 5.2
    ax.text(ex, ey + 4, "Хоналар экспликацияси", fontsize=8.5, family=FONT, weight="bold", va="center")
    for r, row in enumerate(rows):
        y = ey - (r + 1) * rh
        x = ex
        for c, (w, val) in enumerate(zip(cw, row)):
            ax.add_patch(Rectangle((x, y), w, rh, fill=False, lw=LW_THIN))
            bold = r == 0 or row[1].startswith("Жами")
            ax.text(x + (w / 2 if c != 1 else 1.5), y + rh / 2, val, fontsize=7.2, family=FONT,
                    va="center", ha="center" if c != 1 else "left", weight="bold" if bold else "normal")
            x += w

    notes = [
        "Изоҳлар:",
        "1. Барча ўлчамлар миллиметрда.",
        "2. Янги ички деворлар 100 мм, даҳлиз кенглиги 1000 мм.",
        "3. Эшик ўринлари: ванна ва туалет 700 мм,",
        "    ошхона, ётоқхоналар 800 мм, меҳмонхона",
        "    1200 мм икки табақали.",
        "4. Ванна ва туалет эшиклари даҳлизга очилади.",
        "5. Шахталар ўз ўрнида сақланган.",
        "6. Ташқи девор қалинликлари манба расмдан",
        "    тахминий олинган, жойида текширилсин.",
    ]
    for i, n in enumerate(notes):
        ax.text(132, 64 - i * 4.0, n, fontsize=7, family=FONT, va="center")

    tx, ty, tw, th = 230, 5, 185, 40
    ax.add_patch(Rectangle((tx, ty), tw, th, fill=False, lw=0.7 * MM_PT))
    srows = [("Объект", "Квартира (қайта режалаштириш)"), ("Чизма", "Хоналар режаси, ички деворлар"),
             ("Масштаб", "1:50"), ("Формат", "A3"), ("Сана", "24.09.2026")]
    rh2 = th / len(srows)
    for i, (k, v) in enumerate(srows):
        y = ty + th - (i + 1) * rh2
        if i:
            ax.plot([tx, tx + tw], [y + rh2, y + rh2], color="black", lw=LW_THIN)
        ax.text(tx + 2, y + rh2 / 2, k, fontsize=7.5, family=FONT, va="center")
        ax.text(tx + 32, y + rh2 / 2, v, fontsize=8.5, family=FONT, va="center")
    ax.plot([tx + 30, tx + 30], [ty, ty + th], color="black", lw=LW_THIN)

    sx, sy = 30, 80
    for i in range(3):
        ax.add_patch(Rectangle((sx + i * 20, sy), 20, 2, facecolor="black" if i % 2 == 0 else "white",
                               edgecolor="black", lw=LW_THIN))
    for i in range(4):
        ax.text(sx + i * 20, sy + 3, f"{i} м", ha="center", va="bottom", fontsize=7, family=FONT)

    fig.savefig(OUT / f"{NAME}_A3.pdf")
    fig.savefig(OUT / f"{NAME}_A3.png", dpi=200, facecolor="white")
    plt.close(fig)


def render_dxf():
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.styles.new("ARIAL", dxfattribs={"font": "arial.ttf"})
    for n, c in [("A-WALL", 7), ("A-WALL-HATCH", 8), ("A-PART", 6), ("A-SHAFT", 5), ("A-GLAZ", 4),
                 ("A-DOOR", 3), ("A-DIMS", 1), ("A-TEXT", 7), ("A-BALC", 9)]:
        doc.layers.add(n, color=c)
    ds = doc.dimstyles.new("ARCH50")
    for k, v in dict(dimscale=SCALE, dimtxt=2.5, dimasz=1.5, dimtsz=1.2, dimexe=1.5, dimexo=1.0,
                     dimgap=0.7, dimdec=0, dimtad=1, dimtxsty="ARIAL", dimtih=0, dimtoh=0).items():
        ds.dxf.set(k, v)
    msp = doc.modelspace()

    def add_poly(geom, layer, pattern=None, color=None):
        for g in getattr(geom, "geoms", [geom]):
            g = orient(g, 1.0)
            rings = [g.exterior, *g.interiors]
            for ring in rings:
                msp.add_lwpolyline([D(*c) for c in ring.coords[:-1]], close=True, dxfattribs={"layer": layer})
            if pattern or color is not None:
                h = msp.add_hatch(color=color if color is not None else 8, dxfattribs={"layer": "A-WALL-HATCH"})
                if pattern:
                    h.set_pattern_fill(pattern, scale=25)
                for k, ring in enumerate(rings):
                    h.paths.add_polyline_path([D(*c) for c in ring.coords[:-1]], is_closed=True,
                                              flags=1 if k == 0 else 0)

    add_poly(WALLS, "A-WALL", pattern="ANSI31")
    add_poly(PARTITIONS, "A-PART", color=252)
    add_poly(BALCONY, "A-BALC")
    for outer, void in SHAFTS.values():
        add_poly(outer.difference(void), "A-SHAFT", color=251)
        x0, y0, x1, y1 = void.bounds
        msp.add_lwpolyline([D(x0, y0), D(x1, y0), D(x1, y1), D(x0, y1)], close=True, dxfattribs={"layer": "A-SHAFT"})
        msp.add_line(D(x0, y0), D(x1, y1), dxfattribs={"layer": "A-SHAFT"})
        msp.add_line(D(x0, y1), D(x1, y0), dxfattribs={"layer": "A-SHAFT"})
    for x0, y0, x1, y1, _ in WINDOWS:
        for xx in (x0, x1, x0 + (x1 - x0) * 0.42, x0 + (x1 - x0) * 0.58):
            msp.add_line(D(xx, y0), D(xx, y1), dxfattribs={"layer": "A-GLAZ"})
        for yy in (y0, y1):
            msp.add_line(D(x0, yy), D(x1, yy), dxfattribs={"layer": "A-GLAZ"})
    for d in DOORS + NEW_DOORS:
        msp.add_line(D(*d["hinge"]), D(*d["leaf_end"]), dxfattribs={"layer": "A-DOOR"})
        hx, hy = D(*d["hinge"])
        ax_, ay_ = D(*d["arc_start"])
        lx, ly = D(*d["leaf_end"])
        a1 = math.degrees(math.atan2(ay_ - hy, ax_ - hx)) % 360
        a2 = math.degrees(math.atan2(ly - hy, lx - hx)) % 360
        if (a2 - a1) % 360 > 180:
            a1, a2 = a2, a1
        msp.add_arc((hx, hy), d["r"], a1, a2, dxfattribs={"layer": "A-DOOR"})
    for kind, pts, pos, obj in EXT_DIMS + INT_DIMS:
        pts = sorted(pts)
        o = obj if obj is not None else pos
        for a, b in zip(pts, pts[1:]):
            if kind == "h":
                dim = msp.add_linear_dim(base=D(a, pos), p1=D(a, o), p2=D(b, o), angle=0,
                                         dimstyle="ARCH50", dxfattribs={"layer": "A-DIMS"})
            else:
                dim = msp.add_linear_dim(base=D(pos, a), p1=D(o, a), p2=D(o, b), angle=90,
                                         dimstyle="ARCH50", dxfattribs={"layer": "A-DIMS"})
            dim.render()

    def txt(s, x, y, h=2.5):
        msp.add_text(s, height=h * SCALE, dxfattribs={"layer": "A-TEXT", "style": "ARIAL"}).set_placement(
            D(x, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    for name, poly, (x, y) in ROOMS:
        txt(name, x, y, 2.5)
        txt(f"{poly.area / 1e6:.2f} м²", x, y + 330, 2.0)
    txt("Балкон", (G.X_KITCHEN_END + G.T_PIER + G.X_R_IN) / 2, 900)
    txt("Кириш", -1650, G.Y_HALL + G.T_COR + 2000)
    txt("ҚАЙТА РЕЖАЛАШТИРИШ РЕЖАСИ  М 1:50", 4800, -3200, 5.0)

    lay = doc.layouts.new("A3 1-50")
    lay.page_setup(size=(420, 297), margins=(0, 0, 0, 0), units="mm")
    lay.add_lwpolyline([(20, 5), (415, 5), (415, 292), (20, 292)], close=True)
    minx, miny, maxx, maxy = -5500, -1900, 15200, 7700
    vw, vh = (maxx - minx) / SCALE, (maxy - miny) / SCALE
    lay.add_viewport(center=(217.5, 172), size=(vw, vh), view_center_point=((minx + maxx) / 2, -(miny + maxy) / 2),
                     view_height=vh * SCALE)
    lay.add_text("КВАРТИРАНИ ҚАЙТА РЕЖАЛАШТИРИШ РЕЖАСИ   М 1:50", height=5,
                 dxfattribs={"style": "ARIAL"}).set_placement((30, 280))
    doc.saveas(OUT / f"{NAME}.dxf")


if __name__ == "__main__":
    render_sheet()
    render_dxf()
    tot = 0
    for name, poly, _ in ROOMS:
        tot += poly.area / 1e6
        print(f"{name:22s} {poly.area / 1e6:6.2f} м²  bounds={tuple(round(v) for v in poly.bounds)}")
    print(f"{'Жами':22s} {tot:6.2f} м²")
