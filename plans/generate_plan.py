"""Квартира режаси: фақат ташқи деворлар ва шахталар, М 1:50.

Координаталар мм да. Бошланғич нуқта (0, 0) — умумий хонанинг чап ички
юзаси ва юқори деворнинг ички юзаси кесишган жойи. X ўнгга, Y пастга
(DXF да Y тескари қилинади).

Ишга тушириш:  python3 plans/generate_plan.py
Натижа: plans/output/ ичида PDF (A3, 1:50), PNG ва DXF.
"""
from pathlib import Path

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, PathPatch, Rectangle
from matplotlib.path import Path as MPath
from shapely.geometry import box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

OUT = Path(__file__).resolve().parent / "output"
SCALE = 50  # 1:50

# --------------------------------------------------------------------------
# Геометрия (мм)
# --------------------------------------------------------------------------
T_TOP = 250      # юқори ташқи девор
T_BOT = 250      # пастки ташқи девор
T_LEFT = 300     # чап ташқи девор
T_RIGHT = 300    # фасад (ётоқхона деразаси) девори
T_COR = 200      # йўлак (подъезд) томондаги девор
T_PIER = 200     # ошхона ва балкон орасидаги девор
T_UNDER = 350    # балкон ва ётоқхона орасидаги девор

X_L_IN = -2100            # чап деворнинг ички юзаси (С/У 1900 + 200)
X_L_OUT = X_L_IN - T_LEFT
X_KITCHEN_END = 10650     # 4000 + 6650 (ошхона)
X_R_IN = 11810            # 4000 + 7810 (ётоқхона)
X_R_OUT = X_R_IN + T_RIGHT
Y_DEPTH = 6000            # умумий хона ички чуқурлиги
Y_HALL = 4200             # С/У 2400 + 100 + даҳлиз 1700
Y_BALC = 2750             # балкон чуқурлиги
Y_UNDER = Y_BALC + T_UNDER  # 3100 = 2950 + 150 (ётоқхона 2900 шу ердан)

DOOR_ENTRY = (-1450, -450)          # кириш эшиги ўрни (X)
PIER_WIN = (1170, 1960)             # балкон блокидаги дераза (Y)
PIER_DOOR = (1960, Y_BALC)          # балкон эшиги (Y)
BED_WIN = (3450, 5700)              # ётоқхона деразаси (Y)
BALC_GLAZ = (0, Y_BALC)             # балкон ойнаси (Y)

walls_raw = [
    box(X_L_OUT, -T_TOP, X_R_OUT, 0),                      # юқори
    box(X_L_OUT, -T_TOP, X_L_IN, Y_HALL + T_COR),          # чап
    box(X_L_OUT, Y_HALL, 0, Y_HALL + T_COR),               # йўлак (горизонтал)
    box(-T_COR, Y_HALL, 0, Y_DEPTH + T_BOT),               # йўлак (вертикал)
    box(-T_COR, Y_DEPTH, X_R_OUT, Y_DEPTH + T_BOT),        # пастки
    box(X_R_IN, -T_TOP, X_R_OUT, Y_DEPTH + T_BOT),         # ўнг фасад
    box(X_KITCHEN_END, 0, X_KITCHEN_END + T_PIER, Y_BALC), # ошхона/балкон
    box(X_KITCHEN_END, Y_BALC, X_R_IN, Y_UNDER),           # балкон остидаги
]
openings = [
    box(DOOR_ENTRY[0], Y_HALL, DOOR_ENTRY[1], Y_HALL + T_COR),
    box(X_R_IN, BALC_GLAZ[0], X_R_OUT, BALC_GLAZ[1]),
    box(X_R_IN, BED_WIN[0], X_R_OUT, BED_WIN[1]),
    box(X_KITCHEN_END, PIER_WIN[0], X_KITCHEN_END + T_PIER, PIER_DOOR[1]),
]
WALLS = unary_union(walls_raw).difference(unary_union(openings))

