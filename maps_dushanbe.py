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
COOLMAP_COLORS = ["#ffffff", "#93c5fd", "#3b82f6", "#1d4ed8", "#1e3a8a"]
HEATMAP_CMAP   = mcolors.LinearSegmentedColormap.from_list("orange_red", HEATMAP_COLORS)
COOLMAP_CMAP   = mcolors.LinearSegmentedColormap.from_list("blue_cold",  COOLMAP_COLORS)

# ── Map display parameters ────────────────────────────────────────────────────
CENTER_LAT = 38.559732
CENTER_LON = 68.771771
MAP_ZOOM   = 2.0
FOLIUM_ZOOM = 14

# ── Load processed data ───────────────────────────────────────────────────────
print("Loading processed GeoPackage...")
gdf = gpd.read_file(INPUT_FILE)
print(f"  {len(gdf)} polygons loaded.")

COOLING_AVAILABLE = gdf["Specific Cooling Demand [kWh/m2·year]"].notna().any()
if not COOLING_AVAILABLE:
    print("  Note: cooling demand values not set — cooling maps will be skipped.")

TYPE_ORDER = [
    "Type Single Family", "Type I", "Type II", "Type III",
    "Type IV", "Type V", "Type VI",
    "School", "Hospital", "Office", "Other",
]
TYPE_COLORS = {
    "Type Single Family": "#a8d5a2",
    "Type I":   "#4da6e8",
    "Type II":  "#2979c4",
    "Type III": "#f5c242",
    "Type IV":  "#f08c30",
    "Type V":   "#e05a1a",
    "Type VI":  "#9b1a1a",
    "School":   "#b39ddb",
    "Hospital": "#f48fb1",
    "Office":   "#4db6ac",
    "Other":    "#90a4ae",
}

# ── Compute map extent (center + zoom) ────────────────────────────────────────
center_proj = gpd.GeoSeries(
    gpd.points_from_xy([CENTER_LON], [CENTER_LAT]), crs="EPSG:4326"
).to_crs(gdf.crs).iloc[0]
cx, cy = center_proj.x, center_proj.y

bounds = gdf.total_bounds
hw = (bounds[2] - bounds[0]) / 2 / MAP_ZOOM
hh = (bounds[3] - bounds[1]) / 2 / MAP_ZOOM

# ── Summary ───────────────────────────────────────────────────────────────────
agg = dict(
    Buildings=("Type", "count"),
    Avg_floors=("floors", "mean"),
    Avg_area=("Heated Area [m2]", "mean"),
    SHD=("Specific Heat Demand [kWh/m2·year]", "first"),
    Total_heat=("Total Heat Demand [GWh/year]", "sum"),
)
if COOLING_AVAILABLE:
    agg["SCD"]        = ("Specific Cooling Demand [kWh/m2·year]", "first")
    agg["Total_cool"] = ("Total Cooling Demand [GWh/year]", "sum")

summary = gdf.groupby("Type").agg(**agg).reindex(TYPE_ORDER).round(2)
summary.index.name = "Type"
col_names = [
    "No. Buildings", "Avg. Floors", "Average Heated Area [m²]",
    "Specific Heat Demand [kWh/m²·year]", "Total Heat Demand [GWh/year]",
]
if COOLING_AVAILABLE:
    col_names += ["Specific Cooling Demand [kWh/m²·year]", "Total Cooling Demand [GWh/year]"]
summary.columns = col_names

print("\n" + "═" * 90)
print("  SUMMARY BY BUILDING TYPE — DUSHANBE")
print("═" * 90)
print(summary.to_string())
print("─" * 90)
print(f"  TOTAL buildings : {len(gdf):,}")
print(f"  Total Heat Demand  : {gdf['Total Heat Demand [GWh/year]'].sum():.1f} GWh/year")
if COOLING_AVAILABLE:
    print(f"  Total Cooling Demand: {gdf['Total Cooling Demand [GWh/year]'].sum():.1f} GWh/year")
print("═" * 90)


# ── Helper: apply zoom/center to axis ─────────────────────────────────────────
def apply_zoom(ax):
    ax.set_xlim(cx - hw, cx + hw)
    ax.set_ylim(cy - hh, cy + hh)


# ── Helper: static choropleth PNG ─────────────────────────────────────────────
def plot_heatmap(gdf, column, title, filename, cbar_label, cmap):
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


# ── Helper: interactive choropleth HTML ──────────────────────────────────────
center = [CENTER_LAT, CENTER_LON]

def interactive_choropleth(gdf_web, column, filename, caption, colors, aliases=None):
    vmin = gdf_web[column].min()
    vmax = gdf_web[column].max()
    colormap = bcm.LinearColormap(colors, vmin=vmin, vmax=vmax, caption=caption)
    m = folium.Map(location=center, zoom_start=FOLIUM_ZOOM,
                   tiles="CartoDB positron", prefer_canvas=True)

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


