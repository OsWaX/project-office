# City Design: how Leonida is built

## 1. The state is a set of contrasts, not a map

Leonida (fictional Florida) is composed of regions that each remove something the others
have. This is the core structural idea and it is copyable at any scale.

| Region | Real-world basis | What it is *for* |
|---|---|---|
| **Vice City** | Miami — South Beach, downtown, Brickell | Density, vanity, verticality, nightlife. The reference point everything else is measured against |
| **Leonida Keys** | Florida Keys | Horizontality and travel: island chain, causeways, ocean routes, small communities |
| **Grassrivers** | The Everglades | Wilderness without elevation; swamp, wildlife, airboats. Removes roads |
| **Port Gellhorn** | Panama City, Gulf coast | Rust-belt waterfront: docks, warehouses, shipping, a working-class criminal economy. Removes glamour |
| **Ambrosia** | Lake Okeechobee / Clewiston sugar country | Rural-industrial interior: sugar refineries, biker culture, old American grit. Removes the coast |
| **Mount Kalaga National Park** | North Florida uplands | Forest, canyon, river, trails, elevation. Removes the flat and the city entirely — closest thing to Red Dead terrain |

**The principle:** each region is defined by a subtraction. Nobody needs six variations on
"city". They need one city and five arguments against it. When you can state what a region
*lacks*, players can feel where they are with their eyes closed.

## 2. Fidelity to a real place, then one step sideways

Rockstar kept a research team in Miami for years; fans overlaying trailer stills on
photographs of South Beach find them near-identical, and one interactive map catalogued
20+ real landmarks from the first trailer alone.

The pattern in how real places are transposed:

- **One-to-one where the silhouette is the identity.** Ocean Drive's pastel art-deco hotel
  frontages are recreated almost exactly, because the frontage *is* the recognition.
- **Renamed where ownership matters.** The Kaseya Center becomes the Sahara Arena; E11EVEN
  becomes NINE1NINE. Same shape, different noun.
- **Compressed where geography is inconvenient.** The Venetian Causeway, the island
  structure, the Keys chain — real topology, edited for driving.
- **Parodied where the original is already absurd.** The giant lobster at Rain Barrel
  Village becomes the "Wonder Whale". Roadside Americana needs no exaggeration, only
  translation.

**Transferable rule:** research a real place hard enough that locals recognise it, then
change exactly the things that would create legal or narrative friction. Authenticity is
cheaper than invention and reads better.

## 3. Districts as cultural units

Neighbourhoods are not skins on the same street grid; they are defined by who lives there
and what that does to every asset in frame. Vice City's Little Cuba differs from the
downtown financial towers not only in architecture but in signage language, vehicle mix,
crowd density, clothing and daily routine. Wynwood's mural walls make an entire district
legible from a moving car.

The lesson is that **district identity is carried by four channels at once**:

1. **Architecture** — silhouette, era, material, height.
2. **Surface writing** — language on signs, brand tier, typography, condition of paint.
3. **Population** — who is on the street, dressed how, doing what, at what hour.
4. **Traffic and props** — vehicle class and age, street furniture, litter, what is parked.

Change fewer than three of these and a district reads as the same place with a filter on.

## 4. Making one engine serve many places

A stated design concern: nightlife, coastal highway, swamp, interior hideout, sun-baked
suburban road, industrial space and crowded plaza all need different treatment, yet must
not feel like different games. The reconciler is the **shared systems layer** — one
lighting model, one weather model, one crowd model, one grade pipeline — with per-region
authored *inputs* rather than per-region special cases.

**Transferable rule:** variety belongs in the data, consistency belongs in the systems. If
a location needs bespoke code to look right, it will drift away from the rest of the world.

## 5. Water, weather, humidity

Water is a first-class material here: ray-traced reflections, wet roads that carry sign
colour, ocean between islands, swamp that changes what vehicles are possible. Humidity is
treated as a visible medium — light shafts, haze, softened distance. In a coastal setting,
atmosphere is not a post-effect, it is the thing that unifies every exterior shot.

## 6. Crowds make the city

Density is scaled and placed per location rather than set globally: busy beachfront and
club queues against near-empty rural roads. A city reads as a city because of *where the
people are not*, as much as where they are.