# Шахталар: (ташқи контур, бўшлиқ)
SHAFTS = {
    "С/У шахтаси": (box(X_L_IN, 0, X_L_IN + 250, 1500), box(X_L_IN, 0, X_L_IN + 170, 1420)),
    "Ошхона шахтаси": (box(3900, 0, 4640, 520), box(4000, 0, 4540, 420)),
}

# Деразалар: (x0, y0, x1, y1, йўналиш) — ойна чизиқлари йўналиши
WINDOWS = [
    (X_R_IN, BALC_GLAZ[0], X_R_OUT, BALC_GLAZ[1], "v"),
    (X_R_IN, BED_WIN[0], X_R_OUT, BED_WIN[1], "v"),
    (X_KITCHEN_END, PIER_WIN[0], X_KITCHEN_END + T_PIER, PIER_WIN[1], "v"),
]
# Эшиклар: (ошиқ-мошиқ нуқтаси, эни, очиқ табақа бурчаги, ёй бурчаклари)
DOORS = [
    # Кириш эшиги: ташқарига (йўлакка) очилади
    dict(hinge=(DOOR_ENTRY[1], Y_HALL + T_COR), leaf_end=(DOOR_ENTRY[1], Y_HALL + T_COR + 1000),
         arc_start=(DOOR_ENTRY[0], Y_HALL + T_COR), r=1000),
    # Балкон эшиги: ошхона томонга очилади
    dict(hinge=(X_KITCHEN_END, Y_BALC), leaf_end=(X_KITCHEN_END - 790, Y_BALC),
         arc_start=(X_KITCHEN_END, PIER_DOOR[0]), r=790),
]


def net_area_m2():
    inner = unary_union([
        box(X_L_IN, 0, 0, Y_HALL),
        box(0, 0, X_KITCHEN_END, Y_DEPTH),
        box(X_KITCHEN_END, Y_UNDER, X_R_IN, Y_DEPTH),
    ])
    for outer, _ in SHAFTS.values():
        inner = inner.difference(outer)
    return inner.area / 1e6


BALCONY = box(X_KITCHEN_END + T_PIER, 0, X_R_IN, Y_BALC)

# Ўлчам занжирлари: (тури, нуқталар, чизиқ ҳолати, объект ҳолати)
OFF1, OFF2 = 700, 1300  # ташқи юзадан 14 ва 26 мм (қоғозда)
DIMS = [
    # юқори
    ("h", [X_L_OUT, X_L_IN, X_KITCHEN_END, X_KITCHEN_END + T_PIER, X_R_IN, X_R_OUT], -T_TOP - OFF1, -T_TOP),
    ("h", [X_L_OUT, X_R_OUT], -T_TOP - OFF2, -T_TOP),
    # пастки
    ("h", [-T_COR, 0, X_R_IN, X_R_OUT], Y_DEPTH + T_BOT + OFF1, Y_DEPTH + T_BOT),
    ("h", [-T_COR, X_R_OUT], Y_DEPTH + T_BOT + OFF2, Y_DEPTH + T_BOT),
    # йўлак девори (кириш эшиги)
    ("h", [X_L_OUT, DOOR_ENTRY[0], DOOR_ENTRY[1], -T_COR], Y_HALL + T_COR + 1500, Y_HALL + T_COR),
    # чап
    ("v", [-T_TOP, 0, Y_HALL, Y_HALL + T_COR, Y_DEPTH + T_BOT], X_L_OUT - OFF1, X_L_OUT),
    ("v", [-T_TOP, Y_DEPTH + T_BOT], X_L_OUT - OFF2, X_L_OUT),
    # ўнг
    ("v", [-T_TOP, 0, Y_BALC, BED_WIN[0], BED_WIN[1], Y_DEPTH, Y_DEPTH + T_BOT], X_R_OUT + OFF1, X_R_OUT),
    ("v", [-T_TOP, Y_DEPTH + T_BOT], X_R_OUT + OFF2, X_R_OUT),
    # ички ўлчамлар
    ("v", [0, Y_DEPTH], 1500, None),
    ("h", [0, X_R_IN], 5400, None),
    ("h", [X_L_IN, 0], 3300, None),
    ("v", [0, PIER_WIN[0], PIER_WIN[1], PIER_DOOR[1], Y_UNDER], X_KITCHEN_END - 1100, None),
    # шахталар боғланиши
    ("h", [X_L_IN, X_L_IN + 250, 3900, 4640], 2000, None),
    ("v", [0, 1500], X_L_IN + 700, None),
    ("v", [0, 520], 5100, None),
]

