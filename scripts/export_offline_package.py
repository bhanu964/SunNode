import os
import json
import zipfile
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
from xml.sax.saxutils import escape

print("Starting SuryaGrid Offline Package Exporter...")

# 1. Load Data
districts_path = 'data/boundaries/telangana_33_districts.geojson'
boundary_path = 'data/boundaries/telangana_boundary.geojson'
tgrac_path = 'data/processed/tgrac_substations_official.geojson'
master_path = 'outputs/telangana_electrical_infrastructure.geojson'
verified_pdf_path = 'data/results/substations_verified.geojson'

gdf_districts = gpd.read_file(districts_path)
gdf_boundary = gpd.read_file(boundary_path)
gdf_tgrac = gpd.read_file(tgrac_path)
gdf_master = gpd.read_file(master_path)
gdf_verified = gpd.read_file(verified_pdf_path)

# Merge 1 km calibrated suitability data & PVGIS generation
calib_csv = 'data/processed/substation_land_suitability_1km_calibrated.csv'
if os.path.exists(calib_csv):
    df_calib = pd.read_csv(calib_csv)
    merge_cols = [
        'substation_id', 'largest_green_patch_acres', 'estimated_mw',
        'land_suitability_score', 'viability_tier', 'meets_4_acre_min',
        'meets_10_acre_target', 'red_pct'
    ]
    pvgis_cols = [
        'pvgis_ey_kwh_per_mwp', 'pvgis_ed_kwh_per_mwp', 'pvgis_optimal_tilt_deg',
        'pvgis_dc_cuf_pct', 'direct_annual_generation_mu',
        'direct_annual_generation_mwh', 'direct_evacuation_current_33kv_amps',
        'installed_mva', 'grid_spare_mw', 'grid_capacity_basis', 'land_solar_mw',
        'deployable_solar_mw', 'active_bottleneck', 'unutilized_land_solar_mw',
        'required_33kv_feeder_bays', 'deployable_annual_mu', 'deployable_annual_mwh',
        'turnkey_capex_cr', 'annual_gross_revenue_cr', 'simple_payback_years',
        'suryagrid_master_score', 'master_rank',
        'is_colocated_overlap', 'overlap_factor', 'evacuation_voltage_kv',
        'feeder_bay_type', 'deployable_current_amps', 'required_feeder_bays',
        'tariff_tier', 'tariff_inr_per_kwh', 'revenue_kusum_313_cr', 'revenue_utility_275_cr'
    ]
    for c in pvgis_cols:
        if c in df_calib.columns:
            merge_cols.append(c)
    gdf_tgrac = gdf_tgrac.merge(df_calib[merge_cols], left_on='Record ID', right_on='substation_id', how='left')

print(f"Loaded {len(gdf_districts)} districts, {len(gdf_tgrac)} TGRAC, {len(gdf_master)} master facilities.")

# =========================================================================
# PART 1: GENERATE KMZ FOR GOOGLE EARTH
# =========================================================================
kml_styles = """
  <Style id="tgracStyle">
    <IconStyle>
      <color>ff00d7ff</color>
      <scale>1.2</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/star.png</href></Icon>
    </IconStyle>
    <LabelStyle><scale>0.8</scale></LabelStyle>
  </Style>
  <Style id="ehvStyle">
    <IconStyle>
      <color>ff0000ff</color>
      <scale>1.1</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
    </IconStyle>
  </Style>
  <Style id="hv220Style">
    <IconStyle>
      <color>ff0055ff</color>
      <scale>1.0</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
    </IconStyle>
  </Style>
  <Style id="hv132Style">
    <IconStyle>
      <color>ff00aaff</color>
      <scale>0.9</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
    </IconStyle>
  </Style>
  <Style id="dist33Style">
    <IconStyle>
      <color>ff00aa00</color>
      <scale>0.8</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
    </IconStyle>
  </Style>
  <Style id="govtPdfStyle">
    <IconStyle>
      <color>ffa020f0</color>
      <scale>0.85</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_square.png</href></Icon>
    </IconStyle>
  </Style>
  <Style id="transformerStyle">
    <IconStyle>
      <color>ffffaa00</color>
      <scale>0.6</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/donut.png</href></Icon>
    </IconStyle>
  </Style>
  <Style id="boundaryStyle">
    <LineStyle>
      <color>ff1673f9</color>
      <width>3</width>
    </LineStyle>
    <PolyStyle><fill>0</fill></PolyStyle>
  </Style>
  <Style id="districtStyle">
    <LineStyle>
      <color>8094a3b8</color>
      <width>1</width>
    </LineStyle>
    <PolyStyle><fill>0</fill></PolyStyle>
  </Style>
"""

