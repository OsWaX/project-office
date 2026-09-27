# Apartment floor plan, redrawn at 1:50

Redrawn from `source/original-plan.jpg` (a phone photo of a developer's plan).

| File | What it is |
|---|---|
| `output/flat-plan_1-50_A3.pdf` | Print-ready A3 sheet. Print at **100 % / actual size** to get the plan at 1:50 (1 m = 20 mm; there's a scale bar on the sheet to check). |
| `output/flat-plan_1-50.dxf` | CAD file (AutoCAD 2010 DXF). Model space is in millimetres (1 unit = 1 mm). The `A3 1-50` layout holds the sheet with a locked 1:50 viewport. |
| `output/flat-plan_1-50_A3.png` | Preview of the PDF. |
| `output/replan_1-50_A3.pdf`, `output/replan_1-50.dxf`, `.png` | Sheet 2: replanning proposal (interior walls only), same scale and sheet setup. |
| `build_plan.py` | Generates the as-drawn plan (sheet 1): `pip install -r requirements.txt && python3 build_plan.py` |

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

## Sheet 2: replanning proposal (`build_replan.py`)

Only interior partitions change; the shell, columns, shafts and facade stay as on sheet 1.
New partitions are drawn orange, demolished ones dashed.

* **4 → 4.1 + 4.2 children's rooms**, each with its own door. The west wall moves to the column (C1)
  and the 45° wall is extended. 4.2 gets the facade window; **4.1 has no window** unless the north
  wall is external, so it needs a glazed transom or borrowed light (flagged on the sheet).
* **3 → 3.1 bathroom + 3.2 WC** with separate doors. The WC (1.0 × 1.0 m) is taken from the hall corner
  and opens onto the passage. The bathroom's east wall moves 600 mm east (4.1 → 4.8 m²; the WC is no longer inside it).
* **6 → secret room** (about 12.4 m²), reached only through a hidden bookcase door from the loggia.
  Its north part joins the studio.
* **5 kitchen**: the west wall becomes a glazed partition with a glass door. The fridge moves to the worktop run.
* **2 corridor → studio** with a dining zone (table at the kitchen wall) and a lounge zone (sofa and TV
  in the former north part of room 6). To keep the dining zone clear, bedroom 7's door moves from the
  corridor to its vestibule's south wall.

Areas on sheet 2 are measured from the drawing (net of columns and shafts), next to the source
values ("было"), so unchanged rooms show small differences.

## Sheet 3: replanning, variant 2 (`build_replan_v2.py`)

Interior walls only.

* **4 → 4.1 daughter's room (6.6 m²) and 4.2 son's room (8.0 m²)**, separate rooms with separate doors
  off a 900 mm passage. The block's south-west corner is squared off. 4.2 gets the facade window;
  **4.1 has no window of its own**.
* **3 → 3.1 bathroom (4.4 m², rectangular: the 45° corner is squared)** with its own door, plus a separate
  **3.2 WC (1.0 m²)** in the hall corner with its own door.
* **6 → 6 PC and home-cinema room (12.4 m²)**: screen, three recliners, projector and PC desk. The only
  way in is a hidden bookcase door from the loggia.
* **5 kitchen (12.1 m²)**: the west wall is glazed. The south wall now starts at bedroom 7's west wall,
  so the kitchen gains a nook for the fridge and a pantry.
* **7 → master bedroom (18.3 m²)**: its west wall runs straight up to the kitchen wall. The door moves
  onto that wall and opens from the studio's lounge zone.
* **2 corridor → studio (13.2 m²)** with a dining zone at the kitchen glass and a lounge zone in the
  north part of the former room 6.

## Sheet 4: replanning variant 3, the client's sketch (`build_replan_v3.py`)

The walls were read off the client's sketch, which was drawn over sheet 1: 1 sketch px = 0.21 mm on paper = 10.5 mm
real. They were then snapped to 50 mm. Page 1 is the plan at 1:50; page 2 is the room and wall calculation (also in
`output/replan-v3_calculation.csv`).

| Room | Clear size, mm | Area, m² |
|---|---|---|
| 1 Hall | 2900 × 2000 | 5.8 |
| 2 Studio (lounge + dining) | L-shaped, 2900 wide | 21.8 |
| 3 Bathroom / WC (unchanged) | 1665–1900 × 2450 | 4.0 |
| 4 Children's room for two | 4970 × 3000 | 14.3 |
| 5 Kitchen (open plan) | 4200 × 1700 | 6.0 |
| 6 Hidden PC + home-cinema room | 2900 × 4600 | 13.0 |
| 7 Master bedroom | 3150 × 5800 | 18.1 |
| 7.1 En-suite shower room | 1500 × 1150 | 1.7 |
| 7.2 Walk-in wardrobe | 1550 × 1150 | 1.6 |
| 8 Loggia | 3150 × 1650 | 5.1 |

New walls: 11.65 m in total (200 / 100 mm). Demolition: 8.47 m (200 mm).

## Sheet 5: colour furnished design of variant 3 (`build_design_v3.py`)

The same walls, doors, dimensions and areas as sheet 4, still at 1:50, with floor finishes added:
- oak parquet in the living rooms,
- porcelain tile in the hall and kitchen,
- bathroom tile in both bathrooms,
- dark carpet in the cinema room,
- decking on the loggia.

Coloured furniture and décor are added too. Outputs: `output/design-v3_1-50_A3.pdf`, `.png` (200 dpi), `.dxf`.