# --------------------------------------------------------------------------
# PDF / PNG (A3, 1:50)
# --------------------------------------------------------------------------
PAPER_W, PAPER_H = 420, 297
OX, OY = 106, 222   # модел (0,0) нуқтасининг қоғоздаги ўрни (мм)
MM_PT = 72 / 25.4
LW_WALL = 0.5 * MM_PT
LW_THIN = 0.18 * MM_PT
LW_MED = 0.3 * MM_PT
FS_DIM = 7.5
FONT = "DejaVu Sans"


def P(x, y):
    return OX + x / SCALE, OY - y / SCALE


def poly_patch(geom, **kw):
    geoms = getattr(geom, "geoms", [geom])
    verts, codes = [], []
    for g in geoms:
        g = orient(g, 1.0)
        for ring in [g.exterior, *g.interiors]:
            pts = [P(*c) for c in ring.coords]
            verts += pts
            codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2) + [MPath.CLOSEPOLY]
    return PathPatch(MPath(verts, codes), **kw)


def line(ax, p1, p2, lw=LW_THIN, **kw):
    (x1, y1), (x2, y2) = P(*p1), P(*p2)
    ax.plot([x1, x2], [y1, y2], color=kw.pop("color", "black"), lw=lw,
            solid_capstyle="butt", **kw)


def text_w_mm(s, fs=FS_DIM):
    return len(s) * fs * 0.6 / MM_PT


def draw_dim(ax, kind, pts, pos, obj):
    tick, over, gap = 1.1, 1.5, 1.0  # мм (қоғоз)
    pts = sorted(pts)
    if kind == "h":
        yl = OY - pos / SCALE
        side = -1 if obj is not None and pos > obj else 1  # матн томонга
        for x in pts:
            px = OX + x / SCALE
            if obj is not None:
                yo = OY - obj / SCALE
                d = 1 if yl > yo else -1
                ax.plot([px, px], [yo + d * gap, yl + d * over], color="black", lw=LW_THIN)
            ax.plot([px - tick, px + tick], [yl - tick, yl + tick], color="black", lw=LW_MED * 1.6)
        ax.plot([OX + pts[0] / SCALE - over, OX + pts[-1] / SCALE + over], [yl, yl], color="black", lw=LW_THIN)
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            s = f"{b - a:.0f}"
            L = (b - a) / SCALE
            cx = OX + (a + b) / 2 / SCALE
            dy = 0.7
            if L < text_w_mm(s) + 0.8:
                if obj is None:
                    dy = 3.2
                elif i == 0:
                    cx = OX + a / SCALE - text_w_mm(s) / 2 - 1.2
                else:
                    dy = 3.2
            ax.text(cx, yl + dy, s, ha="center", va="bottom", fontsize=FS_DIM, family=FONT)
    else:
        xl = OX + pos / SCALE
        for y in pts:
            py = OY - y / SCALE
            if obj is not None:
                xo = OX + obj / SCALE
                d = 1 if xl > xo else -1
                ax.plot([xo + d * gap, xl + d * over], [py, py], color="black", lw=LW_THIN)
            ax.plot([xl - tick, xl + tick], [py - tick, py + tick], color="black", lw=LW_MED * 1.6)
        ax.plot([xl, xl], [OY - pts[0] / SCALE + over, OY - pts[-1] / SCALE - over], color="black", lw=LW_THIN)
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            s = f"{b - a:.0f}"
            L = (b - a) / SCALE
            cy = OY - (a + b) / 2 / SCALE
            dx = 0.7
            if L < text_w_mm(s) + 0.8:
                if obj is None:
                    dx = 3.2
                elif i == 0:
                    cy = OY - a / SCALE + text_w_mm(s) / 2 + 1.2
                elif i == len(pts) - 2:
                    cy = OY - b / SCALE - text_w_mm(s) / 2 - 1.2
                else:
                    dx = 3.2
            ax.text(xl - dx, cy, s, ha="center", va="bottom", rotation=90,
                    rotation_mode="anchor", fontsize=FS_DIM, family=FONT)


