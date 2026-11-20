import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json

output_png = "/Users/bhanuprasad/.gemini/antigravity/brain/fd0a8b34-ef7b-47ae-9d33-8e2736284ecd/SuryaGrid_5km_Substation_Land_Suitability_Presentation.png"
os.makedirs(os.path.dirname(output_png), exist_ok=True)

df = pd.read_csv("data/processed/tgrac_substations_official.csv")

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

fig = plt.figure(figsize=(24, 12), dpi=200, facecolor='#0B0F19')
gs = fig.add_gridspec(2, 3, width_ratios=[1.1, 1.0, 1.1], height_ratios=[1.0, 1.0], wspace=0.22, hspace=0.25)

DARK_BG = '#0B0F19'
CARD_BG = '#151D2F'
BORDER_COL = '#23324D'
CYAN = '#06B6D4'     # 0-3 km
AMBER = '#F59E0B'    # 3-5 km
GREEN = '#10B981'    # Usable land
RED = '#EF4444'      # Built-up / Constrained
BLUE = '#38BDF8'     # Water
ORANGE = '#F97316'   # State boundary
GOLD = '#FFD700'     # Substations

# -----------------------------------------------------------------------------
# PANEL 1 (Left): Statewide Telangana Map & 391 Substations (Confined to Boundary)
# -----------------------------------------------------------------------------
ax_map = fig.add_subplot(gs[:, 0], facecolor=CARD_BG)
ax_map.set_title("TELANGANA STATEWIDE ELECTRICAL GRID (391 SUBSTATIONS)\nStrictly Confined to State Boundary (No Ocean / External Borders)", 
                 color='#F8FAFC', fontsize=13.5, fontweight='bold', pad=15)

if boundary_coords:
    for ring in boundary_coords:
        xs, ys = zip(*ring)
        ax_map.plot(xs, ys, color=ORANGE, linewidth=2.5, label='Telangana State Border')
        ax_map.fill(xs, ys, color='#1E293B', alpha=0.45)

categories = [
    ('FULLY CLEAR (0-5 km Prime Solar Zone)', GREEN, 'Fully Clear (64.2% / 251 SS)', 30),
    ('MODERATE CLEARANCE (Selective Parcel Scouting)', AMBER, 'Moderate (14.8% / 58 SS)', 24),
    ('RESTRICTED / HEAVY URBAN-WATER CONSTRAINTS', RED, 'Restricted/Urban (11.3% / 44 SS)', 28),
    ('CLEAR (Outer 3-5 km Preferred)', '#A855F7', 'Outer 3-5km Clear (5.6% / 22 SS)', 22),
    ('CLEAR (Immediate 0-3 km Preferred)', CYAN, 'Inner 0-3km Clear (4.1% / 16 SS)', 22)
]

for cat_name, color, label_text, size in categories:
    subset = df[df['Overall Clearance (0-5 km)'] == cat_name]
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

ax_map.annotate("Hyderabad Urban Core\n(Restricted Urban)", xy=(78.48, 17.38), xytext=(77.2, 16.5),
                color=RED, fontsize=9.5, fontweight='bold',
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.5),
                bbox=dict(boxstyle="round,pad=0.3", fc="#1E293B", ec=RED, lw=1))

ax_map.annotate("Medaram (400 kV)\n(Prime Solar Basin)", xy=(79.23, 18.71), xytext=(79.5, 19.4),
                color=GREEN, fontsize=9.5, fontweight='bold',
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5),
                bbox=dict(boxstyle="round,pad=0.3", fc="#1E293B", ec=GREEN, lw=1))

# -----------------------------------------------------------------------------
# PANEL 2 (Center): Concentric 5 km Buffer Model (0-3 km & 3-5 km Architecture)
# -----------------------------------------------------------------------------
ax_buf = fig.add_subplot(gs[:, 1], facecolor=CARD_BG)
ax_buf.set_title("SUBSTATION 5 KM CONCENTRIC SEARCH ENVELOPE\nDual-Zone Solar Feeder & Acreage Architecture", 
                 color='#F8FAFC', fontsize=13.5, fontweight='bold', pad=15)

