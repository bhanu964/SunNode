import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

output_png = "/Users/bhanuprasad/.gemini/antigravity/brain/fd0a8b34-ef7b-47ae-9d33-8e2736284ecd/SuryaGrid_DynamicWorld_1km_2km_Suitability_Presentation.png"
os.makedirs(os.path.dirname(output_png), exist_ok=True)

df = pd.read_csv("data/processed/substation_land_suitability_dynamic_world_1k_2k.csv")

boundary_geojson = "data/processed/telangana_boundary.geojson"
boundary_coords = []
if os.path.exists(boundary_geojson):
    with open(boundary_geojson) as f:
        bg = json.load(f)
        feats = bg.get('features', [])
        if feats:
            geom = feats[0].get('geometry', {})
            coords = geom.get('coordinates', [])
            if geom.get('type') == 'Polygon':
                boundary_coords = [coords[0]]
            elif geom.get('type') == 'MultiPolygon':
                boundary_coords = [poly[0] for poly in coords]

fig = plt.figure(figsize=(26, 13), dpi=200, facecolor='#0B0F19')
gs = fig.add_gridspec(2, 3, width_ratios=[1.1, 1.0, 1.1], height_ratios=[1.0, 1.0], wspace=0.22, hspace=0.26)

DARK_BG = '#0B0F19'
CARD_BG = '#151D2F'
BORDER_COL = '#23324D'
GREEN = '#10B981'    # Primary Usable
YELLOW = '#EAB308'   # Crops / Plants / Agriculture
RED = '#EF4444'      # Excluded (Built, Water+30m FTL, Forest)
CYAN = '#06B6D4'     # 1 km buffer
AMBER = '#F59E0B'    # 2 km buffer
ORANGE = '#F97316'   # State boundary
GOLD = '#FFD700'     # Substation

# -----------------------------------------------------------------------------
# PANEL 1 (Left): Telangana Map Color-Coded by Dynamic World Land Suitability
# -----------------------------------------------------------------------------
ax_map = fig.add_subplot(gs[:, 0], facecolor=CARD_BG)
ax_map.set_title("TELANGANA GRID: DYNAMIC WORLD 1KM & 2KM SUITABILITY\n391 Substations Color-Coded by Score (Strictly Inside State Boundary)", 
                 color='#F8FAFC', fontsize=13.5, fontweight='bold', pad=15)

if boundary_coords:
    for ring in boundary_coords:
        xs, ys = zip(*ring)
        ax_map.plot(xs, ys, color=ORANGE, linewidth=2.5, label='Telangana State Border')
        ax_map.fill(xs, ys, color='#1E293B', alpha=0.45)

tier_groups = [
    ('GREEN', GREEN, 'Prime Direct Solar (Score >=65) [102 SS]', 32),
    ('YELLOW', YELLOW, 'Agri / Crop Land Conversion (Score 35-64) [228 SS]', 26),
    ('RED', RED, 'Restricted / Urban / Water / Forest [61 SS]', 30)
]

for code, color, label_text, size in tier_groups:
    subset = df[df['Color Code'] == code]
    if not subset.empty:
        ax_map.scatter(subset['Longitude'], subset['Latitude'], color=color, s=size, alpha=0.9,
                       edgecolors='#FFFFFF', linewidth=0.5, label=label_text, zorder=5)

ax_map.set_xlim(77.0, 81.5)
ax_map.set_ylim(15.7, 19.9)
ax_map.set_xlabel("Longitude (°E)", color='#94A3B8', fontsize=11)
ax_map.set_ylabel("Latitude (°N)", color='#94A3B8', fontsize=11)
ax_map.tick_params(colors='#94A3B8')
for spine in ax_map.spines.values():
    spine.set_color(BORDER_COL)

ax_map.legend(loc='lower right', facecolor='#0F172A', edgecolor=BORDER_COL, fontsize=9.5, labelcolor='#F1F5F9')

ax_map.annotate("Narayanguda (132 kV)\n(100% Built-up / RED)", xy=(78.49, 17.39), xytext=(77.2, 16.4),
                color=RED, fontsize=9.5, fontweight='bold',
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.5),
                bbox=dict(boxstyle="round,pad=0.3", fc="#1E293B", ec=RED, lw=1))