kml_parts = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<kml xmlns="http://www.opengis.net/kml/2.2">',
    '<Document>',
    '  <name>SuryaGrid - Telangana Electrical Substation Inventory</name>',
    '  <description><![CDATA[<h3>SuryaGrid: Telangana Statewide Electrical Substation Intelligence Platform</h3><p>Comprehensive GIS dataset including official TGTRANSCO grid substations and statewide distribution infrastructure.</p>]]></description>',
    kml_styles
]

# Folder 1: Boundary
kml_parts.append('  <Folder><name>1. Telangana Administrative Boundaries</name><open>0</open>')
for _, row in gdf_boundary.iterrows():
    geom = row.geometry
    polys = [geom] if geom.geom_type == 'Polygon' else (geom.geoms if geom.geom_type == 'MultiPolygon' else [])
    for p in polys:
        coords_str = " ".join([f"{x},{y},0" for x, y in p.exterior.coords])
        kml_parts.append(f"""    <Placemark>
      <name>Telangana State Boundary</name>
      <styleUrl>#boundaryStyle</styleUrl>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>{coords_str}</coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>""")

for _, row in gdf_districts.iterrows():
    d_name = escape(str(row.get('district_name') or row.get('NAME') or 'District'))
    geom = row.geometry
    polys = [geom] if geom.geom_type == 'Polygon' else (geom.geoms if geom.geom_type == 'MultiPolygon' else [])
    for p in polys:
        coords_str = " ".join([f"{x},{y},0" for x, y in p.exterior.coords])
        kml_parts.append(f"""    <Placemark>
      <name>{d_name} District</name>
      <styleUrl>#districtStyle</styleUrl>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>{coords_str}</coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>""")
kml_parts.append('  </Folder>')

