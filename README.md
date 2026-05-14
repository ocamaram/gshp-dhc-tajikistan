# GSHP DHC Tajikistan — Building Heat Demand Analysis (Dushanbe)

Spatial analysis of building stock heat demand in Dushanbe, Tajikistan,
based on building footprint data from a GeoPackage file.

## Scripts

### `preprocess_dushanbe.py`
Loads the raw building footprint GeoPackage (`Data/Dushanbe.gpkg`) and
enriches each building with the following fields:

| Field | Description |
|---|---|
| `floors` | Number of floors estimated from building height (height / 2.5), capped at 20 |
| `Tagging` | OSM `building=*` tag value (from spatial join with Geofabrik data) |
| `Use` | `residential` or `tertiary`, derived from OSM tag or heuristic |
| `Type` | Building typology (see tables below) |
| `Specific Heat Demand [kWh/m2·year]` | Specific heat demand assigned by typology |
| `Heated Area [m2]` | Net floor area: footprint area × floors × 0.70 (GFA→NFA factor) |
| `Total Heat Demand [GWh/year]` | Annual heat demand per building |
| `Specific Cooling Demand [kWh/m2·year]` | Specific cooling demand by typology (placeholder — pending data) |
| `Cooling Area [m2]` | Same as `Heated Area [m2]` |
| `Total Cooling Demand [GWh/year]` | Annual cooling demand per building (null until data available) |

#### OSM Tagging → classification pipeline

1. **Spatial join with Geofabrik** (`Data/Geofabrik_tajikistan.gpkg`, layer
   `gis_osm_buildings_a_free`): for each building, the centroid is matched
   against OSM polygons with an explicit `building` tag. Tags marked as
   `construction` are excluded from the join (ambiguous use). Where a match
   is found, the OSM tag is stored in `osm_type`.

2. **`Use` assignment** (in order of priority):
   - OSM tag available → `residential` if tag is in the residential group; `tertiary` otherwise.
   - No OSM tag, 1-floor building with footprint area > 500 m² → `tertiary`.
   - Otherwise → `residential` (default).

3. **`Tagging`** (used downstream for typology):
   - OSM tag available → use OSM tag directly.
   - No OSM tag, `Use=residential` → `house` (≤ 2 floors) or `apartments` (> 2 floors).
   - No OSM tag, `Use=tertiary` → `yes`.

4. **`Type` assignment**:
   - **Residential**: floor count determines the type (Type Single Family–VI).
   - **Tertiary**: `Tagging` determines the type directly; floor count is used
     only to compute heated area and heat demand.

#### OSM tag → Use mapping

| `building=` tag | Use |
|---|---|
| `house`, `detached`, `semidetached_house`, `bungalow`, `terrace` | residential |
| `apartments`, `residential`, `dormitory`, `block`, `yes;residential` | residential |
| `construction` | ignored (falls through to heuristic/default) |
| everything else | tertiary |

#### OSM tag → Type mapping (tertiary)

| `building=` tag | Type |
|---|---|
| `school`, `kindergarten`, `college`, `university`, `education` | School |
| `hospital`, `clinic`, `doctors` | Hospital |
| `office`, `commercial`, `retail`, `industrial` | Office |
| `yes`, `public`, `civic`, `government`, `mosque`, `church`, `warehouse`, `hotel`, `roof` | Other |

Output: `Results/Dushanbe_processed.gpkg`

---

### `maps_dushanbe.py`
Loads the processed GeoPackage and produces:

**Console summary** — building count, average floors, average heated area,
specific and total heat demand per typology.

**Static maps (PNG, 150 dpi):**
- `Types.png` — building typology with categorical colours
- `Specific_Heat_Demand.png` — specific heat demand (orange–red gradient)
- `Total_Heat_Demand.png` — total heat demand in GWh/year (orange–red gradient)
- `Specific_Cooling_Demand.png` — specific cooling demand (blue gradient) — generated when cooling data available
- `Total_Cooling_Demand.png` — total cooling demand in GWh/year (blue gradient) — generated when cooling data available

**Interactive maps (HTML, Folium/Leaflet):**
- `Types_interactive.html`
- `Specific_Heat_Demand_interactive.html`
- `Total_Heat_Demand_interactive.html`
- `Specific_Cooling_Demand_interactive.html` — generated when cooling data available
- `Total_Cooling_Demand_interactive.html` — generated when cooling data available

Cooling maps are generated automatically once specific cooling demand values are populated in `cooling_demand_map` inside `preprocess_dushanbe.py`.

All maps are centred on the geometric centroid of the dataset with a
configurable zoom level (`MAP_ZOOM = 1.5` by default).

## Results

### Building typologies
![Building typologies](Results/Types.png)

### Specific heat demand
![Specific heat demand](Results/Specific_Heat_Demand.png)

### Total heat demand
![Total heat demand](Results/Total_Heat_Demand.png)

## Analysis

### Dataset overview