def draw_window(ax, x0, y0, x1, y1, orient_):
    # деворнинг икки юзаси + иккита ойна чизиғи
    if orient_ == "v":
        for x in (x0, x1):
            line(ax, (x, y0), (x, y1), lw=LW_THIN)
        for f in (0.42, 0.58):
            xm = x0 + (x1 - x0) * f
            line(ax, (xm, y0), (xm, y1), lw=LW_THIN)
        for y in (y0, y1):
            line(ax, (x0, y), (x1, y), lw=LW_THIN)
    else:
        for y in (y0, y1):
            line(ax, (x0, y), (x1, y), lw=LW_THIN)
        for f in (0.42, 0.58):
            ym = y0 + (y1 - y0) * f
            line(ax, (x0, ym), (x1, ym), lw=LW_THIN)


def draw_door(ax, d):
    line(ax, d["hinge"], d["leaf_end"], lw=LW_MED * 1.4)
    hx, hy = P(*d["hinge"])
    ax_, ay_ = P(*d["arc_start"])
    lx, ly = P(*d["leaf_end"])
    import math
    a1 = math.degrees(math.atan2(ay_ - hy, ax_ - hx))
    a2 = math.degrees(math.atan2(ly - hy, lx - hx))
    lo, hi = sorted([a1, a2])
    if hi - lo > 180:
        lo, hi = hi, lo + 360
    r = d["r"] / SCALE
    ax.add_patch(Arc((hx, hy), 2 * r, 2 * r, theta1=lo, theta2=hi, lw=LW_THIN, color="black"))


def label(ax, x, y, s, fs=8, **kw):
    px, py = P(x, y)
    ax.text(px, py, s, ha=kw.pop("ha", "center"), va=kw.pop("va", "center"), fontsize=fs, family=FONT, **kw)


def leader(ax, frm, to, s, fs=7.5, ha="left"):
    (x1, y1), (x2, y2) = P(*frm), P(*to)
    ax.plot([x1, x2], [y1, y2], color="black", lw=LW_THIN)
    ax.plot([x1], [y1], marker="o", ms=1.6, color="black")
    ax.plot([x2, x2 + (12 if ha == "left" else -12)], [y2, y2], color="black", lw=LW_THIN)
    ax.text(x2 + (0.5 if ha == "left" else -0.5), y2 + 0.6, s, ha=ha, va="bottom", fontsize=fs, family=FONT)


