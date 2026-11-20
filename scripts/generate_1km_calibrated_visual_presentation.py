#!/usr/bin/env python3
"""
scripts/generate_1km_calibrated_visual_presentation.py
Generates high-contrast visual presentation artifact for the Refined 1 km
Acreage-Calibrated Land Assessment across Telangana's 391 electrical substations.
Reflects the updated Green mask (open farmland/crops on slope <= 5° classified as Green Ready)
and Yellow strictly restricted to trees and moderate slope (5°–10°).
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D

output_png = "/Users/bhanuprasad/.gemini/antigravity/brain/fd0a8b34-ef7b-47ae-9d33-8e2736284ecd/SuryaGrid_1km_Calibrated_Suitability_Presentation.png"
os.makedirs(os.path.dirname(output_png), exist_ok=True)

csv_path = "data/processed/substation_land_suitability_1km_calibrated.csv"
df = pd.read_csv(csv_path)

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

fig = plt.figure(figsize=(26, 13.5), dpi=200, facecolor='#090D16')
gs = fig.add_gridspec(2, 3, width_ratios=[1.15, 1.0, 1.15], height_ratios=[1.0, 1.0], wspace=0.22, hspace=0.28)

DARK_BG = '#090D16'
CARD_BG = '#111827'
BORDER_COL = '#1F2937'
TEXT_MUTED = '#9CA3AF'
TEXT_BRIGHT = '#F9FAFB'

GREEN_HIGH = '#10B981'    # Score 90-100 (>=10ac Farmland/Open Ready)
GREEN_VIABLE = '#34D399'  # Score 70-89 (4-10ac Farmland/Open Ready)
YELLOW_COND = '#FACC15'   # Score 40-69 (Trees/5-10° Slope Clearance)
RED_CONSTR = '#EF4444'    # Score 0-39 (Urban/Water/Steep >10°)

BUF_FILL = '#93C5FD'      # 1 km buffer fill
BUF_EDGE = '#60A5FA'      # 1 km buffer border
SS_CORE = '#0F172A'       # Substation core
ORANGE = '#F97316'        # State boundary

# -----------------------------------------------------------------------------
# PANEL 1 (Left): Statewide Telangana Map (391 Substations Color-Coded by Score)
# -----------------------------------------------------------------------------
ax_map = fig.add_subplot(gs[:, 0], facecolor=CARD_BG)
ax_map.set_title("TELANGANA GRID: REFINED 1 KM ACREAGE-CALIBRATED SUITABILITY\nFarmland & Open Ground Ready for Solar (391 Substations)", 
                 color=TEXT_BRIGHT, fontsize=13, fontweight='bold', pad=14)

if boundary_coords:
    for ring in boundary_coords:
        xs, ys = zip(*ring)
        ax_map.plot(xs, ys, color=ORANGE, linewidth=2.4, label='Telangana State Border', zorder=2)
        ax_map.fill(xs, ys, color='#1E293B', alpha=0.45, zorder=1)

# Group substations by viability score tier
high_ss = df[df['land_suitability_score'] >= 90.0]
viable_ss = df[(df['land_suitability_score'] >= 70.0) & (df['land_suitability_score'] < 90.0)]
cond_ss = df[(df['land_suitability_score'] >= 40.0) & (df['land_suitability_score'] < 70.0)]
low_ss = df[df['land_suitability_score'] < 40.0]

# Plot with halos
ax_map.scatter(cond_ss['lon'], cond_ss['lat'], c=YELLOW_COND, s=28, alpha=0.85, label=f'Conditional (Needs Clearance) [{len(cond_ss)} SS]', zorder=3)
ax_map.scatter(viable_ss['lon'], viable_ss['lat'], c=GREEN_VIABLE, s=36, alpha=0.9, label=f'Viable 4-10ac Farmland/Open [{len(viable_ss)} SS]', zorder=4)
ax_map.scatter(high_ss['lon'], high_ss['lat'], c=GREEN_HIGH, s=44, edgecolors='#FFFFFF', linewidths=0.6, alpha=0.95, label=f'High >=10ac Farmland Ready [{len(high_ss)} SS]', zorder=5)
ax_map.scatter(low_ss['lon'], low_ss['lat'], c=RED_CONSTR, s=32, edgecolors='#FFFFFF', linewidths=0.6, alpha=0.95, label=f'Low / Constrained Urban [{len(low_ss)} SS]', zorder=6)

# Highlight benchmark sample substations
benchmarks = ['Narayanguda', 'Gajwel (400KV)', 'K.M.Pally (220KV)', 'Ganeshpahad', 'Kondapaka']
for b_name in benchmarks:
    match = df[df['substation_name'] == b_name]
    if not match.empty:
        row = match.iloc[0]
        ax_map.scatter(row['lon'], row['lat'], s=120, facecolors='none', edgecolors='#38BDF8', linewidths=2.0, zorder=7)
        offset_y = 0.12 if 'Gajwel' not in b_name else -0.16
        ax_map.annotate(f"{b_name}\nScore: {row['land_suitability_score']}", 
                        (row['lon'], row['lat']),
                        xytext=(row['lon'] + 0.12, row['lat'] + offset_y),
                        fontsize=8.5, color='#F8FAFC', fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.25", fc="#0B0F19", ec="#38BDF8", lw=1.2, alpha=0.9),
                        arrowprops=dict(arrowstyle="->", color="#38BDF8", lw=1.0),
                        zorder=8)

ax_map.set_xlabel("Longitude (°E)", color=TEXT_MUTED, fontsize=10, labelpad=8)
ax_map.set_ylabel("Latitude (°N)", color=TEXT_MUTED, fontsize=10, labelpad=8)
ax_map.tick_params(colors=TEXT_MUTED, labelsize=9)
ax_map.grid(True, color=BORDER_COL, linestyle='--', alpha=0.5)
ax_map.legend(loc='lower left', facecolor='#0B0F19', edgecolor=BORDER_COL, fontsize=9.5, labelcolor=TEXT_BRIGHT, framealpha=0.95)

# -----------------------------------------------------------------------------
# PANEL 2 (Top Middle): 1 km Substation Micro-Siting Radial Simulation
# -----------------------------------------------------------------------------
ax_sim = fig.add_subplot(gs[0, 1], facecolor=CARD_BG)
ax_sim.set_title("1,000 METER (1 KM) FEEDER EVACUATION ZONE\nFarmland / Crops Shaded Green (Primary Usable)", 
                 color=TEXT_BRIGHT, fontsize=12.5, fontweight='bold', pad=12)

# Draw concentric 1km circle
circle_1k = plt.Circle((0, 0), 1000, color=BUF_FILL, alpha=0.15, zorder=1)
circle_1k_edge = plt.Circle((0, 0), 1000, fill=False, edgecolor=BUF_EDGE, linewidth=2.0, linestyle='-', zorder=2)
ax_sim.add_patch(circle_1k)
ax_sim.add_patch(circle_1k_edge)

# Draw simulated land-cover zones:
# 1. Broad Green Farmland / Open Fields covering the surrounding area
farm_patch = patches.Polygon([(-950, -950), (950, -950), (950, 950), (-950, 950)], color=GREEN_HIGH, alpha=0.55, zorder=3)
ax_sim.add_patch(farm_patch)

# 2. Red Zone: Substation compound in center + small settlement cluster & lake with 30m buffer
sub_compound = patches.Rectangle((-180, -180), 360, 360, color=RED_CONSTR, alpha=0.75, zorder=4)
ax_sim.add_patch(sub_compound)
settlement = patches.Rectangle((-850, 450), 320, 280, color=RED_CONSTR, alpha=0.65, zorder=4)
ax_sim.add_patch(settlement)
lake_patch = patches.Circle((600, -550), 220, color='#3B82F6', alpha=0.7, zorder=4)
lake_ftl = patches.Circle((600, -550), 280, fill=False, edgecolor=RED_CONSTR, linewidth=2, linestyle='--', zorder=5)
ax_sim.add_patch(lake_patch)
ax_sim.add_patch(lake_ftl)

# 3. Yellow Zone: Isolated tree orchard and moderate slope hill ridge (strictly minor clearance)
orchard_patch = patches.Polygon([(-750, -750), (-400, -800), (-450, -450), (-700, -400)], color=YELLOW_COND, alpha=0.7, zorder=4)
ax_sim.add_patch(orchard_patch)
ridge_patch = patches.Polygon([(400, 350), (750, 450), (800, 750), (450, 650)], color=YELLOW_COND, alpha=0.7, zorder=4)
ax_sim.add_patch(ridge_patch)

# Substation Marker at Center: Dark Charcoal Core with Crisp White Halo
halo_circle = plt.Circle((0, 0), 65, color='#FFFFFF', zorder=6)
core_circle = plt.Circle((0, 0), 45, color=SS_CORE, zorder=7)
ax_sim.add_patch(halo_circle)
ax_sim.add_patch(core_circle)

ax_sim.annotate("Substation Point\n(White Halo + Charcoal Core)", (0, 0), xytext=(90, -110),
                fontsize=8.5, color='#F8FAFC', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="#0B0F19", ec="#FFFFFF", lw=1.0, alpha=0.9),
                arrowprops=dict(arrowstyle="->", color="#FFFFFF", lw=1.2), zorder=8)

ax_sim.annotate("GREEN READY: Flat Farmland / Open Fields\n(Crops, Bare, Scrub <= 5° Slope)", (250, -250),
                fontsize=8, color='#10B981', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="#064E3B", ec="#10B981", lw=1.0), zorder=8)

ax_sim.annotate("YELLOW: Trees / Orchards & 5°–10° Slope\n(Minor Clearance / Grading Only)", (-620, -520),
                fontsize=8, color='#FACC15', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="#451A03", ec="#FACC15", lw=1.0), zorder=8)

ax_sim.annotate("RED: Substation Compound & Built\n(Strictly Excluded)", (-120, 220),
                fontsize=8, color='#EF4444', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="#450A0A", ec="#EF4444", lw=1.0), zorder=8)

ax_sim.set_xlim(-1150, 1150)
ax_sim.set_ylim(-1150, 1150)
ax_sim.set_aspect('equal')
ax_sim.axis('off')

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# PANEL 3 (Bottom Middle): Stage 4.5 Master Techno-Economic Architecture
# -----------------------------------------------------------------------------
ax_fix = fig.add_subplot(gs[1, 1], facecolor=CARD_BG)
ax_fix.set_title("STAGE 4.5: VOLTAGE-TIER & DATA INTEGRITY ARCHITECTURE", 
                 color='#38BDF8', fontsize=12.5, fontweight='bold', pad=12)

reclass_text = (
    "STAGE 4.5 DATA INTEGRITY & TECHNO-ECONOMIC ARCHITECTURE:\n\n"
    "1. LAYER 1 — LAND POTENTIAL & OVERLAP DEDUPLICATION:\n"
    "   • Raw Land: 29,984 MW | Deduplicated Land: 29,366 MW (-617 MW overlap).\n"
    "   • 53 Co-Located Substations (<2 km overlap) deduplicated via Voronoi/buffers.\n\n"
    "2. LAYER 2 — 1-TO-1 ANNEXURE-D & MASTER BOTTLENECK:\n"
    "   • Voltage-aware matching stops double-allocating shared Annexure-D MVA.\n"
    "   • True Deployable MW: 12,950 MW (Raw) -> 12,603 MW (Deduplicated).\n"
    "   • 247 SS Grid Constrained (63.2%) | 130 SS Land Constrained (33.2%).\n\n"
    "3. LAYER 3 — VOLTAGE-TIER EVACUATION & FEEDER BAYS:\n"
    "   • 33 kV VCB Bays: 275 SS (17.85 A/MW, max 320 A/bay, PM-KUSUM feeder).\n"
    "   • 132 kV SF6 Bays: 85 SS (4.46 A/MW, 50 MW/bay, 220 kV STU pool).\n"
    "   • 220 kV SF6 Bays: 31 SS (2.68 A/MW, 100 MW/bay, 400 kV STU pool).\n\n"
    "4. LAYER 4 — DUAL TARIFF ROI & RECONCILED CASH FLOWS:\n"
    "   • PM-KUSUM (132/33 kV): ₹3.13/kWh | Utility STU (220/400 kV): ₹2.75/kWh.\n"
    "   • Dedup CAPEX: ₹47,260 Cr | Dedup Annual Revenue: ₹5,484 Cr/yr.\n"
    "   • Statewide Payback: strictly 10.13 Years from aggregate cash flows.\n"
    "   • 25-Yr Net Profit: ₹58,858 Cr (0.91 availability & degradation multiplier)."
)

ax_fix.text(0.04, 0.94, reclass_text, color=TEXT_BRIGHT, fontsize=8.8,
            fontfamily='monospace', va='top', ha='left', transform=ax_fix.transAxes,
            bbox=dict(boxstyle="round,pad=0.6", fc="#0B0F19", ec="#38BDF8", lw=1.2, alpha=0.95))
ax_fix.axis('off')

# -----------------------------------------------------------------------------
# PANEL 4 (Top Right): 5 Sample Substations Validation Matrix with Stage 4.5 Metrics
# -----------------------------------------------------------------------------
ax_bench = fig.add_subplot(gs[0, 2], facecolor=CARD_BG)
ax_bench.set_title("5-SUBSTATION BENCHMARK: VOLTAGE-TIER EVACUATION & ROI\nmin(Land MW, Grid Spare MW) with Tiered Tariffs (₹3.13 / ₹2.75)", 
                   color=TEXT_BRIGHT, fontsize=12.0, fontweight='bold', pad=12)

# Substation, Land MW, Grid MW, Deploy MW, Evac Bay, Bottleneck, Payback, Score
sample_data = [
    ("Gajwel (400KV)", "121.2", "38.0", "38.0 MW", "220kV SF6", "GRID CONSTRAINED", "10.9 y", "58.5"),
    ("K.M.Pally (220KV)", "119.6", "158.0", "119.6 MW", "132kV SF6", "LAND CONSTRAINED", "11.0 y", "75.0"),
    ("Ganeshpahad", "132.6", "15.0", "15.0 MW", "33kV VCB", "GRID CONSTRAINED", "9.6 y", "48.8"),
    ("Kondapaka", "85.9", "28.4", "28.4 MW", "33kV VCB", "GRID CONSTRAINED", "9.3 y", "56.9"),
    ("Narayanguda", "0.0", "45.0", "0.0 MW", "None (0A)", "URBAN EXCLUDED", "0.0 y", "0.0"),
]

ax_bench.axis('off')

# Render styled table
col_headers = ["Substation", "Land MW", "Grid MW", "Deploy MW", "Evac Bay", "Bottleneck", "Payback", "Score"]
cell_text = []
for name, lmw, gmw, dmw, ebay, bneck, pb, sc in sample_data:
    cell_text.append([name, lmw, gmw, dmw, ebay, bneck, pb, sc])

table = ax_bench.table(cellText=cell_text, colLabels=col_headers, loc='center', cellLoc='center',
                       colWidths=[0.21, 0.10, 0.10, 0.13, 0.13, 0.19, 0.09, 0.08])
table.auto_set_font_size(False)
table.set_fontsize(8.2)
table.scale(1.0, 2.0)

for (r, c), cell in table.get_celld().items():
    if r == 0:
        cell.set_facecolor('#0B0F19')
        cell.set_text_props(color='#38BDF8', fontweight='bold')
    else:
        cell.set_edgecolor(BORDER_COL)
        if c == 3: # Deployable MW
            cell.set_text_props(color='#38BDF8', fontweight='bold')
        elif c == 4: # Evac Bay
            cell.set_text_props(color='#A855F7', fontweight='bold')
        elif c == 5: # Bottleneck
            cell.set_text_props(color='#FACC15' if 'GRID' in cell_text[r-1][c] else ('#34D399' if 'LAND' in cell_text[r-1][c] else '#EF4444'), fontweight='bold', fontsize=7.5)
        elif c == 7: # Score
            cell.set_text_props(color='#38BDF8' if float(cell_text[r-1][c]) > 0 else '#EF4444', fontweight='bold')
        else:
            cell.set_text_props(color=TEXT_BRIGHT)

# -----------------------------------------------------------------------------
# PANEL 5 (Bottom Right): Master Bottleneck Distribution & Financial Impact
# -----------------------------------------------------------------------------
ax_pie = fig.add_subplot(gs[1, 2], facecolor=CARD_BG)
tot_land_mw = 29366.4
tot_deploy_mw = 12602.6
tot_rev_cr = 5484.10
ax_pie.set_title(f"STAGE 4.5 DEDUPLICATED BOTTLENECKS & IMPACT\nDeployable: {tot_deploy_mw:,.0f} MW (Dedup) | Revenue: ₹{tot_rev_cr:,.0f} Cr/yr", 
                 color=TEXT_BRIGHT, fontsize=12.0, fontweight='bold', pad=12)

# Bottleneck distribution
grid_con = 247
land_con = 130
urban_ex = 14

b_sizes = [grid_con, land_con, urban_ex]
b_labels = [
    f"Grid Constrained\n({grid_con} SS | {grid_con/391*100:.1f}%)\n[16,764 MW Land-Locked]",
    f"1 km Land Constrained\n({land_con} SS | {land_con/391*100:.1f}%)\n[Full Land Utilized]",
    f"Urban / Excluded\n({urban_ex} SS | {urban_ex/391*100:.1f}%)\n[0 MW Ground Solar]"
]
b_colors = ['#F59E0B', '#10B981', '#EF4444']
b_explode = (0.04, 0.04, 0.08)

wedges, texts, autotexts = ax_pie.pie(b_sizes, labels=b_labels, autopct='%1.1f%%', startangle=140,
                                      colors=b_colors, explode=b_explode,
                                      textprops=dict(color=TEXT_BRIGHT, fontsize=8.5, fontweight='bold'),
                                      wedgeprops=dict(edgecolor='#090D16', linewidth=1.5))
for autotext in autotexts:
    autotext.set_color('#090D16')
    autotext.set_fontsize(9)

fig.suptitle("SuryaGrid: Telangana Statewide Substation 1 km Land Suitability Assessment\nPM-KUSUM Component-A & Challenge 10 Feeder Solar Potential (Dynamic World 10m + USGS SRTM 30m)", 
             fontsize=17, fontweight='bold', color='#38BDF8', y=0.985)

plt.savefig(output_png, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close()
print(f"Presentation saved successfully to: {output_png}")