# ══════════════════════════════════════════════════════════════════════════════
# Prepare simplified web GeoDataFrame
# ══════════════════════════════════════════════════════════════════════════════
gdf_web = gdf.copy()
gdf_web["geometry"] = gdf_web["geometry"].simplify(tolerance=5)
gdf_web = gdf_web.to_crs(epsg=4326)

tooltip_cols = [
    "Type", "floors",
    "Heated Area [m2]", "Specific Heat Demand [kWh/m2·year]", "Total Heat Demand [GWh/year]",
    "Cooling Area [m2]", "Specific Cooling Demand [kWh/m2·year]", "Total Cooling Demand [GWh/year]",
    "geometry",
]
tooltip_fields   = [c for c in tooltip_cols if c != "geometry"]
tooltip_aliases  = [
    "Type:", "Floors:",
    "Heated Area [m²]:", "Specific Heat Demand [kWh/m²·year]:", "Total Heat Demand [GWh/year]:",
    "Cooling Area [m²]:", "Specific Cooling Demand [kWh/m²·year]:", "Total Cooling Demand [GWh/year]:",
]


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
# MAPS 2–3 — Heat Demand (static PNG)
# ══════════════════════════════════════════════════════════════════════════════
plot_heatmap(gdf, "Specific Heat Demand [kWh/m2·year]",
             "Specific Heat Demand — Dushanbe",
             "Specific_Heat_Demand.png", "Specific Heat Demand [kWh/m²·year]",
             HEATMAP_CMAP)

plot_heatmap(gdf, "Total Heat Demand [GWh/year]",
             "Total Heat Demand — Dushanbe",
             "Total_Heat_Demand.png", "Total Heat Demand [GWh/year]",
             HEATMAP_CMAP)


# ══════════════════════════════════════════════════════════════════════════════
# MAPS 4–5 — Cooling Demand (static PNG) — only when data available
# ══════════════════════════════════════════════════════════════════════════════
if COOLING_AVAILABLE:
    plot_heatmap(gdf, "Specific Cooling Demand [kWh/m2·year]",
                 "Specific Cooling Demand — Dushanbe",
                 "Specific_Cooling_Demand.png", "Specific Cooling Demand [kWh/m²·year]",
                 COOLMAP_CMAP)

    plot_heatmap(gdf, "Total Cooling Demand [GWh/year]",
                 "Total Cooling Demand — Dushanbe",
                 "Total_Cooling_Demand.png", "Total Cooling Demand [GWh/year]",
                 COOLMAP_CMAP)
else:
    print("Cooling maps skipped (no cooling demand data).")


# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE MAPS (Folium / HTML)
# ══════════════════════════════════════════════════════════════════════════════
print("\nGenerating interactive maps...")

# ── Interactive Map 1 — Building Types ───────────────────────────────────────
m1 = folium.Map(location=center, zoom_start=FOLIUM_ZOOM,
                tiles="CartoDB positron", prefer_canvas=True)

def style_type(feature):
    t = feature["properties"]["Type"]
    return {"fillColor": TYPE_COLORS.get(t, "#cccccc"), "color": "white",
            "weight": 0.3, "fillOpacity": 0.75}

folium.GeoJson(
    gdf_web[tooltip_cols],
    style_function=style_type,
    tooltip=folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
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


# ── Interactive Maps 2–3 — Heat Demand ───────────────────────────────────────
interactive_choropleth(
    gdf_web, "Specific Heat Demand [kWh/m2·year]",
    "Specific_Heat_Demand_interactive.html",
    "Specific Heat Demand [kWh/m²·year]", HEATMAP_COLORS,
    aliases=["Type:", "Floors:", "Specific Heat Demand [kWh/m²·year]:"],
)
interactive_choropleth(
    gdf_web, "Total Heat Demand [GWh/year]",
    "Total_Heat_Demand_interactive.html",
    "Total Heat Demand [GWh/year]", HEATMAP_COLORS,
    aliases=["Type:", "Floors:", "Total Heat Demand [GWh/year]:"],
)

# ── Interactive Maps 4–5 — Cooling Demand ────────────────────────────────────
if COOLING_AVAILABLE:
    interactive_choropleth(
        gdf_web, "Specific Cooling Demand [kWh/m2·year]",
        "Specific_Cooling_Demand_interactive.html",
        "Specific Cooling Demand [kWh/m²·year]", COOLMAP_COLORS,
        aliases=["Type:", "Floors:", "Specific Cooling Demand [kWh/m²·year]:"],
    )
    interactive_choropleth(
        gdf_web, "Total Cooling Demand [GWh/year]",
        "Total_Cooling_Demand_interactive.html",
        "Total Cooling Demand [GWh/year]", COOLMAP_COLORS,
        aliases=["Type:", "Floors:", "Total Cooling Demand [GWh/year]:"],
    )
else:
    print("Cooling interactive maps skipped (no cooling demand data).")

print("\n✓ Process complete. Results in 'Results/' folder.")