c5 = patches.Circle((0, 0), 5.0, facecolor='#F59E0B', alpha=0.15, edgecolor=AMBER, linewidth=3, linestyle='--', label='Outer 3-5 km Limit (5,000 m)')
c3 = patches.Circle((0, 0), 3.0, facecolor='#06B6D4', alpha=0.25, edgecolor=CYAN, linewidth=3.5, label='Inner 0-3 km Limit (3,000 m)')
c0 = patches.Circle((0, 0), 0.35, facecolor=GOLD, edgecolor='#FFFFFF', linewidth=2, zorder=10)

ax_buf.add_patch(c5)
ax_buf.add_patch(c3)
ax_buf.add_patch(c0)

ax_buf.annotate("", xy=(3.0, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="<->", color=CYAN, lw=2.5))
ax_buf.text(1.5, 0.25, "R = 3 km\n(2,827 ha / 6,985 ac)", color=CYAN, fontsize=10.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle="round,pad=0.2", fc="#0F172A", ec=CYAN, lw=0.8))

ax_buf.annotate("", xy=(5.0, 0), xytext=(3.0, 0), arrowprops=dict(arrowstyle="<->", color=AMBER, lw=2.5))
ax_buf.text(4.0, 0.25, "ΔR = 2 km\n(5,027 ha / 12,420 ac)", color=AMBER, fontsize=10.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle="round,pad=0.2", fc="#0F172A", ec=AMBER, lw=0.8))

ax_buf.text(0, -0.7, "GRID SUBSTATION\n(Bus / Switchyard)", color=GOLD, fontsize=11, fontweight='bold', ha='center')

