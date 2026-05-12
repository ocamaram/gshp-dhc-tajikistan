import geopandas as gpd
import os

INPUT_FILE = os.path.join("Data", "Dushanbe.gpkg")
OUTPUT_DIR = "Results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading GeoPackage...")
gdf = gpd.read_file(INPUT_FILE)
print(f"  {len(gdf)} polygons loaded. Columns: {list(gdf.columns)}")

# ── Floors ────────────────────────────────────────────────────────────────────
gdf["floors"] = (gdf["height"] / 2.5).astype(int)
gdf["floors"] = gdf["floors"].clip(lower=1)

# ── Building Type ─────────────────────────────────────────────────────────────
def assign_type(f):
    if f <= 2:
        return "Type Single Family"
    elif f == 3:
        return "Type I"
    elif f == 4:
        return "Type II"
    elif 5 <= f <= 8:
        return "Type III"
    elif f == 9:
        return "Type IV"
    elif 10 <= f <= 11:
        return "Type V"
    else:
        return "Type VI"

gdf["Type"] = gdf["floors"].apply(assign_type)

# ── Specific Heat Demand ──────────────────────────────────────────────────────
heat_demand_map = {
    "Type Single Family": 145,
    "Type I":  74,
    "Type II": 55,
    "Type III": 59,
    "Type IV": 65,
    "Type V":  54,
    "Type VI": 40,
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
