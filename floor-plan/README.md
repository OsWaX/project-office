# Apartment floor plan, redrawn at 1:50

Redrawn from `source/original-plan.jpg` (a phone photo of a developer's plan).

| File | What it is |
|---|---|
| `output/flat-plan_1-50_A3.pdf` | Print-ready A3 sheet. Print at **100 % / actual size** to get the plan at 1:50 (1 m = 20 mm; there's a scale bar on the sheet to check). |
| `output/flat-plan_1-50.dxf` | CAD file (AutoCAD 2010 DXF). Model space is in millimetres (1 unit = 1 mm). The `A3 1-50` layout holds the sheet with a locked 1:50 viewport. |
| `output/flat-plan_1-50_A3.png` | Preview of the PDF. |
| `build_plan.py` | Generates all of the above: `pip install -r requirements.txt && python3 build_plan.py` |

## What's exact and what's inferred

**Exact, taken from the source:** all 15 printed dimensions (3600, 2000, 4970, 3000, 2450, 1665,
1850, 4350, 2900, 4200, 5850, 3150, 6300, 2900, 1650) and the room areas.
Each run of the script checks that the geometry reproduces every dimension, that each DXF
`DIMENSION` entity measures its value, and that each dimension line in the PDF is exactly value/50 mm long.

**Inferred (the source doesn't dimension these):** wall thickness (200 mm throughout), columns,
door/window positions and widths, shafts and furniture. These were scaled off a
perspective-corrected copy of the photo (homography fitted to the dimensioned walls, residuals about ±30 mm).
Check them on site before using the drawing for construction.

Two places where the source is slightly inconsistent, and how they were resolved:

* The right-hand chain (3000 + 2900 + 5850 + 1650 + four 200 mm walls = 14000) and the left-hand chain
  through the corridor (4350 + 6300) disagree by about 67 mm if the 45° living-room wall sits exactly where
  it's drawn. The 45° wall (not dimensioned) was moved 67 mm so that every printed dimension holds.
* Room areas are shown as printed. Areas computed from the drawn geometry differ by up to about
  0.5 m² (e.g. the bedroom marked 17.8 m² is 2.9 × 6.3 = 18.27 m² gross), presumably because the
  developer's figures leave out columns, wardrobes and similar.