ax_map.annotate("K.M.Pally (220 kV)\n(Top Score: 84.4 / GREEN)", xy=(78.92, 16.76), xytext=(79.5, 16.1),
                color=GREEN, fontsize=9.5, fontweight='bold',
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5),
                bbox=dict(boxstyle="round,pad=0.3", fc="#1E293B", ec=GREEN, lw=1))

# -----------------------------------------------------------------------------
# PANEL 2 (Center): Concentric 1km & 2km Feeder Architecture & Color Legend
# -----------------------------------------------------------------------------
ax_buf = fig.add_subplot(gs[:, 1], facecolor=CARD_BG)
ax_buf.set_title("CONCENTRIC 1 KM & 2 KM SOLAR FEEDER ARCHITECTURE\nChallenge 10: Dynamic World 10m Multi-Spectral Masking", 
                 color='#F8FAFC', fontsize=13.5, fontweight='bold', pad=15)

# Outer 2km circle (Amber)
c2 = patches.Circle((0, 0), 4.8, facecolor='#F59E0B', alpha=0.12, edgecolor=AMBER, linewidth=3, linestyle='--', label='Extended 2 km Limit')
# Inner 1km circle (Cyan)
c1 = patches.Circle((0, 0), 2.4, facecolor='#06B6D4', alpha=0.22, edgecolor=CYAN, linewidth=3.5, label='Primary 1 km Limit')
# Substation center
c0 = patches.Circle((0, 0), 0.35, facecolor=GOLD, edgecolor='#FFFFFF', linewidth=2, zorder=10)

ax_buf.add_patch(c2)
ax_buf.add_patch(c1)
ax_buf.add_patch(c0)

# Radii indicator lines
ax_buf.annotate("", xy=(2.4, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="<->", color=CYAN, lw=2.5))
ax_buf.text(1.2, 0.25, "R = 1 km\n(776 ac / 314 ha)", color=CYAN, fontsize=10.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle="round,pad=0.2", fc="#0F172A", ec=CYAN, lw=0.8))

ax_buf.annotate("", xy=(4.8, 0), xytext=(2.4, 0), arrowprops=dict(arrowstyle="<->", color=AMBER, lw=2.5))
ax_buf.text(3.6, 0.25, "R = 2 km\n(3,103 ac / 1,256 ha)", color=AMBER, fontsize=10.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle="round,pad=0.2", fc="#0F172A", ec=AMBER, lw=0.8))

ax_buf.text(0, -0.65, "GRID SUBSTATION\n(Step-down Bus)", color=GOLD, fontsize=11, fontweight='bold', ha='center')

# Color Class Legend Box
color_box_text = (
    "SATELLITE COLOR CLASSIFICATION RULES:\n\n"
    "[GREEN] Primary Usable Land (Ideal for Solar)\n"
    "  * Bare ground, scrub, open grass\n"
    "  * Slope <= 5° (SRTM 30m) | Excludes water+30m\n"
    "  * Contiguous patch >= 5 acres (~20,235 m²)\n\n"
    "[YELLOW] Crops / Agriculture / Plants\n"
    "  * Cultivated cropland & light vegetation\n"
    "  * Slope <= 5° | Prime target for Agro-PV / PM-KUSUM\n"
    "  * Requires land-use NOC / conversion\n\n"
    "[RED] Strictly Excluded (Unusable)\n"
    "  * Built-up settlements, roads, towns\n"
    "  * Water bodies / lakes + 30m FTL buffer\n"
    "  * Deep dense tree forest | Steep slope > 5°"
)
ax_buf.text(-5.0, -3.2, color_box_text, color='#F8FAFC', fontsize=9.2,
            bbox=dict(boxstyle="round,pad=0.5", fc="#0F172A", ec='#38BDF8', lw=1.5))

ax_buf.set_xlim(-5.6, 5.6)
ax_buf.set_ylim(-5.6, 5.6)
ax_buf.set_aspect('equal')
ax_buf.axis('off')

# -----------------------------------------------------------------------------
# PANEL 3 (Top Right): 1 km Land Cover Breakdown (5 Sample Benchmarks)
# -----------------------------------------------------------------------------
ax_comp = fig.add_subplot(gs[0, 2], facecolor=CARD_BG)
ax_comp.set_title("1 KM DYNAMIC WORLD LAND BREAKDOWN (%)\nSample Benchmarks: Green (Usable) vs Yellow (Agri) vs Red (Excluded)", 
                  color='#F8FAFC', fontsize=12.0, fontweight='bold', pad=12)

