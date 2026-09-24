"""Мебеллар жойлашуви режаси, М 1:50.

Деворлар, эшиклар ва хоналар generate_layout.py дан олинади.
Мебеллар ҳақиқий стандарт ўлчамларда (мм) чизилади.
Ишга тушириш:  python3 plans/generate_furniture.py
"""
from matplotlib.patches import Circle as MCircle
from matplotlib.patches import Polygon as MPolygon
from shapely import affinity
from shapely.geometry import Point, box

import generate_layout as L
from generate_plan import LW_THIN, SCALE, D, P

NAME = "plan_mebel_joylashuvi_1-50"
TITLE = "МЕБЕЛЛАР ЖОЙЛАШУВИ РЕЖАСИ"

# --------------------------------------------------------------------------
# Примитивлар: ("poly", нуқталар, ёпиқ, штрих) ва ("circle", cx, cy, r, штрих)
# --------------------------------------------------------------------------


class Item:
    """Мебель. u — орқа томондан (девордан) олдинга, v — эни бўйича."""

    def __init__(self, x0, y0, x1, y1, back="top"):
        self.x0, self.y0, self.x1, self.y1, self.back = x0, y0, x1, y1, back
        if back in ("top", "bottom"):
            self.Du, self.Wv = y1 - y0, x1 - x0
        else:
            self.Du, self.Wv = x1 - x0, y1 - y0
        self.shapes = []

    def g(self, u, v):
        b = self.back
        if b == "top":
            return self.x0 + v, self.y0 + u
        if b == "bottom":
            return self.x0 + v, self.y1 - u
        if b == "left":
            return self.x0 + u, self.y0 + v
        return self.x1 - u, self.y0 + v

    def poly(self, pts, closed=True, dashed=False):
        self.shapes.append(("poly", [self.g(u, v) for u, v in pts], closed, dashed))

    def rect(self, u0, v0, u1, v1, r=0, dashed=False):
        if r:
            geom = box(u0 + r, v0 + r, u1 - r, v1 - r).buffer(r, quad_segs=4)
            self.poly(list(geom.exterior.coords)[:-1], dashed=dashed)
        else:
            self.poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], dashed=dashed)

    def line(self, u0, v0, u1, v1, dashed=False):
        self.poly([(u0, v0), (u1, v1)], closed=False, dashed=dashed)

    def ellipse(self, uc, vc, ru, rv):
        geom = affinity.scale(Point(uc, vc).buffer(1, quad_segs=12), ru, rv)
        self.poly(list(geom.exterior.coords)[:-1])

    def circle(self, uc, vc, r, dashed=False):
        x, y = self.g(uc, vc)
        self.shapes.append(("circle", x, y, r, dashed))

    def outline(self, r=0):
        self.rect(0, 0, self.Du, self.Wv, r=r)
        return self