# Folder 2: Official TGRAC
kml_parts.append('  <Folder><name>2. ⭐ TGRAC TGTRANSCO Official Substations (391)</name><open>1</open>')
for _, row in gdf_tgrac.iterrows():
    name = escape(str(row.get('Substation Name', 'Substation')))
    volt = escape(str(row.get('Voltage Level', 'Unknown')))
    cap = escape(str(row.get('Total Capacity (MVA)', 'N/A')))
    tx = escape(str(row.get('Transformer Configuration', 'N/A')))
    dist = escape(str(row.get('District', 'N/A')))
    mandal = escape(str(row.get('Mandal', 'N/A')))
    comm = escape(str(row.get('Commissioning Date', 'N/A')))
    ptype = escape(str(row.get('Substation Type', 'N/A')))
    headroom = escape(str(row.get('Available Solar Headroom (MW)', 'Pending Feeder Audit')))
    solar_gen = escape(str(row.get('Existing Solar Connected (MW)', '0.0')))
    solar_plants = escape(str(row.get('Connected Solar Power Plants', 'None')))
    feeders = escape(str(row.get('33kV Feeders Count', 'N/A')))
    v03 = escape(str(row.get('Zone 0-3km Verdict', 'N/A')))
    u03 = escape(str(row.get('0-3km Usable (%)', 'N/A')))
    v35 = escape(str(row.get('Zone 3-5km Verdict', 'N/A')))
    u35 = escape(str(row.get('3-5km Usable (%)', 'N/A')))
    overall_land = escape(str(row.get('Overall Clearance (0-5 km)', 'N/A')))
    lon, lat = row.geometry.x, row.geometry.y
    
    desc = f"""<![CDATA[
    <table border="1" cellpadding="4" cellspacing="0" style="font-family:Arial, sans-serif; font-size:12px; border-collapse:collapse; width:360px;">
      <tr bgcolor="#0f172a"><th colspan="2" style="color:#f59e0b; text-align:left;">⭐ {name} ({volt})</th></tr>
      <tr bgcolor="#1e293b"><th colspan="2" style="color:#38bdf8; font-size:11px; text-align:left;">SuryaGrid Rank #{row.get('master_rank', 'N/A')} | Master Score: {row.get('suryagrid_master_score', 'N/A')} / 100</th></tr>
      <tr bgcolor="#dcfce7"><td colspan="2" style="font-weight:bold; color:#166534;">1. LAND SUITABILITY (1 km Feeder Radius)</td></tr>
      <tr><td><b>Contiguous Green Farmland:</b></td><td style="color:#15803d; font-weight:bold;">{row.get('largest_green_patch_acres', 'N/A')} ac -> {row.get('land_solar_mw', 'N/A')} MW</td></tr>
      <tr><td><b>Land Suitability Score:</b></td><td>{row.get('land_suitability_score', 'N/A')} / 100 ({row.get('viability_tier', 'N/A')})</td></tr>
      <tr bgcolor="#fef3c7"><td colspan="2" style="font-weight:bold; color:#92400e;">2. GRID HOSTING & MASTER BOTTLENECK</td></tr>
      <tr><td><b>Installed PTR Capacity:</b></td><td>{row.get('installed_mva', cap)} MVA</td></tr>
      <tr><td><b>Grid Spare Capacity:</b></td><td>{row.get('grid_spare_mw', 'N/A')} MW ({row.get('grid_capacity_basis', 'Calculated')})</td></tr>
      <tr bgcolor="#fef9c3"><td><b>True Deployable Capacity:</b></td><td style="color:#b45309; font-weight:bold; font-size:13px;">{row.get('deployable_solar_mw', 'N/A')} MW</td></tr>
      <tr><td><b>Active Bottleneck:</b></td><td style="color:#dc2626; font-weight:bold;">{row.get('active_bottleneck', 'N/A')}</td></tr>
      <tr><td><b>Grid Evacuation / Bay:</b></td><td>{row.get('deployable_current_amps', row.get('deployable_current_33kv_amps', 'N/A'))} A @ {row.get('evacuation_voltage_kv', 33)} kV ({row.get('required_feeder_bays', row.get('required_33kv_feeder_bays', 'N/A'))} x {row.get('feeder_bay_type', '33 kV VCB Feeder Bay')})</td></tr>
      <tr><td><b>Co-Location Status:</b></td><td style="color:{'#f59e0b' if row.get('is_colocated_overlap') else '#10b981'}; font-weight:bold;">{'Shared Yard (< 2 km Overlap, Dedup Applied)' if row.get('is_colocated_overlap') else 'Dedicated Single Yard'}</td></tr>
      <tr bgcolor="#f3e8ff"><td colspan="2" style="font-weight:bold; color:#6b21a8;">3. PVGIS v5.3 SOLAR GENERATION</td></tr>
      <tr><td><b>Specific Annual Yield:</b></td><td>{float(row.get('pvgis_ey_kwh_per_mwp') or 0):,.0f} kWh/MWp/yr</td></tr>
      <tr><td><b>Optimal Tilt / CUF:</b></td><td>{row.get('pvgis_optimal_tilt_deg', 'N/A')}° South | CUF: {row.get('pvgis_dc_cuf_pct', 'N/A')}%</td></tr>
      <tr bgcolor="#ecfdf5"><td><b>Annual Solar Energy:</b></td><td style="color:#065f46; font-weight:bold;">{float(row.get('deployable_annual_mu') or 0):,.3f} MU/yr ({float(row.get('deployable_annual_mwh') or 0):,.1f} MWh/yr)</td></tr>
      <tr bgcolor="#e0f2fe"><td colspan="2" style="font-weight:bold; color:#0369a1;">4. 25-YEAR FINANCIAL ROI ({row.get('tariff_tier', 'PM-KUSUM')} @ ₹{row.get('tariff_inr_per_kwh', 3.13)}/kWh)</td></tr>
      <tr><td><b>Turnkey CAPEX (@ ₹3.75 Cr/MW):</b></td><td>₹{float(row.get('turnkey_capex_cr') or 0):,.2f} Cr</td></tr>
      <tr><td><b>Gross Revenue / Year:</b></td><td style="color:#047857; font-weight:bold;">₹{float(row.get('annual_gross_revenue_cr') or 0):,.2f} Cr/yr</td></tr>
      <tr><td><b>Simple Payback Period:</b></td><td style="color:#0369a1; font-weight:bold;">{row.get('simple_payback_years', 'N/A')} Years</td></tr>
      <tr bgcolor="#f1f5f9"><td><b>Administrative Location:</b></td><td>{dist} District, {mandal} Mandal</td></tr>
      <tr><td><b>Coordinates:</b></td><td>{lat:.5f}, {lon:.5f}</td></tr>
      <tr bgcolor="#f1f5f9"><td colspan="2" style="font-size:10px; color:#64748b;">Source: TGRAC / TGTRANSCO, DISCOM Annexure-D, EU JRC PVGIS v5.3 & GEE Dynamic World</td></tr>
    </table>
    ]]>"""
    kml_parts.append(f"""    <Placemark>
      <name>{name} ({volt})</name>
      <description>{desc}</description>
      <styleUrl>#tgracStyle</styleUrl>
      <Point><coordinates>{lon},{lat},0</coordinates></Point>
    </Placemark>""")