def render_sheet():
    plt.rcParams["hatch.linewidth"] = 0.35
    fig = plt.figure(figsize=(PAPER_W / 25.4, PAPER_H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, PAPER_W)
    ax.set_ylim(0, PAPER_H)
    ax.set_aspect("equal")
    ax.axis("off")

    # Рамка (ГОСТ: чапда 20, қолганида 5 мм)
    ax.add_patch(Rectangle((20, 5), PAPER_W - 25, PAPER_H - 10, fill=False, lw=0.7 * MM_PT))

    # Балкон поли (оч рангда)
    ax.add_patch(poly_patch(BALCONY, facecolor="#eef3f7", edgecolor="none"))

    # Ташқи деворлар
    ax.add_patch(poly_patch(WALLS, facecolor="#d9d9d9", edgecolor="none", hatch="//////"))
    ax.add_patch(poly_patch(WALLS, facecolor="none", edgecolor="black", lw=LW_WALL))

    # Шахталар
    for outer, void in SHAFTS.values():
        ax.add_patch(poly_patch(outer.difference(void), facecolor="#8c8c8c", edgecolor="black", lw=LW_MED))
        ax.add_patch(poly_patch(void, facecolor="white", edgecolor="black", lw=LW_MED))
        x0, y0, x1, y1 = void.bounds
        line(ax, (x0, y0), (x1, y1), lw=LW_THIN)
        line(ax, (x0, y1), (x1, y0), lw=LW_THIN)

    for w in WINDOWS:
        draw_window(ax, *w)
    for d in DOORS:
        draw_door(ax, d)
    for dim in DIMS:
        draw_dim(ax, *dim)

    # Ёзувлар
    label(ax, (X_KITCHEN_END + T_PIER + X_R_IN) / 2, 900, "Балкон", fs=8)
    label(ax, (X_KITCHEN_END + T_PIER + X_R_IN) / 2, 1250, "2.6 м²", fs=7)
    label(ax, 6200, 2300, "Умумий майдон (ички деворларсиз)", fs=9)
    label(ax, 6200, 2800, f"≈ {net_area_m2():.1f} м²", fs=9)
    leader(ax, (X_L_IN + 85, 900), (X_L_IN + 1500, 850), "Шахта (С/У)")
    leader(ax, (4270, 210), (5600, 1150), "Шахта (ошхона)")
    label(ax, -1650, Y_HALL + T_COR + 2000,
          "Кириш (подъезд йўлагидан)", fs=7.5)

    # Сарлавҳа
    ax.text(OX + X_L_OUT / SCALE, 282, "КВАРТИРА РЕЖАСИ — ФАҚАТ ТАШҚИ ДЕВОРЛАР ВА ШАХТАЛАР",
            fontsize=12, family=FONT, weight="bold", va="center")
    ax.text(OX + X_L_OUT / SCALE, 274, "М 1:50", fontsize=11, family=FONT, va="center")

    # Масштаб чизғичи: 0–3 м
    sx, sy = 30, 22
    for i in range(3):
        ax.add_patch(Rectangle((sx + i * 20, sy), 20, 2, facecolor="black" if i % 2 == 0 else "white",
                               edgecolor="black", lw=LW_THIN))
    for i in range(4):
        ax.text(sx + i * 20, sy + 3, f"{i} м", ha="center", va="bottom", fontsize=7, family=FONT)
    ax.text(sx, sy - 3.5, "Масштаб чизғичи (1:50 да 1 м = 20 мм)", fontsize=6.5, family=FONT, va="center")

    # Изоҳлар
    notes = [
        "Изоҳлар:",
        "1. Барча ўлчамлар миллиметрда.",
        "2. Ички деворлар олиб ташланган, ташқи деворлар,",
        "    дераза ва эшик ўринлари сақланган.",
        "3. С/У ва ошхонадаги шахталар ўз ўрнида кўрсатилган.",
        "4. Девор қалинликлари ва шахта ўлчамлари манба",
        "    расмдан тахминий олинган, жойида текширилсин.",
    ]
    for i, n in enumerate(notes):
        ax.text(110, 56 - i * 4.2, n, fontsize=7, family=FONT, va="center")

    # Штамп
    tx, ty, tw, th = 230, 5, 185, 40
    ax.add_patch(Rectangle((tx, ty), tw, th, fill=False, lw=0.7 * MM_PT))
    rows = [("Объект", "Квартира (қайта режалаштириш учун)"), ("Чизма", "Ташқи деворлар режаси"),
            ("Масштаб", "1:50"), ("Формат", "A3"), ("Сана", "24.09.2026")]
    rh = th / len(rows)
    for i, (k, v) in enumerate(rows):
        y = ty + th - (i + 1) * rh
        if i:
            ax.plot([tx, tx + tw], [y + rh, y + rh], color="black", lw=LW_THIN)
        ax.text(tx + 2, y + rh / 2, k, fontsize=7.5, family=FONT, va="center")
        ax.text(tx + 32, y + rh / 2, v, fontsize=8.5, family=FONT, va="center")
    ax.plot([tx + 30, tx + 30], [ty, ty + th], color="black", lw=LW_THIN)

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "plan_tashqi_devorlar_1-50_A3.pdf")
    fig.savefig(OUT / "plan_tashqi_devorlar_1-50_A3.png", dpi=200, facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------------------
# DXF (модел фазоси 1:1 мм, A3 варақда 1:50 кўриниш)
# --------------------------------------------------------------------------
def D(x, y):
    return (x, -y)


def render_dxf():
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.styles.new("ARIAL", dxfattribs={"font": "arial.ttf"})
    for name, color in [("A-WALL", 7), ("A-WALL-HATCH", 8), ("A-SHAFT", 5), ("A-GLAZ", 4),
                        ("A-DOOR", 3), ("A-DIMS", 1), ("A-TEXT", 7), ("A-BALC", 9)]:
        doc.layers.add(name, color=color)
    ds = doc.dimstyles.duplicate_entry("EZ_M_50_H25_CM", "ARCH50") if "EZ_M_50_H25_CM" in doc.dimstyles \
        else doc.dimstyles.new("ARCH50")
    ds.dxf.dimscale = SCALE
    ds.dxf.dimtxt = 2.5
    ds.dxf.dimasz = 1.5
    ds.dxf.dimtsz = 1.2   # архитектура чизиқчалари
    ds.dxf.dimexe = 1.5
    ds.dxf.dimexo = 1.0
    ds.dxf.dimgap = 0.7
    ds.dxf.dimdec = 0
    ds.dxf.dimtad = 1
    ds.dxf.dimlfac = 1
    ds.dxf.dimpost = "<>"
    ds.dxf.dimtxsty = "ARIAL"
    ds.dxf.dimtih = 0
    ds.dxf.dimtoh = 0
    msp = doc.modelspace()

    def add_poly(geom, layer, hatch=False, fill=None):
        for g in getattr(geom, "geoms", [geom]):
            g = orient(g, 1.0)
            rings = [g.exterior, *g.interiors]
            for ring in rings:
                msp.add_lwpolyline([D(*c) for c in ring.coords[:-1]], close=True, dxfattribs={"layer": layer})
            if hatch or fill is not None:
                h = msp.add_hatch(color=fill if fill is not None else 8,
                                  dxfattribs={"layer": "A-WALL-HATCH"})
                if hatch:
                    h.set_pattern_fill("ANSI31", scale=25)
                for k, ring in enumerate(rings):
                    h.paths.add_polyline_path([D(*c) for c in ring.coords[:-1]], is_closed=True,
                                              flags=1 if k == 0 else 0)

    add_poly(WALLS, "A-WALL", hatch=True)
    add_poly(BALCONY, "A-BALC")
    for outer, void in SHAFTS.values():
        add_poly(outer.difference(void), "A-SHAFT", fill=252)
        x0, y0, x1, y1 = void.bounds
        msp.add_lwpolyline([D(x0, y0), D(x1, y0), D(x1, y1), D(x0, y1)], close=True, dxfattribs={"layer": "A-SHAFT"})
        msp.add_line(D(x0, y0), D(x1, y1), dxfattribs={"layer": "A-SHAFT"})
        msp.add_line(D(x0, y1), D(x1, y0), dxfattribs={"layer": "A-SHAFT"})
    for x0, y0, x1, y1, _ in WINDOWS:
        for xx in (x0, x1, x0 + (x1 - x0) * 0.42, x0 + (x1 - x0) * 0.58):
            msp.add_line(D(xx, y0), D(xx, y1), dxfattribs={"layer": "A-GLAZ"})
        for yy in (y0, y1):
            msp.add_line(D(x0, yy), D(x1, yy), dxfattribs={"layer": "A-GLAZ"})
    import math
    for d in DOORS:
        msp.add_line(D(*d["hinge"]), D(*d["leaf_end"]), dxfattribs={"layer": "A-DOOR"})
        hx, hy = D(*d["hinge"])
        ax_, ay_ = D(*d["arc_start"])
        lx, ly = D(*d["leaf_end"])
        a1 = math.degrees(math.atan2(ay_ - hy, ax_ - hx)) % 360
        a2 = math.degrees(math.atan2(ly - hy, lx - hx)) % 360
        if (a2 - a1) % 360 > 180:
            a1, a2 = a2, a1
        msp.add_arc((hx, hy), d["r"], a1, a2, dxfattribs={"layer": "A-DOOR"})

    for kind, pts, pos, _obj in DIMS:
        pts = sorted(pts)
        for a, b in zip(pts, pts[1:]):
            if kind == "h":
                dim = msp.add_linear_dim(base=D(a, pos), p1=D(a, _obj if _obj is not None else pos),
                                         p2=D(b, _obj if _obj is not None else pos), angle=0,
                                         dimstyle="ARCH50", dxfattribs={"layer": "A-DIMS"})
            else:
                dim = msp.add_linear_dim(base=D(pos, a), p1=D(_obj if _obj is not None else pos, a),
                                         p2=D(_obj if _obj is not None else pos, b), angle=90,
                                         dimstyle="ARCH50", dxfattribs={"layer": "A-DIMS"})
            dim.render()

    def txt(s, x, y, h=2.5, rot=0):
        msp.add_text(s, height=h * SCALE, rotation=rot,
                     dxfattribs={"layer": "A-TEXT", "style": "ARIAL"}).set_placement(
            D(x, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    txt("Балкон", (X_KITCHEN_END + T_PIER + X_R_IN) / 2, 900, 2.5)
    txt("Шахта", X_L_IN + 1100, 700, 2.0)
    txt("Шахта", 4270, 850, 2.0)
    txt("Кириш", -1650, Y_HALL + T_COR + 2000, 2.5)
    txt(f"Умумий майдон ≈ {net_area_m2():.1f} м²", 6200, 2600, 3.0)
    txt("ТАШҚИ ДЕВОРЛАР РЕЖАСИ  М 1:50", 4800, -3200, 5.0)

    # A3 варақ (paperspace) 1:50 viewport билан
    lay = doc.layouts.new("A3 1-50")
    lay.page_setup(size=(420, 297), margins=(0, 0, 0, 0), units="mm")
    lay.add_lwpolyline([(20, 5), (415, 5), (415, 292), (20, 292)], close=True)
    minx, miny, maxx, maxy = -5500, -1900, 15200, 7700  # модел (Y пастга)
    vw, vh = (maxx - minx) / SCALE, (maxy - miny) / SCALE
    cx_m, cy_m = (minx + maxx) / 2, -(miny + maxy) / 2
    lay.add_viewport(center=(217.5, 172), size=(vw, vh), view_center_point=(cx_m, cy_m), view_height=vh * SCALE)
    lay.add_text("КВАРТИРА РЕЖАСИ — ТАШҚИ ДЕВОРЛАР ВА ШАХТАЛАР   М 1:50", height=5,
                 dxfattribs={"style": "ARIAL"}).set_placement((30, 280))
    lay.add_text("Ўлчамлар мм да. Девор қалинликлари тахминий.", height=3,
                 dxfattribs={"style": "ARIAL"}).set_placement((30, 20))

    OUT.mkdir(parents=True, exist_ok=True)
    doc.saveas(OUT / "plan_tashqi_devorlar_1-50.dxf")


if __name__ == "__main__":
    render_sheet()
    render_dxf()
    print(f"Ички майдон ≈ {net_area_m2():.2f} м²")
    print("Тайёр:", *sorted(p.name for p in OUT.iterdir()), sep="\n  ")
