# GSHP DHC Tajikistan — Building Heat Demand Analysis (Dushanbe)

Spatial analysis of building stock heat demand in Dushanbe, Tajikistan,
based on building footprint data from a GeoPackage file.

## Scripts

### `preprocess_dushanbe.py`
Loads the raw building footprint GeoPackage (`Data/Dushanbe.gpkg`) and
computes the following fields for each building:

| Field | Description |
|---|---|
| `floors` | Number of floors estimated from building height (height / 2.5) |
| `Type` | Building typology (Single Family, Type I–VI) based on floor count |
| `Specific Heat Demand [kWh/m2·year]` | Specific heat demand assigned by typology |
| `Heated Area [m2]` | Total heated floor area (footprint area × floors) |
| `Total Heat Demand [GWh/year]` | Annual heat demand per building |

Output: `Results/Dushanbe_processed.gpkg`

---

### `maps_dushanbe.py`
Loads the processed GeoPackage and produces:

**Console summary** — building count, average floors, average heated area,
specific and total heat demand per typology.

**Static maps (PNG, 150 dpi):**
- `Types.png` — building typology with categorical colours
- `Specific_Heat_Demand.png` — specific heat demand (YlOrRd gradient)
- `Total_Heat_Demand.png` — total heat demand in GWh/year (YlOrRd gradient)

**Interactive maps (HTML, Folium/Leaflet):**
- `Types_interactive.html`
- `Specific_Heat_Demand_interactive.html`
- `Total_Heat_Demand_interactive.html`

All maps are centred on the geometric centroid of the dataset with a
configurable zoom level (`MAP_ZOOM = 1.5` by default).

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
.venv/bin/python3 preprocess_dushanbe.py   # generate processed GeoPackage
.venv/bin/python3 maps_dushanbe.py         # generate summary + maps
```

## Building typology

| Type | Floors | Specific Heat Demand [kWh/m²·year] |
|---|---|---|
| Type Single Family | ≤ 2 | 145 |
| Type I | 3 | 74 |
| Type II | 4 | 55 |
| Type III | 5–8 | 59 |
| Type IV | 9 | 65 |
| Type V | 10–11 | 54 |
| Type VI | ≥ 12 | 40 |
