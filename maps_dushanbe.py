import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import numpy as np
import os
import folium
import branca.colormap as bcm

INPUT_FILE = os.path.join("Results", "Dushanbe_processed.gpkg")
OUTPUT_DIR = "Results"

HEATMAP_COLORS = ["#FFB347", "#E84000", "#C80000", "#9B0000", "#7F0000"]
HEATMAP_CMAP = mcolors.LinearSegmentedColormap.from_list("orange_red", HEATMAP_COLORS)

# ── Map display parameters ────────────────────────────────────────────────────
# Center coordinates (WGS84 lat/lon)
CENTER_LAT = 38.559732
CENTER_LON = 68.771771
# MAP_ZOOM > 1 zooms in (1.5 = show 67% of full extent); 1.0 = show full extent
MAP_ZOOM = 2.0
FOLIUM_ZOOM = 14

# ── Load processed data ───────────────────────────────────────────────────────
print("Loading processed GeoPackage...")
gdf = gpd.read_file(INPUT_FILE)
print(f"  {len(gdf)} polygons loaded.")

TYPE_ORDER = [
    "Type Single Family", "Type I", "Type II", "Type III",
    "Type IV", "Type V", "Type VI"
]
TYPE_COLORS = {
    "Type Single Family": "#a8d5a2",
    "Type I":   "#4da6e8",
    "Type II":  "#2979c4",
    "Type III": "#f5c242",
    "Type IV":  "#f08c30",
    "Type V":   "#e05a1a",
    "Type VI":  "#9b1a1a",
}
heat_demand_map = {
    "Type Single Family": 145,
    "Type I":  74,
    "Type II": 55,
    "Type III": 59,
    "Type IV": 65,
    "Type V":  54,
    "Type VI": 40,
}

# ── Compute map extent (center + zoom) ────────────────────────────────────────
# Convert center from WGS84 to the projected CRS of the data
center_proj = gpd.GeoSeries(
    gpd.points_from_xy([CENTER_LON], [CENTER_LAT]), crs="EPSG:4326"
).to_crs(gdf.crs).iloc[0]
cx, cy = center_proj.x, center_proj.y

bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
hw = (bounds[2] - bounds[0]) / 2 / MAP_ZOOM
hh = (bounds[3] - bounds[1]) / 2 / MAP_ZOOM

# ── Summary ───────────────────────────────────────────────────────────────────
summary = gdf.groupby("Type").agg(
    Buildings=("Type", "count"),
    Avg_floors=("floors", "mean"),
    Avg_heated_area=("Heated Area [m2]", "mean"),
    Specific_demand=("Specific Heat Demand [kWh/m2·year]", "first"),
    Total_demand_GWh=("Total Heat Demand [GWh/year]", "sum"),
).reindex(TYPE_ORDER).round(2)
summary.index.name = "Type"
summary.columns = [
    "No. Buildings", "Avg. Floors", "Average Heated Area [m²]",
    "Specific Heat Demand [kWh/m²·year]", "Total Heat Demand [GWh/year]"
]

print("\n" + "═" * 80)
print("  SUMMARY BY BUILDING TYPE — DUSHANBE")
print("═" * 80)
print(summary.to_string())
print("─" * 80)
print(f"  TOTAL buildings: {len(gdf):,}  |  Total Heat Demand: {gdf['Total Heat Demand [GWh/year]'].sum():.1f} GWh/year")
print("═" * 80)


# ── Helper: apply zoom/center to axis ─────────────────────────────────────────
def apply_zoom(ax):
    ax.set_xlim(cx - hw, cx + hw)
    ax.set_ylim(cy - hh, cy + hh)


# ══════════════════════════════════════════════════════════════════════════════
# MAP 1 — Building Types (static PNG)
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(14, 10))
for t in TYPE_ORDER:
    subset = gdf[gdf["Type"] == t]
    if not subset.empty:
        subset.plot(ax=ax, color=TYPE_COLORS[t], linewidth=0.3, edgecolor="white")

patches = [
    mpatches.Patch(color=TYPE_COLORS[t], label=t)
    for t in TYPE_ORDER if t in gdf["Type"].values
]
ax.legend(handles=patches, title="Building Type", loc="lower left",
          fontsize=8, title_fontsize=9, framealpha=0.9)
ax.set_title("Building Typology — Dushanbe", fontsize=15, fontweight="bold", pad=12)
apply_zoom(ax)
ax.set_axis_off()
plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "Types.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Map 'Types.png' saved.")


# ══════════════════════════════════════════════════════════════════════════════
# MAP 2 — Specific Heat Demand [kWh/m²·year]  (YlOrRd gradient)
# ══════════════════════════════════════════════════════════════════════════════
# MAP 3 — Total Heat Demand [GWh/year]  (YlOrRd gradient)
# ══════════════════════════════════════════════════════════════════════════════
def plot_heatmap(gdf, column, title, filename, cbar_label, cmap=HEATMAP_CMAP):
    fig, ax = plt.subplots(figsize=(14, 10))
    vmin, vmax = gdf[column].min(), gdf[column].max()
    gdf.plot(ax=ax, column=column, cmap=cmap, linewidth=0.2,
             edgecolor="white", vmin=vmin, vmax=vmax, legend=False)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, shrink=0.7)
    cbar.set_label(cbar_label, fontsize=9)
    ax.set_title(title, fontsize=15, fontweight="bold", pad=12)
    apply_zoom(ax)
    ax.set_axis_off()
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, filename), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Map '{filename}' saved.")