| Metric | Value |
|---|---|
| Total buildings | 179,912 |
| Conditioned area — NFA (heating & cooling) | 93.1 M m² |
| GFA→NFA factor applied | 0.70 |
| Total heat demand | 7,199 GWh/year |
| Weighted average specific heat demand | 77.3 kWh/m²·year |
| Total cooling demand | pending specific cooling demand data |
| Weighted average specific cooling demand | pending specific cooling demand data |

### OSM spatial join coverage

The Geofabrik OSM extract for Tajikistan (`gis_osm_buildings_a_free`) was
used to obtain building type tags via a centroid-within join. Coverage is
limited due to two independent constraints:

| Stage | Buildings | % of total |
|---|---|---|
| No OSM counterpart in dataset | 135,066 | 75.1% |
| OSM match but no explicit `type` tag | 43,858 | 24.4% |
| OSM match with `type` tag | 908 | 0.5% |
| Tertiary by area heuristic (1 floor > 500 m²) | 534 | 0.3% |
| Residential by default | 178,470 | 99.2% |

The low OSM match rate reflects data sparsity in Tajikistan, not a
projection or geometry issue — both datasets share the same bounding box
after reprojection to EPSG:32642.

### Heat demand by building type

| Type | Buildings | NFA [M m²] | Heat Demand [GWh/year] | % Total |
|---|---|---|---|---|
| Type Single Family | 126,059 | 25.4 | 3,678.6 | 35.8% |
| Type I (3 floors) | 41,429 | 42.0 | 3,108.2 | 30.2% |
| Type II (4 floors) | 9,138 | 26.1 | 1,436.2 | 14.0% |
| Type III (5–8 floors) | 1,557 | 19.1 | 1,124.2 | 10.9% |
| Type VI (12–20 floors) | 749 | 15.6 | 622.1 | 6.0% |
| Other (tertiary) | 617 | 1.5 | 102.2 | 1.0% |
| Office | 153 | 1.5 | 98.2 | 1.0% |
| Type V (10–11 floors) | 113 | 1.0 | 52.1 | 0.5% |
| School | 63 | 0.6 | 35.2 | 0.3% |
| Type IV (9 floors) | 16 | 0.2 | 16.2 | 0.2% |
| Hospital | 18 | 0.1 | 11.4 | 0.1% |

Type Single Family dominates heat demand (35.8%) despite having the lowest
total NFA, due to its high specific heat demand (145 kWh/m²·year).
Type I apartment blocks are the largest contributor by NFA (42.0 M m²).

### Cooling demand by building type

Cooling demand breakdown will be populated once specific cooling demand
values per typology are available. The `cooling_demand_map` in
`preprocess_dushanbe.py` is the single point of entry — running the two
scripts regenerates all cooling results and maps automatically.

| Type | Buildings | NFA [M m²] | Cooling Demand [GWh/year] |
|---|---|---|---|
| Type Single Family | 126,059 | 25.4 | — |
| Type I (3 floors) | 41,429 | 42.0 | — |
| Type II (4 floors) | 9,138 | 26.1 | — |
| Type III (5–8 floors) | 1,557 | 19.1 | — |
| Type VI (12–20 floors) | 749 | 15.6 | — |
| Other (tertiary) | 617 | 1.5 | — |
| Office | 153 | 1.5 | — |
| Type V (10–11 floors) | 113 | 1.0 | — |
| School | 63 | 0.6 | — |
| Type IV (9 floors) | 16 | 0.2 | — |
| Hospital | 18 | 0.1 | — |

## Data

| File | Description |
|---|---|
| `Data/Dushanbe.gpkg` | Building footprints with `height`, `Area`, `Volume`, `Surface` fields; `Use` field is empty by default |
| `Data/Geofabrik_tajikistan.gpkg` | OSM extract for Tajikistan ([Geofabrik](https://download.geofabrik.de/asia/tajikistan.html)); layer `gis_osm_buildings_a_free` used for tagging |

## Requirements

```
geopandas
matplotlib
numpy
folium
branca
```

Install in a virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install geopandas matplotlib numpy folium branca
```

## Usage

```bash
.venv/bin/python3 preprocess_dushanbe.py   # spatial join + classification → Dushanbe_processed.gpkg
.venv/bin/python3 maps_dushanbe.py         # summary + static and interactive maps
```

## Building typology

### Residential (`Use = "residential"`)

| Type | Floors | Specific Heat Demand [kWh/m²·year] |
|---|---|---|
| Type Single Family | ≤ 2 | 145 |
| Type I | 3 | 74 |
| Type II | 4 | 55 |
| Type III | 5–8 | 59 |
| Type IV | 9 | 65 |
| Type V | 10–11 | 54 |
| Type VI | 12–20 | 40 |

### Tertiary (`Use = "tertiary"`)

| Type | OSM tag | Specific Heat Demand [kWh/m²·year] |
|---|---|---|
| School | `school`, `kindergarten`, `college`, `university`, `education` | 60 |
| Hospital | `hospital`, `clinic`, `doctors` | 102.5 |
| Office | `office`, `commercial`, `retail`, `industrial` | 67.5 |
| Other | all other tertiary tags | 67.5 |