def bed(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline(r=30)
    W = it.Wv
    if W >= 1400:
        it.rect(70, 90, 470, W / 2 - 45, r=60)
        it.rect(70, W / 2 + 45, 470, W - 90, r=60)
    else:
        it.rect(70, 110, 450, W - 110, r=60)
    it.line(620, 0, 620, W)
    it.line(620, W - 420, 1000, W)
    return it


def nightstand(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline()
    it.circle(it.Du / 2, it.Wv / 2, 110)
    return it


def wardrobe(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline()
    it.line(it.Du - 40, 0, it.Du - 40, it.Wv)          # эшик табақаси
    it.line(it.Du / 2, 60, it.Du / 2, it.Wv - 60)       # илгич штанга
    v = 180
    while v < it.Wv - 120:
        it.line(it.Du / 2 - 170, v - 40, it.Du / 2 + 170, v + 40)
        v += 180
    return it


def sofa(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline(r=60)
    D_, W = it.Du, it.Wv
    it.rect(0, 0, 220, W, r=40)             # суянчиқ
    it.rect(220, 0, D_, 200, r=40)          # тирсаклар
    it.rect(220, W - 200, D_, W, r=40)
    n = 3 if W > 1700 else 2
    step = (W - 400) / n
    for i in range(1, n):
        it.line(220, 200 + i * step, D_, 200 + i * step)
    return it


def chair(cx, cy, back, s=420):
    it = Item(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, back).outline(r=40)
    it.rect(0, 0, 80, s, r=30)
    return it


def table(x0, y0, x1, y1, r=30):
    return Item(x0, y0, x1, y1).outline(r=r)


def round_table(cx, cy, rad):
    it = Item(cx - rad, cy - rad, cx + rad, cy + rad)
    it.circle(rad, rad, rad)
    return it


def cabinet(x0, y0, x1, y1, back, dashed_front=True):
    it = Item(x0, y0, x1, y1, back).outline()
    it.line(it.Du - 40, 0, it.Du - 40, it.Wv)
    return it


def fridge(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline()
    it.rect(40, 40, it.Du - 60, it.Wv - 40)
    it.line(40, 40, it.Du - 60, it.Wv - 40)
    it.line(40, it.Wv - 40, it.Du - 60, 40)
    return it


def counter(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline()
    return it


def sink(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back)
    it.rect(0, 0, it.Du, it.Wv, r=50)
    it.rect(60, 60, it.Du - 60, it.Wv * 0.55, r=60)
    it.circle(it.Du / 2, it.Wv * 0.3, 30)
    for k in range(4):
        vv = it.Wv * 0.62 + k * it.Wv * 0.09
        it.line(80, vv, it.Du - 80, vv)
    return it


def hob(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline(r=20)
    for uu in (0.3, 0.7):
        for vv in (0.28, 0.72):
            it.circle(it.Du * uu, it.Wv * vv, 95 if vv < 0.5 else 75)
    return it


def washer(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back)
    it.rect(0, 0, it.Du, it.Wv, dashed=True)
    it.circle(it.Du / 2 + 20, it.Wv / 2, 200, dashed=True)
    return it


def bathtub(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline(r=40)
    it.rect(70, 70, it.Du - 70, it.Wv - 70, r=220)
    it.circle(200, it.Wv / 2, 35)
    return it


def basin(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline(r=20)
    it.ellipse(it.Du * 0.52, it.Wv / 2, it.Du * 0.32, it.Wv * 0.34)
    it.circle(it.Du * 0.52, it.Wv / 2, 25)
    return it


def wc(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back)
    it.rect(0, 0, 180, it.Wv, r=30)                                   # бачок
    it.ellipse(180 + (it.Du - 180) / 2, it.Wv / 2, (it.Du - 180) / 2, it.Wv / 2 - 10)
    it.ellipse(180 + (it.Du - 180) / 2 + 20, it.Wv / 2, (it.Du - 180) / 2 - 90, it.Wv / 2 - 90)
    return it


def desk(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline()
    it.rect(40, it.Wv - 460, it.Du - 60, it.Wv - 40)  # тортмали тумба
    return it


def shelf(x0, y0, x1, y1, back):
    it = Item(x0, y0, x1, y1, back).outline()
    n = max(2, int(it.Wv // 400))
    for k in range(1, n):
        it.line(0, k * it.Wv / n, it.Du, k * it.Wv / n)
    return it


def rug(cx, cy, rad):
    it = Item(cx - rad, cy - rad, cx + rad, cy + rad)
    it.circle(rad, rad, rad, dashed=True)
    return it


# --------------------------------------------------------------------------
# Жойлаштириш (координаталар мм, 0,0 — умумий хона ички бурчаги)
# --------------------------------------------------------------------------
FURNITURE = [
    # Ванна
    bathtub(-1300, 0, -550, 1700, "top"),
    basin(-2100, 1650, -1650, 2250, "left"),
    # Туалет
    wc(-90, 0, 290, 680, "top"),
    basin(300, 1050, 650, 1500, "right"),
    # Ошхона
    fridge(750, 0, 1350, 650, "top"),
    counter(1350, 0, 3900, 600, "top"),
    sink(1650, 50, 2450, 520, "top"),
    washer(2520, 0, 3120, 580, "top"),
    hob(3220, 40, 3800, 560, "top"),
    table(1300, 1600, 2400, 2300),
    chair(1575, 1370, "top"), chair(2125, 1370, "top"),
    chair(1070, 1950, "left"), chair(2630, 1950, "right"),
    # Катталар ётоқхонаси
    wardrobe(4740, 0, 5340, 1750, "left"),
    bed(6900, 0, 8500, 2000, "top"),
    nightstand(6400, 0, 6850, 400, "top"),
    nightstand(8550, 0, 9000, 400, "top"),
    cabinet(10200, 150, 10650, 1100, "right"),
    chair(9900, 625, "left", s=400),
    # Болалар хонаси 1
    bed(7250, 5100, 9250, 6000, "left"),
    nightstand(6800, 5600, 7200, 6000, "bottom"),
    wardrobe(5930, 4650, 6530, 6000, "left"),
    desk(7800, 3800, 9000, 4400, "top"),
    chair(8400, 4620, "bottom"),
    # Болалар хонаси 2
    bed(9450, 4000, 10350, 6000, "bottom"),
    wardrobe(10250, 3100, 11400, 3700, "top"),
    desk(11210, 4000, 11810, 5200, "right"),
    chair(10960, 4600, "left"),
    nightstand(10400, 5600, 10800, 6000, "bottom"),
    # Меҳмонхона
    sofa(0, 4100, 900, 6000, "left"),
    table(1050, 4750, 1550, 5350),
    table(2400, 4450, 4400, 5350, r=40),
    *[chair(x, 4260, "top") for x in (2650, 3150, 3650, 4150)],
    *[chair(x, 5540, "bottom") for x in (2650, 3150, 3650, 4150)],
    chair(2190, 4900, "left"), chair(4610, 4900, "right"),
    cabinet(5430, 4150, 5830, 5750, "right"),
    # Даҳлиз
    wardrobe(-2100, 2800, -1500, 4150, "left"),
    # Балкон
    round_table(11330, 1000, 300),
    chair(11330, 460, "top", s=400), chair(11330, 1540, "bottom", s=400),
]

LABEL_POS = {
    "Ванна": (-925, 2050),
    "Туалет": (100, 1850),
    "Ошхона": (3300, 1050),
    "Катталар ётоқхонаси": (9350, 1500),
    "Болалар хонаси 1": (7300, 4550),
    "Болалар хонаси 2": (10900, 3880),
    "Йўлакча": (8000, 3200),
    "Меҳмонхона": (3400, 4760),
    "Даҳлиз": (2000, 3050),
    "Балкон": (11330, 1950),
}

NOTES = [
    "Изоҳлар:",
    "1. Барча ўлчамлар миллиметрда.",
    "2. Мебеллар стандарт ўлчамларда: катта каравот",
    "    1600×2000, болалар каравоти 900×2000,",
    "    шкафлар 600 чуқурликда, ошхона ишчи юзаси 600.",
    "3. Штрих чизиқ: кир ювиш машинаси ишчи юза остида.",
    "4. Ошхона эшиги стол сиғиши учун ўнг четга кўчирилди.",
    "5. Эшиклар очилиш зонаси мебелдан бўш қолдирилган.",
]

LW_FURN = 0.25 * 72 / 25.4
FURN_COLOR = "#1f4e79"


def draw_mpl(ax):
    for it in FURNITURE:
        for sh in it.shapes:
            if sh[0] == "poly":
                _, pts, closed, dashed = sh
                pp = [P(x, y) for x, y in pts]
                ax.add_patch(MPolygon(pp, closed=closed, fill=False, edgecolor=FURN_COLOR, lw=LW_FURN,
                                      linestyle=(0, (3, 2)) if dashed else "solid", joinstyle="round"))
            else:
                _, x, y, r, dashed = sh
                ax.add_patch(MCircle(P(x, y), r / SCALE, fill=False, edgecolor=FURN_COLOR, lw=LW_FURN,
                                     linestyle=(0, (3, 2)) if dashed else "solid"))


def draw_dxf(msp, doc):
    doc.layers.add("A-FURN", color=150)
    if "DASHED" not in doc.linetypes:
        doc.linetypes.add("DASHED", pattern=[0.5, 0.25, -0.25], description="Dashed __ __")
    for it in FURNITURE:
        for sh in it.shapes:
            attrs = {"layer": "A-FURN"}
            if sh[0] == "poly":
                _, pts, closed, dashed = sh
                if dashed:
                    attrs.update(linetype="DASHED", ltscale=100)
                msp.add_lwpolyline([D(x, y) for x, y in pts], close=closed, dxfattribs=attrs)
            else:
                _, x, y, r, dashed = sh
                if dashed:
                    attrs.update(linetype="DASHED", ltscale=100)
                msp.add_circle(D(x, y), r, dxfattribs=attrs)


if __name__ == "__main__":
    L.render_sheet(name=NAME, title=TITLE, sheet="Мебеллар жойлашуви", int_dims=False,
                   label_pos=LABEL_POS, extra=draw_mpl, notes=NOTES)
    L.render_dxf(name=NAME, title=TITLE, int_dims=False, label_pos=LABEL_POS, extra=draw_dxf)
    print("Тайёр:", NAME)