info_inner = (
    "INNER 0-3 KM ZONE (CYAN)\n"
    "• Prime PM-KUSUM Component-A Zone\n"
    "• Direct 11 kV & 33 kV Dedication\n"
    "• Evacuation Losses: < 1.5%\n"
    "• Minimal line length & RoW constraints\n"
    "• Target Capacity: 1 MW to 10 MW"
)
ax_buf.text(-4.8, 3.2, info_inner, color='#F1F5F9', fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.5", fc="#0F172A", ec=CYAN, lw=1.5))

info_outer = (
    "OUTER 3-5 KM ZONE (AMBER)\n"
    "• Secondary Expansion & MW Aggregation\n"
    "• Standard 33 kV Evacuation Feeder\n"
    "• Evacuation Losses: 2.0% - 3.2%\n"
    "• High Acreage for Mega-Scale Arrays\n"
    "• Target Capacity: 10 MW to 50 MW"
)
ax_buf.text(-4.8, -3.2, info_outer, color='#F1F5F9', fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.5", fc="#0F172A", ec=AMBER, lw=1.5))

ax_buf.set_xlim(-5.8, 5.8)
ax_buf.set_ylim(-5.8, 5.8)
ax_buf.set_aspect('equal')
ax_buf.axis('off')

# -----------------------------------------------------------------------------
# PANEL 3 (Top Right): 0-3 km Satellite Clearance Breakdown
# -----------------------------------------------------------------------------
ax_comp = fig.add_subplot(gs[0, 2], facecolor=CARD_BG)
ax_comp.set_title("0-3 KM SATELLITE CLEARANCE BREAKDOWN\nRural Prime Substations vs Urban Core (ESA WorldCover 10m)", 
                  color='#F8FAFC', fontsize=12.5, fontweight='bold', pad=12)

benchmarks = [
    ("Thimmajipet (Nagarkurnool)", 97.6, 0.5, 0.9, 0.1),
    ("Kondapaka (Siddipet)", 91.0, 0.8, 2.6, 0.4),
    ("Medaram (Peddapalli)", 88.4, 2.1, 4.2, 5.3),
    ("Julurupadu (Kothagudem)", 76.5, 3.4, 3.1, 17.0),
    ("Narayanguda (Hyderabad)", 3.3, 4.1, 83.5, 2.1)
]

labels = [b[0] for b in benchmarks]
usable_vals = [b[1] for b in benchmarks]
water_vals = [b[2] for b in benchmarks]
built_vals = [b[3] for b in benchmarks]
slope_vals = [b[4] for b in benchmarks]

y_pos = np.arange(len(labels))
bar_height = 0.55

p1 = ax_comp.barh(y_pos, usable_vals, bar_height, color=GREEN, label='Usable Flat Land (<=5°)')
p2 = ax_comp.barh(y_pos, water_vals, bar_height, left=usable_vals, color=BLUE, label='Lakes & Water')
p3 = ax_comp.barh(y_pos, built_vals, bar_height, left=np.array(usable_vals)+np.array(water_vals), color=RED, label='Built-up / Urban')
p4 = ax_comp.barh(y_pos, slope_vals, bar_height, left=np.array(usable_vals)+np.array(water_vals)+np.array(built_vals), color='#EAB308', label='Steep Slope (>5°)')

ax_comp.set_yticks(y_pos)
ax_comp.set_yticklabels(labels, color='#F8FAFC', fontsize=9.5, fontweight='bold')
ax_comp.set_xlabel("0-3 km Zone Area Share (%)", color='#94A3B8', fontsize=10)
ax_comp.set_xlim(0, 100)
ax_comp.tick_params(colors='#94A3B8')
for spine in ax_comp.spines.values():
    spine.set_color(BORDER_COL)

ax_comp.legend(loc='lower center', bbox_to_anchor=(0.5, -0.32), ncol=2, facecolor='#0F172A', edgecolor=BORDER_COL, fontsize=8.5, labelcolor='#F1F5F9')

# -----------------------------------------------------------------------------
# PANEL 4 (Bottom Right): Statewide Clearance Distribution
# -----------------------------------------------------------------------------
ax_pie = fig.add_subplot(gs[1, 2], facecolor=CARD_BG)
ax_pie.set_title("STATEWIDE 5 KM LAND CLEARANCE CLASSIFICATION\nTotal 391 TGTRANSCO / TGRAC Grid Substations", 
                 color='#F8FAFC', fontsize=12.5, fontweight='bold', pad=12)

counts = [251, 58, 44, 22, 16]
cat_labels = [
    'Fully Clear 0-5 km (251 / 64.2%)',
    'Moderate Scouting (58 / 14.8%)',
    'Restricted Urban (44 / 11.3%)',
    'Outer 3-5 km Clear (22 / 5.6%)',
    'Inner 0-3 km Clear (16 / 4.1%)'
]
pie_colors = [GREEN, AMBER, RED, '#A855F7', CYAN]

wedges, texts, autotexts = ax_pie.pie(counts, colors=pie_colors, autopct='%1.1f%%', startangle=140,
                                      pctdistance=0.75, textprops=dict(color='#FFFFFF', fontweight='bold', fontsize=9.5),
                                      wedgeprops=dict(width=0.45, edgecolor=BORDER_COL, linewidth=1.5))

ax_pie.legend(wedges, cat_labels, loc='center left', bbox_to_anchor=(1.02, 0.5), facecolor='#0F172A', edgecolor=BORDER_COL, fontsize=9, labelcolor='#F1F5F9')

fig.suptitle("SuryaGrid: Telangana Statewide Substation 0-3 km & 3-5 km Land Suitability Architecture\nStrictly Masked to Telangana State & 5 km Substation Envelopes (No External / Maritime Features)",
             color='#38BDF8', fontsize=15.5, fontweight='bold', y=0.98)

plt.savefig(output_png, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close()
print("Saved presentation graphic successfully to:", output_png)