benchmarks = [
    ("K.M.Pally (220kV)", 34.2, 40.1, 13.9 + 0.0 + 3.4 + 7.1),
    ("Ganeshpahad (132kV)", 52.1, 26.5, 19.0 + 0.2 + 0.3 + 1.0),
    ("Peddashankarampet", 33.0, 18.7, 4.8 + 9.2 + 23.8 + 15.1),
    ("Medaram (400kV)", 0.0, 12.7, 42.4 + 10.1 + 14.5 + 5.3),
    ("Narayanguda (132kV)", 0.0, 0.0, 100.0)
]

labels = [b[0] for b in benchmarks]
usable_vals = [b[1] for b in benchmarks]
crops_vals = [b[2] for b in benchmarks]
excluded_vals = [100.0 - (u + c) for u, c in zip(usable_vals, crops_vals)]

y_pos = np.arange(len(labels))
bar_height = 0.55

p1 = ax_comp.barh(y_pos, usable_vals, bar_height, color=GREEN, label='Green: Direct Usable (>=5ac)')
p2 = ax_comp.barh(y_pos, crops_vals, bar_height, left=usable_vals, color=YELLOW, label='Yellow: Crops / Agri')
p3 = ax_comp.barh(y_pos, excluded_vals, bar_height, left=np.array(usable_vals)+np.array(crops_vals), color=RED, label='Red: Excluded (Built/Water/Forest)')

ax_comp.set_yticks(y_pos)
ax_comp.set_yticklabels(labels, color='#F8FAFC', fontsize=9.5, fontweight='bold')
ax_comp.set_xlabel("1 km Buffer Area Share (%)", color='#94A3B8', fontsize=10)
ax_comp.set_xlim(0, 100)
ax_comp.tick_params(colors='#94A3B8')
for spine in ax_comp.spines.values():
    spine.set_color(BORDER_COL)

ax_comp.legend(loc='lower center', bbox_to_anchor=(0.5, -0.32), ncol=2, facecolor='#0F172A', edgecolor=BORDER_COL, fontsize=8.5, labelcolor='#F1F5F9')

# -----------------------------------------------------------------------------
# PANEL 4 (Bottom Right): Statewide Suitability Tier Breakdown & Solar Capacity
# -----------------------------------------------------------------------------
ax_pie = fig.add_subplot(gs[1, 2], facecolor=CARD_BG)
ax_pie.set_title("STATEWIDE SUITABILITY TIERS & SOLAR CAPACITY (391 SS)\nTargeting 4.5 Acres per 1 MW Capacity", 
                 color='#F8FAFC', fontsize=12.0, fontweight='bold', pad=12)

counts = [102, 228, 61]
cat_labels = [
    'GREEN: Prime Direct Solar (102 SS / 26.1%)\n1km Capacity: 3,314 MW',
    'YELLOW: Agricultural Solar (228 SS / 58.3%)\n1km Capacity w/ Crops: 32,825 MW',
    'RED: Excluded / Restricted (61 SS / 15.6%)\nUrban / Water / Forest'
]
pie_colors = [GREEN, YELLOW, RED]

wedges, texts, autotexts = ax_pie.pie(counts, colors=pie_colors, autopct='%1.1f%%', startangle=140,
                                      pctdistance=0.75, textprops=dict(color='#FFFFFF', fontweight='bold', fontsize=9.5),
                                      wedgeprops=dict(width=0.45, edgecolor=BORDER_COL, linewidth=1.5))

ax_pie.legend(wedges, cat_labels, loc='center left', bbox_to_anchor=(1.02, 0.5), facecolor='#0F172A', edgecolor=BORDER_COL, fontsize=9, labelcolor='#F1F5F9')

fig.suptitle("SuryaGrid: Dynamic World (10m) 1km & 2km Substation Land Assessment Architecture\nTelangana Energy Department Challenge 10 | Concentric Feeder Envelopes | FTL 30m Water Buffer",
             color='#38BDF8', fontsize=15.5, fontweight='bold', y=0.98)

plt.savefig(output_png, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close()
print("Saved Dynamic World presentation graphic to:", output_png)
