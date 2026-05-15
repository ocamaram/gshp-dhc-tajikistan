import geopandas as gpd
import os

INPUT_FILE     = os.path.join("Data", "Dushanbe.gpkg")
OSM_FILE       = os.path.join("Data", "Geofabrik_tajikistan.gpkg")
OSM_LAYER      = "gis_osm_buildings_a_free"
OUTPUT_DIR     = "Results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── OSM tag → Use ──────────────────────────────────────────────────────────────
RESIDENTIAL_TAGS = {
    "house", "detached", "semidetached_house", "bungalow", "terrace",
    "apartments", "residential", "dormitory", "block",
    "yes;residential", "hotel",
}

# ── OSM tag → Type (tertiary only) ────────────────────────────────────────────
TERTIARY_TAG_TO_TYPE = {
    "school":       "School",
    "kindergarten": "School",
    "college":      "School",
    "university":   "School",
    "hospital":     "Hospital",
    "clinic":       "Hospital",
    "doctors":      "Hospital",
    "office":       "Office",
    "commercial":   "Office",
    "retail":       "Office",
    "industrial":   "Office",
    "yes":          "Other",
    "public":       "Other",
    "civic":        "Other",
    "government":   "Other",
    "mosque":       "Other",
    "church":       "Other",
    "warehouse":    "Other",
    "education":    "School",
    "roof":         "Other",
}

# ── Load input data ────────────────────────────────────────────────────────────
print("Loading GeoPackage...")
gdf = gpd.read_file(INPUT_FILE)
print(f"  {len(gdf)} polygons loaded. Columns: {list(gdf.columns)}")

# ── Floors ────────────────────────────────────────────────────────────────────
FLOOR_HEIGHT_RES = 2.6  # m — used after Use is finalised
FLOOR_HEIGHT_TER = 3.0  # m — used after Use is finalised
# Initial estimate using residential height; corrected below once Use is known
gdf["floors"] = (gdf["height"] / FLOOR_HEIGHT_RES).astype(int).clip(lower=1, upper=20)

# ── OSM spatial join to get building tag ──────────────────────────────────────
print("Loading OSM buildings...")
osm = gpd.read_file(OSM_FILE, layer=OSM_LAYER)
IGNORE_TAGS = {"construction"}
osm = osm[osm["type"].notna() & (osm["type"] != "") & ~osm["type"].isin(IGNORE_TAGS)][["type", "geometry"]]
osm = osm.to_crs(gdf.crs)
print(f"  {len(osm)} OSM buildings with explicit tag.")

# Join by centroid: for each polygon find the OSM building its centroid falls in
print("Joining with OSM data...")
centroids = gdf.copy()
centroids["geometry"] = gdf.geometry.centroid
joined = gpd.sjoin(centroids[["geometry"]], osm, how="left", predicate="within")
# Keep first match per polygon in case of duplicates
joined = joined[~joined.index.duplicated(keep="first")]
gdf["osm_type"] = joined["type"]

# ── Use: OSM where available, heuristic otherwise ─────────────────────────────
# Heuristic: residential by default; 1–2 floor buildings > 1000 m² → tertiary
AREA_THRESH_TERTIARY = 1000  # m²

def assign_use(row):
    if isinstance(row["osm_type"], str) and row["osm_type"]:
        return "residential" if row["osm_type"] in RESIDENTIAL_TAGS else "tertiary"
    if row["floors"] <= 2 and row["Area"] > AREA_THRESH_TERTIARY:
        return "tertiary"
    return "residential"

gdf["Use"] = gdf.apply(assign_use, axis=1)
n_osm_use  = (gdf["osm_type"].notna() & (gdf["osm_type"] != "")).sum()
n_heuristic = ((gdf["Use"] == "tertiary") & ~(gdf["osm_type"].notna() & (gdf["osm_type"] != ""))).sum()
print(f"  Use assigned: {n_osm_use} from OSM tag, {n_heuristic} tertiary by area heuristic, rest residential by default.")

# ── Tagging: OSM tag where available, default otherwise ───────────────────────
def default_tagging(row):
    if row["Use"] == "residential":
        return "house" if row["floors"] <= 2 else "apartments"
    return "yes"