kml_parts.append('  </Folder>')

# Helper for master inventory folders
def add_master_folder(folder_name, style_id, filter_fn, open_state=0):
    kml_parts.append(f'  <Folder><name>{folder_name}</name><open>{open_state}</open>')
    count = 0
    for _, row in gdf_master.iterrows():
        if filter_fn(row):
            count += 1
            name = escape(str(row.get('Facility Name', 'Electrical Facility')))
            volt = escape(str(row.get('Voltage Level', 'Unknown')))
            cat = escape(str(row.get('Infrastructure Category', 'Substation')))
            dist = escape(str(row.get('District', 'Unknown')))
            mandal = escape(str(row.get('Mandal', 'Unknown')))
            op = escape(str(row.get('DISCOM / Operator', 'Unknown')))
            pdf_st = escape(str(row.get('PDF Match Status', 'N/A')))
            headroom = escape(str(row.get('Available Solar Headroom (MW)', 'Pending Feeder Audit')))
            solar_gen = escape(str(row.get('Existing Solar Connected (MW)', '0.0')))
            solar_plants = escape(str(row.get('Connected Solar Plants', 'None')))
            lon, lat = row.geometry.x, row.geometry.y
            
            desc = f"""<![CDATA[
            <table border="1" cellpadding="4" cellspacing="0" style="font-family:Arial, sans-serif; font-size:12px; border-collapse:collapse; width:300px;">
              <tr bgcolor="#0f172a"><th colspan="2" style="color:#38bdf8; text-align:left;">{name}</th></tr>
              <tr><td><b>Category:</b></td><td>{cat}</td></tr>
              <tr><td><b>Voltage:</b></td><td>{volt}</td></tr>
              <tr bgcolor="#fef3c7"><td><b>Solar Headroom:</b></td><td style="color:#b45309; font-weight:bold;">{headroom} {'MW' if 'Pending' not in headroom else ''}</td></tr>
              <tr><td><b>Existing Solar:</b></td><td style="color:#047857; font-weight:bold;">{solar_gen} MW</td></tr>
              <tr><td><b>Operator:</b></td><td>{op}</td></tr>
              <tr><td><b>District:</b></td><td>{dist}</td></tr>
              <tr><td><b>Mandal:</b></td><td>{mandal}</td></tr>
              <tr><td><b>PDF Status:</b></td><td>{pdf_st}</td></tr>
              <tr><td><b>Coordinates:</b></td><td>{lat:.5f}, {lon:.5f}</td></tr>
            </table>
            ]]>"""
            kml_parts.append(f"""    <Placemark>
      <name>{name}</name>
      <description>{desc}</description>
      <styleUrl>#{style_id}</styleUrl>
      <Point><coordinates>{lon},{lat},0</coordinates></Point>
    </Placemark>""")
    kml_parts.append('  </Folder>')
    print(f"Added folder {folder_name}: {count} placemarks")

# Folder 3: 400kV & 765kV
add_master_folder("3. 765 kV & 400 kV Extra High Voltage (Red)", "ehvStyle", 
                  lambda r: '765' in str(r.get('Voltage Level')) or '400' in str(r.get('Voltage Level')), 1)

# Folder 4: 220kV
add_master_folder("4. 220 kV High Voltage Transmission (Orange)", "hv220Style", 
                  lambda r: '220' in str(r.get('Voltage Level')), 0)

# Folder 5: 132kV
add_master_folder("5. 132 kV Grid Substations (Amber)", "hv132Style", 
                  lambda r: '132' in str(r.get('Voltage Level')), 0)

# Folder 6: 33/11kV
add_master_folder("6. 33/11 kV Primary Distribution Substations (Green)", "dist33Style", 
                  lambda r: '33/11' in str(r.get('Voltage Level')) or r.get('Infrastructure Category') == '33_11KV_SUBSTATION', 0)

# Folder 7: Govt PDF Matched
add_master_folder("7. Government PDF Matched Locations (Purple)", "govtPdfStyle", 
                  lambda r: r.get('PDF Match Status') in ['EXACT_MATCH', 'HIGH_CONFIDENCE_LIKELY_MATCH'], 0)