plot_heatmap(
    gdf,
    column="Specific Heat Demand [kWh/m2·year]",
    title="Specific Heat Demand — Dushanbe",
    filename="Specific_Heat_Demand.png",
    cbar_label="Specific Heat Demand [kWh/m²·year]",
)

plot_heatmap(
    gdf,
    column="Total Heat Demand [GWh/year]",
    title="Total Heat Demand — Dushanbe",
    filename="Total_Heat_Demand.png",
    cbar_label="Total Heat Demand [GWh/year]",
)


# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE MAPS (Folium / HTML)
# ══════════════════════════════════════════════════════════════════════════════
print("\nGenerating interactive maps...")

gdf_web = gdf.copy()
gdf_web["geometry"] = gdf_web["geometry"].simplify(tolerance=5)
gdf_web = gdf_web.to_crs(epsg=4326)

center = [CENTER_LAT, CENTER_LON]

# ── Interactive Map 1 — Building Types ───────────────────────────────────────
cols = ["Type", "floors", "Heated Area [m2]",
        "Specific Heat Demand [kWh/m2·year]", "Total Heat Demand [GWh/year]", "geometry"]

m1 = folium.Map(location=center, zoom_start=FOLIUM_ZOOM, tiles="CartoDB positron", prefer_canvas=True)

def style_type(feature):
    t = feature["properties"]["Type"]
    return {"fillColor": TYPE_COLORS.get(t, "#cccccc"), "color": "white",
            "weight": 0.3, "fillOpacity": 0.75}

folium.GeoJson(
    gdf_web[cols],
    style_function=style_type,
    tooltip=folium.GeoJsonTooltip(
        fields=["Type", "floors", "Heated Area [m2]",
                "Specific Heat Demand [kWh/m2·year]", "Total Heat Demand [GWh/year]"],
        aliases=["Type:", "Floors:", "Heated Area [m²]:",
                 "Specific Heat Demand [kWh/m²·year]:", "Total Heat Demand [GWh/year]:"],
        localize=True,
    ),
).add_to(m1)

legend_html = (
    "<div style='position:fixed;bottom:30px;left:30px;z-index:1000;background:white;"
    "padding:10px;border-radius:6px;font-size:12px;box-shadow:2px 2px 6px rgba(0,0,0,0.3)'>"
    "<b>Building Type</b><br>"
)
for t in TYPE_ORDER:
    if t in gdf["Type"].values:
        legend_html += (
            f"<span style='background:{TYPE_COLORS[t]};display:inline-block;"
            f"width:14px;height:14px;margin-right:5px;border-radius:2px'></span>{t}<br>"
        )
legend_html += "</div>"
m1.get_root().html.add_child(folium.Element(legend_html))
m1.save(os.path.join(OUTPUT_DIR, "Types_interactive.html"))
print("Interactive map 'Types_interactive.html' saved.")


# ── Helper: interactive choropleth with YlOrRd gradient ──────────────────────
def interactive_choropleth(gdf_web, column, filename, caption,
                            colors=None, aliases=None):
    if colors is None:
        colors = HEATMAP_COLORS
    vmin = gdf_web[column].min()
    vmax = gdf_web[column].max()
    colormap = bcm.LinearColormap(colors, vmin=vmin, vmax=vmax, caption=caption)

    m = folium.Map(location=center, zoom_start=FOLIUM_ZOOM, tiles="CartoDB positron", prefer_canvas=True)

    def style_fn(feature):
        val = feature["properties"][column]
        return {"fillColor": colormap(val), "color": "white",
                "weight": 0.2, "fillOpacity": 0.75}

    tip_aliases = aliases or ["Type:", "Floors:", caption + ":"]
    folium.GeoJson(
        gdf_web[["Type", "floors", column, "geometry"]],
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["Type", "floors", column],
            aliases=tip_aliases,
            localize=True,
        ),
    ).add_to(m)
    colormap.add_to(m)
    m.save(os.path.join(OUTPUT_DIR, filename))
    print(f"Interactive map '{filename}' saved.")


# ── Interactive Map 2 — Specific Heat Demand ─────────────────────────────────
interactive_choropleth(
    gdf_web,
    column="Specific Heat Demand [kWh/m2·year]",
    filename="Specific_Heat_Demand_interactive.html",
    caption="Specific Heat Demand [kWh/m²·year]",
    aliases=["Type:", "Floors:", "Specific Heat Demand [kWh/m²·year]:"],
)

# ── Interactive Map 3 — Total Heat Demand ────────────────────────────────────
interactive_choropleth(
    gdf_web,
    column="Total Heat Demand [GWh/year]",
    filename="Total_Heat_Demand_interactive.html",
    caption="Total Heat Demand [GWh/year]",
    aliases=["Type:", "Floors:", "Total Heat Demand [GWh/year]:"],
)

print("\n✓ Process complete. Results in 'Results/' folder.")
