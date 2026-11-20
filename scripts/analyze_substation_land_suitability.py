#!/usr/bin/env python3
"""
scripts/analyze_substation_land_suitability.py
Performs satellite-based terrain, slope, and land cover suitability analysis
around every electrical substation in Telangana using Google Earth Engine:
- Zone 1: 0 to 3 km radius (Inner primary interconnection zone)
- Zone 2: 3 to 5 km radius (Outer secondary interconnection zone)

Evaluates:
- Terrain Slope (SRTM DEM, threshold <= 5 deg flat/gentle vs >5 deg steep)
- Water Bodies & Lakes (ESA WorldCover 10m class 80 & 90)
- Built-up & Urban Settlements (ESA WorldCover 10m class 50)
- Forest & Dense Tree Cover (ESA WorldCover 10m class 10)
- Usable Empty / Open Land (Flat, non-water, non-built, non-forest)
- Clearance Verdict (CLEAR / HIGHLY SUITABLE, MODERATE, CONSTRAINED)
"""

import os
import time
import ee
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def analyze_land_suitability():
    print("Initializing Google Earth Engine for Substation Land Suitability Analysis...")
    ee.Initialize(project='ai-voice-agent-crm')
    
    # 1. Load official TGRAC grid substations asset
    asset_id = 'projects/ai-voice-agent-crm/assets/suryagrid_tgrac_tgtransco_official'
    substations = ee.FeatureCollection(asset_id)
    count = substations.size().getInfo()
    print(f"Loaded {count} substations from {asset_id}")
    
    # 2. Define Terrain & Land Cover Imagery
    dem = ee.Image('USGS/SRTMGL1_003')
    slope = ee.Terrain.slope(dem)
    steep = slope.gt(5) # slope > 5 degrees is non-optimal / steep for solar
    
    # ESA WorldCover 10m
    wc = ee.ImageCollection('ESA/WorldCover/v200').first()
    water = wc.eq(80).Or(wc.eq(90))   # Permanent water & wetlands
    built = wc.eq(50)                 # Built-up, settlements, buildings, roads
    forest = wc.eq(10)                # Tree cover / dense forest
    
    # Unusable for ground-mounted solar: water, built-up, forest, or steep slope
    unusable = water.Or(built).Or(forest).Or(steep)
    usable = unusable.Not()            # Usable empty / open flat land
    
    # Pixel area in hectares (1 ha = 10,000 sq m)
    area_img = ee.Image.pixelArea().divide(10000.0).rename('total_ha')
    usable_img = area_img.updateMask(usable).rename('usable_ha')
    water_img = area_img.updateMask(water).rename('water_ha')
    built_img = area_img.updateMask(built).rename('built_ha')
    forest_img = area_img.updateMask(forest).rename('forest_ha')
    steep_img = area_img.updateMask(steep).rename('steep_ha')
    
    combined_img = area_img.addBands([usable_img, water_img, built_img, forest_img, steep_img])
    
    # 3. Buffer geometries
    # Zone 1: 0 to 3 km (circle)
    def make_zone_0_3(feat):
        geom_3k = feat.geometry().buffer(3000)
        return feat.setGeometry(geom_3k)
        
    # Zone 2: 3 to 5 km (donut ring)
    def make_zone_3_5(feat):
        geom_3k = feat.geometry().buffer(3000)
        geom_5k = feat.geometry().buffer(5000)
        donut = geom_5k.difference(geom_3k)
        return feat.setGeometry(donut)
        
    fc_0_3 = substations.map(make_zone_0_3)
    fc_3_5 = substations.map(make_zone_3_5)
    
    print("Running Earth Engine reduceRegions for 0 to 3 km zones (60m resolution)...")
    t0 = time.time()
    reduced_0_3 = combined_img.reduceRegions(
        collection=fc_0_3,
        reducer=ee.Reducer.sum(),
        scale=60
    ).getInfo()
    print(f"Zone 0-3km computed in {time.time()-t0:.2f}s.")
    
    print("Running Earth Engine reduceRegions for 3 to 5 km zones (60m resolution)...")
    t1 = time.time()
    reduced_3_5 = combined_img.reduceRegions(
        collection=fc_3_5,
        reducer=ee.Reducer.sum(),
        scale=60
    ).getInfo()
    print(f"Zone 3-5km computed in {time.time()-t1:.2f}s.")
    
    # 4. Process and structure records
    features_0_3 = {f['properties'].get('record_id') or f['properties'].get('Record ID'): f['properties'] for f in reduced_0_3['features']}
    features_3_5 = {f['properties'].get('record_id') or f['properties'].get('Record ID'): f['properties'] for f in reduced_3_5['features']}
    
    records = []
    
    for rid, p0 in features_0_3.items():
        p1 = features_3_5.get(rid, {})
        
        ss_name = p0.get('substation_name') or p0.get('Substation Name') or 'Unknown'
        dist = p0.get('district') or p0.get('District') or 'Unknown'
        mandal = p0.get('mandal') or p0.get('Mandal') or 'Unknown'
        volt = p0.get('voltage_level') or p0.get('Voltage Level') or 'Unknown'
        
        # 0 to 3 km metrics
        tot_0_3 = float(p0.get('total_ha') or 2800.0)
        use_0_3 = float(p0.get('usable_ha') or 0.0)
        wat_0_3 = float(p0.get('water_ha') or 0.0)
        bld_0_3 = float(p0.get('built_ha') or 0.0)
        fst_0_3 = float(p0.get('forest_ha') or 0.0)
        stp_0_3 = float(p0.get('steep_ha') or 0.0)
        
        use_pct_0_3 = (use_0_3 / tot_0_3 * 100.0) if tot_0_3 > 0 else 0.0
        wat_pct_0_3 = (wat_0_3 / tot_0_3 * 100.0) if tot_0_3 > 0 else 0.0
        bld_pct_0_3 = (bld_0_3 / tot_0_3 * 100.0) if tot_0_3 > 0 else 0.0
        stp_pct_0_3 = (stp_0_3 / tot_0_3 * 100.0) if tot_0_3 > 0 else 0.0
        
        # Verdict 0-3km
        if use_pct_0_3 >= 70.0 and use_0_3 >= 1500.0:
            verdict_0_3 = "CLEAR / HIGHLY SUITABLE"
        elif use_pct_0_3 >= 40.0:
            verdict_0_3 = "MODERATE / PARTIALLY CLEAR"
        else:
            verdict_0_3 = "CONSTRAINED (Urban/Water/Steep)"
            
        # 3 to 5 km metrics
        tot_3_5 = float(p1.get('total_ha') or 4950.0)
        use_3_5 = float(p1.get('usable_ha') or 0.0)
        wat_3_5 = float(p1.get('water_ha') or 0.0)
        bld_3_5 = float(p1.get('built_ha') or 0.0)
        fst_3_5 = float(p1.get('forest_ha') or 0.0)
        stp_3_5 = float(p1.get('steep_ha') or 0.0)
        
        use_pct_3_5 = (use_3_5 / tot_3_5 * 100.0) if tot_3_5 > 0 else 0.0
        wat_pct_3_5 = (wat_3_5 / tot_3_5 * 100.0) if tot_3_5 > 0 else 0.0
        bld_pct_3_5 = (bld_3_5 / tot_3_5 * 100.0) if tot_3_5 > 0 else 0.0
        stp_pct_3_5 = (stp_3_5 / tot_3_5 * 100.0) if tot_3_5 > 0 else 0.0
        
        # Verdict 3-5km
        if use_pct_3_5 >= 70.0 and use_3_5 >= 3000.0:
            verdict_3_5 = "CLEAR / HIGHLY SUITABLE"
        elif use_pct_3_5 >= 40.0:
            verdict_3_5 = "MODERATE / PARTIALLY CLEAR"
        else:
            verdict_3_5 = "CONSTRAINED (Urban/Water/Steep)"
            
        # Overall Land Clearance Assessment
        if verdict_0_3 == "CLEAR / HIGHLY SUITABLE" and verdict_3_5 == "CLEAR / HIGHLY SUITABLE":
            overall_status = "FULLY CLEAR (0-5 km Prime Solar Zone)"
        elif verdict_0_3 == "CLEAR / HIGHLY SUITABLE":
            overall_status = "CLEAR (Immediate 0-3 km Preferred)"
        elif verdict_3_5 == "CLEAR / HIGHLY SUITABLE":
            overall_status = "CLEAR (Outer 3-5 km Preferred)"
        elif "MODERATE" in verdict_0_3 or "MODERATE" in verdict_3_5:
            overall_status = "MODERATE CLEARANCE (Selective Parcel Scouting)"
        else:
            overall_status = "RESTRICTED / HEAVY URBAN-WATER CONSTRAINTS"
            
        records.append({
            'Record ID': rid,
            'Substation Name': ss_name,
            'District': dist,
            'Mandal': mandal,
            'Voltage Level': volt,
            'Overall Clearance (0-5 km)': overall_status,
            
            # 0 to 3 km
            'Zone 0-3km Verdict': verdict_0_3,
            '0-3km Usable Land (ha)': round(use_0_3, 1),
            '0-3km Usable (%)': round(use_pct_0_3, 1),
            '0-3km Water/Lakes (%)': round(wat_pct_0_3, 1),
            '0-3km Built-up (%)': round(bld_pct_0_3, 1),
            '0-3km Steep Slope >5° (%)': round(stp_pct_0_3, 1),
            
            # 3 to 5 km
            'Zone 3-5km Verdict': verdict_3_5,
            '3-5km Usable Land (ha)': round(use_3_5, 1),
            '3-5km Usable (%)': round(use_pct_3_5, 1),
            '3-5km Water/Lakes (%)': round(wat_pct_3_5, 1),
            '3-5km Built-up (%)': round(bld_pct_3_5, 1),
            '3-5km Steep Slope >5° (%)': round(stp_pct_3_5, 1),
            
            '0-3km Total Area (ha)': round(tot_0_3, 1),
            '3-5km Total Area (ha)': round(tot_3_5, 1)
        })
        
    df_suitability = pd.DataFrame(records)
    
    # Save CSV
    out_csv = 'data/processed/substation_land_suitability_3km_5km.csv'
    df_suitability.to_csv(out_csv, index=False)
    print(f"\nSaved CSV: {out_csv} ({len(df_suitability)} rows)")
    
    # Print summary statistics
    print("\n--- Statewide Land Suitability Summary ---")
    print(df_suitability['Overall Clearance (0-5 km)'].value_counts())
    print("\nZone 0-3km Verdict Breakdown:")
    print(df_suitability['Zone 0-3km Verdict'].value_counts())
    print("\nZone 3-5km Verdict Breakdown:")
    print(df_suitability['Zone 3-5km Verdict'].value_counts())
    
    # 5. Add Sheet to Excel Workbook
    wb_path = 'outputs/SuryaGrid_Telangana_Statewide_Substation_Inventory.xlsx'
    wb = openpyxl.load_workbook(wb_path)
    
    sheet_name = 'LAND SUITABILITY (3KM & 5KM)'
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name, index=2)
    
    header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid") # Emerald green
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    
    headers = list(df_suitability.columns)
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
    for _, row in df_suitability.iterrows():
        ws.append(list(row.values))
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=ws.max_row, column=col_idx)
            cell.font = data_font
            cell.border = border_thin
            # Color-code verdict
            if col_idx == 6 or col_idx == 7 or col_idx == 13:
                val = str(cell.value)
                if 'FULLY CLEAR' in val or 'CLEAR / HIGHLY' in val:
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Light green
                    cell.font = Font(name="Calibri", size=10, bold=True, color="166534")
                elif 'CONSTRAINED' in val or 'RESTRICTED' in val:
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Light red
                    cell.font = Font(name="Calibri", size=10, bold=True, color="991B1B")
                elif 'MODERATE' in val:
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid") # Light yellow
                    cell.font = Font(name="Calibri", size=10, bold=True, color="92400E")
                    
    for col in ws.columns:
        max_len = max(len(str(c.value or '')) for c in col[:50])
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)
        
    wb.save(wb_path)
    print(f"Added '{sheet_name}' sheet to {wb_path} (Total sheets: {len(wb.sheetnames)})")
    
    return df_suitability

if __name__ == '__main__':
    analyze_land_suitability()
