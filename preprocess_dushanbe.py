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
}

# ── Load input data ────────────────────────────────────────────────────────────
print("Loading GeoPackage...")
gdf = gpd.read_file(INPUT_FILE)
print(f"  {len(gdf)} polygons loaded. Columns: {list(gdf.columns)}")

# ── Floors ────────────────────────────────────────────────────────────────────
gdf["floors"] = (gdf["height"] / 2.5).astype(int).clip(lower=1)

# ── OSM spatial join to get building tag ──────────────────────────────────────
print("Loading OSM buildings...")
osm = gpd.read_file(OSM_FILE, layer=OSM_LAYER)
osm = osm[osm["type"].notna() & (osm["type"] != "")][["type", "geometry"]]
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
    "School":    60.0,
    "Hospital":  102.5,
    "Office":    67.5,
    "Other":     67.5,
}
gdf["Specific Heat Demand [kWh/m2·year]"] = gdf["Type"].map(heat_demand_map)

# ── Heated Area & Total Heat Demand ───────────────────────────────────────────
gdf["Heated Area [m2]"] = gdf["Area"] * gdf["floors"]
gdf["Total Heat Demand [GWh/year]"] = (
    gdf["Specific Heat Demand [kWh/m2·year]"] * gdf["Heated Area [m2]"]
) / 1e6

# ── Save processed GeoPackage ─────────────────────────────────────────────────
out_gpkg = os.path.join(OUTPUT_DIR, "Dushanbe_processed.gpkg")
gdf.to_file(out_gpkg, driver="GPKG")
print(f"File saved: {out_gpkg}")
print("✓ Preprocessing complete.")