# Folder 8: Transformers
add_master_folder("8. Distribution Transformers (Blue)", "transformerStyle", 
                  lambda r: r.get('Infrastructure Category') == 'DISTRIBUTION_TRANSFORMER', 0)

kml_parts.append('</Document>')
kml_parts.append('</kml>')

kml_content = "\n".join(kml_parts)

# Write to KMZ
kmz_path = 'outputs/SuryaGrid_Telangana_Substations_Offline.kmz'
with zipfile.ZipFile(kmz_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr('doc.kml', kml_content)
print(f"✅ KMZ created: {kmz_path} ({os.path.getsize(kmz_path)/1024:.1f} KB)")


# =========================================================================
# PART 2: GENERATE STATEWIDE HIGH-RESOLUTION MAP ATLAS (PDF)
# =========================================================================
pdf_path = 'outputs/SuryaGrid_Telangana_Substations_Map_Atlas.pdf'
with PdfPages(pdf_path) as pdf:
    # ---------------- PAGE 1: Master Overview ----------------
    fig, ax = plt.subplots(figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    # Plot boundaries
    gdf_districts.plot(ax=ax, color='#1e293b', edgecolor='#475569', linewidth=0.8, alpha=0.9)
    gdf_boundary.plot(ax=ax, color='none', edgecolor='#f97316', linewidth=2.0)
    
    # Add District labels
    for _, row in gdf_districts.iterrows():
        name = row.get('district_name') or row.get('NAME') or ''
        centroid = row.geometry.centroid
        ax.text(centroid.x, centroid.y, name, color='#94a3b8', fontsize=6.5, 
                ha='center', va='center', weight='bold', alpha=0.6)
        
    # Plot points by category
    mask_33 = gdf_master['Voltage Level'].astype(str).str.contains('33/11', na=False) | (gdf_master['Infrastructure Category'] == '33_11KV_SUBSTATION')
    ax.scatter(gdf_master[mask_33].geometry.x, gdf_master[mask_33].geometry.y, 
               color='#22c55e', s=20, alpha=0.75, label='33/11 kV Distribution Substations', zorder=3)
    
    mask_132 = gdf_master['Voltage Level'].astype(str).str.contains('132', na=False)
    ax.scatter(gdf_master[mask_132].geometry.x, gdf_master[mask_132].geometry.y, 
               color='#f59e0b', s=35, alpha=0.85, label='132 kV Grid Substations', zorder=4)
    
    mask_220 = gdf_master['Voltage Level'].astype(str).str.contains('220', na=False)
    ax.scatter(gdf_master[mask_220].geometry.x, gdf_master[mask_220].geometry.y, 
               color='#f97316', s=55, alpha=0.9, label='220 kV High Voltage Substations', zorder=5)
    
    mask_400 = gdf_master['Voltage Level'].astype(str).str.contains('400|765', na=False)
    ax.scatter(gdf_master[mask_400].geometry.x, gdf_master[mask_400].geometry.y, 
               color='#ef4444', s=90, alpha=0.95, edgecolors='#ffffff', linewidths=1.2, 
               label='400 kV & 765 kV Extra High Voltage (EHV)', zorder=6)
    
    # TGRAC Official (Gold Stars)
    ax.scatter(gdf_tgrac.geometry.x, gdf_tgrac.geometry.y, 
               color='#ffd700', marker='*', s=75, alpha=0.85, 
               label='⭐ TGRAC / TGTRANSCO Official Grid (391)', zorder=7)
    
    # Formatting
    ax.set_title("SuryaGrid: Telangana Statewide Electrical Substation Infrastructure Map", 
                 color='#38bdf8', fontsize=18, weight='bold', pad=20)
    ax.set_xlabel("Longitude (°E)", color='#94a3b8', fontsize=11)
    ax.set_ylabel("Latitude (°N)", color='#94a3b8', fontsize=11)
    ax.tick_params(colors='#94a3b8', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#334155')
        
    # Legend
    legend = ax.legend(loc='lower right', facecolor='#1e293b', edgecolor='#334155', 
                       fontsize=10, labelcolor='#f8fafc', framealpha=0.95)
    
    # Stats Box (Top Left)
    stats_text = (
        "SuryaGrid Platform Summary\n"
        "------------------------------------\n"
        "• State: Telangana (33 Districts)\n"
        "• Total Facilities Mapped: 1,124\n"
        "• TGRAC Official Grid: 391 Substations\n"
        "• Govt PDF Verified: 178 Matches\n"
        "• Statewide Master: 1,045 Facilities\n"
        "• Coordinates: WGS84 (EPSG:4326)\n"
        "• Source: TGTRANSCO, TGRAC, OSM"
    )
    ax.text(0.02, 0.96, stats_text, transform=ax.transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.8', facecolor='#1e293b', edgecolor='#38bdf8', alpha=0.9),
            fontsize=9.5, color='#e2e8f0', family='monospace')
    
    plt.tight_layout()
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Page 1 rendered: Statewide Master Grid Map")

    # ---------------- PAGE 2: Transmission Grid vs Distribution Grid ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 10), dpi=300)
    fig.patch.set_facecolor('#0f172a')
    
    # Map 1: Transmission Grid (>= 132 kV)
    ax1.set_facecolor('#0f172a')
    gdf_districts.plot(ax=ax1, color='#1e293b', edgecolor='#334155', linewidth=0.6)
    gdf_boundary.plot(ax=ax1, color='none', edgecolor='#f97316', linewidth=1.5)
    ax1.scatter(gdf_tgrac.geometry.x, gdf_tgrac.geometry.y, color='#ffd700', marker='*', s=50, label='TGRAC Grid (391)')
    ax1.scatter(gdf_master[mask_400].geometry.x, gdf_master[mask_400].geometry.y, color='#ef4444', s=60, label='400/765 kV')
    ax1.scatter(gdf_master[mask_220].geometry.x, gdf_master[mask_220].geometry.y, color='#f97316', s=40, label='220 kV')
    ax1.scatter(gdf_master[mask_132].geometry.x, gdf_master[mask_132].geometry.y, color='#f59e0b', s=25, label='132 kV')
    ax1.set_title("A. High Voltage Transmission Grid (>= 132 kV)", color='#f59e0b', fontsize=14, weight='bold')
    ax1.legend(loc='lower right', facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc', fontsize=9)
    ax1.tick_params(colors='#94a3b8', labelsize=8)
    for spine in ax1.spines.values():
        spine.set_color('#334155')

    # Map 2: Distribution Grid (33/11 kV & Transformers)
    ax2.set_facecolor('#0f172a')
    gdf_districts.plot(ax=ax2, color='#1e293b', edgecolor='#334155', linewidth=0.6)
    gdf_boundary.plot(ax=ax2, color='none', edgecolor='#f97316', linewidth=1.5)
    ax2.scatter(gdf_master[mask_33].geometry.x, gdf_master[mask_33].geometry.y, color='#22c55e', s=20, label='33/11 kV Substations')
    mask_tx = gdf_master['Infrastructure Category'] == 'DISTRIBUTION_TRANSFORMER'
    if mask_tx.any():
        ax2.scatter(gdf_master[mask_tx].geometry.x, gdf_master[mask_tx].geometry.y, color='#0284c7', s=15, alpha=0.5, label='Distribution Transformers')
    ax2.scatter(gdf_verified.geometry.x, gdf_verified.geometry.y, color='#a855f7', s=30, label='Govt PDF Matches (178)')
    ax2.set_title("B. Primary Distribution Grid (33/11 kV & Step-Down)", color='#22c55e', fontsize=14, weight='bold')
    ax2.legend(loc='lower right', facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc', fontsize=9)
    ax2.tick_params(colors='#94a3b8', labelsize=8)
    for spine in ax2.spines.values():
        spine.set_color('#334155')

    plt.tight_layout()
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Page 2 rendered: Transmission vs Distribution Grid")

    # ---------------- PAGE 3: District Breakdown Chart ----------------
    fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    # Calculate district counts from master
    dist_counts = gdf_master['District'].value_counts().head(20)
    y_pos = range(len(dist_counts))
    
    bars = ax.barh(y_pos, dist_counts.values, color='#38bdf8', edgecolor='#0284c7', alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(dist_counts.index, color='#e2e8f0', fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Discovered Electrical Facilities", color='#94a3b8', fontsize=11)
    ax.set_title("Top 20 Telangana Districts by Discovered Electrical Facilities", color='#38bdf8', fontsize=16, weight='bold', pad=15)
    ax.tick_params(colors='#94a3b8')
    for spine in ax.spines.values():
        spine.set_color('#334155')
        
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 1, bar.get_y() + bar.get_height()/2, f"{int(w)}", 
                va='center', color='#f8fafc', fontsize=9, weight='bold')
        
    plt.tight_layout()
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Page 3 rendered: District Distribution Chart")

print(f"✅ Map Atlas PDF created: {pdf_path} ({os.path.getsize(pdf_path)/1024:.1f} KB)")