gdf["Tagging"] = gdf.apply(
    lambda row: row["osm_type"] if isinstance(row["osm_type"], str) and row["osm_type"]
                else default_tagging(row),
    axis=1,
)
gdf.drop(columns=["osm_type"], inplace=True)

n_osm = (gdf["Tagging"] != gdf.apply(default_tagging, axis=1)).sum()
print(f"  {n_osm} polygons tagged from OSM; rest use default.")

# ── Use: derived from Tagging ─────────────────────────────────────────────────
gdf["Use"] = gdf["Tagging"].apply(
    lambda tag: "residential" if tag in RESIDENTIAL_TAGS else "tertiary"
)

# ── Floors (corrected per Use) ─────────────────────────────────────────────────
gdf["floors"] = gdf.apply(
    lambda row: int(
        (row["height"] / (FLOOR_HEIGHT_RES if row["Use"] == "residential" else FLOOR_HEIGHT_TER))
    ),
    axis=1,
).clip(lower=1, upper=20)

# ── Type ───────────────────────────────────────────────────────────────────────
def assign_type_residential(floors):
    if floors <= 2:    return "Type Single Family"
    elif floors == 3:  return "Type I"
    elif floors == 4:  return "Type II"
    elif floors <= 8:  return "Type III"
    elif floors == 9:  return "Type IV"
    elif floors <= 11: return "Type V"
    else:              return "Type VI"

def assign_type(row):
    if row["Use"] == "residential":
        return assign_type_residential(row["floors"])
    # Tertiary: Tagging drives Type; floors only affect area and heat demand
    return TERTIARY_TAG_TO_TYPE.get(row["Tagging"], "Other")

gdf["Type"] = gdf.apply(assign_type, axis=1)

# ── Specific Heat Demand ──────────────────────────────────────────────────────
heat_demand_map = {
    "Type Single Family": 145,
    "Type I":    74,
    "Type II":   55,
    "Type III":  59,
    "Type IV":   65,
    "Type V":    54,
    "Type VI":   40,
    "School":    72.0,
    "Hospital":  123.0,
    "Office":    81.0,
    "Other":     81.0,
}
gdf["Specific Heat Demand [kWh/m2·year]"] = gdf["Type"].map(heat_demand_map)

# ── Specific Cooling Demand ───────────────────────────────────────────────────
# Preliminary values for Dushanbe (~1,300–1,500 CDD base 18°C).
# Residential and School assumed unrefrigerated (0). Tertiary values are
# order-of-magnitude estimates pending measured or modelled data.
cooling_demand_map = {
    "Type Single Family": 0,
    "Type I":    0,
    "Type II":   0,
    "Type III":  0,
    "Type IV":   0,
    "Type V":    0,
    "Type VI":   0,
    "School":    0,
    "Hospital":  90.0,
    "Office":    45.0,
    "Other":     40.0,
}
gdf["Specific Cooling Demand [kWh/m2·year]"] = gdf["Type"].map(cooling_demand_map)

# ── Conditioned Area, Heat & Cooling Demand ───────────────────────────────────
GFA_TO_NFA = 0.70
gdf["Heated Area [m2]"]  = gdf["Area"] * gdf["floors"] * GFA_TO_NFA
gdf["Cooling Area [m2]"] = gdf["Heated Area [m2]"]

gdf["Total Heat Demand [GWh/year]"] = (
    gdf["Specific Heat Demand [kWh/m2·year]"] * gdf["Heated Area [m2]"]
) / 1e6
gdf["Total Cooling Demand [GWh/year]"] = (
    gdf["Specific Cooling Demand [kWh/m2·year]"] * gdf["Cooling Area [m2]"]
) / 1e6

# ── Save processed GeoPackage ─────────────────────────────────────────────────
out_gpkg = os.path.join(OUTPUT_DIR, "Dushanbe_processed.gpkg")
gdf.to_file(out_gpkg, driver="GPKG")
print(f"File saved: {out_gpkg}")
print("✓ Preprocessing complete.")
