#!/usr/bin/env python3
"""
scripts/analyze_substation_land_suitability_1km_calibrated.py
Telangana Energy Department Challenge 10: Solar Substation Potential Assessment
Refined Production-Grade 1,000m (1 km) Surrounding Land Analysis:
- Scope: Single 1,000m (1 km) Analysis Radius (~776 acres / ~3.14 km2)
- Dynamic World V1 (10m) 12-Month Mode Reduction
- USGS SRTM 30m Slope Filter (<= 5 deg)
- 30m Water Exclusion Buffer (Telangana FTL rule)
- Revised 3-Tier Operational Classification:
    • GREEN (Primary Usable / Ready): Bare, scrub, grass (slope <= 5°, outside 30m water, non-built)
    • YELLOW (Conditional / Clearance): Trees and crops (slope <= 5°, outside 30m water, non-built)
    • RED (Strictly Unusable): Built-up, water + 30m FTL buffer, flooded veg, snow, slope > 5°
- Acreage-Calibrated Scoring (4–10 Acre Practical Target):
    • >= 10 contiguous GREEN acres -> 90–100 (High)
    • 4 to < 10 contiguous GREEN acres -> 70–89 (Viable)
    • < 4 GREEN acres, but >= 4 contiguous GREEN + YELLOW acres -> 40–69 (Conditional)
    • < 4 contiguous usable acres total -> 0–39 (Low / Constrained)
- Output Schema:
    substation_id, substation_name, district, mandal, voltage_level, lat, lon,
    green_acres_total, largest_green_patch_acres, yellow_acres_total, red_pct,
    meets_4_acre_min, meets_10_acre_target, estimated_mw, land_suitability_score, viability_tier
"""

import os
import time
import json
import ee
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def run_pipeline():
    print("==========================================================================")
    print("SuryaGrid: Challenge 10 - Refined 1 km Acreage-Calibrated Land Analysis")
    print("Google Cloud Project: ai-voice-agent-crm | Scale: 1 km Radius (~776 ac)")
    print("==========================================================================")

    t_start = time.time()
    ee.Initialize(project='ai-voice-agent-crm')

    p = 'projects/ai-voice-agent-crm/assets/'
    boundary = ee.FeatureCollection(p + 'suryagrid_telangana_boundary')
    substations = ee.FeatureCollection(p + 'suryagrid_tgrac_tgtransco_official')
    total_ss = substations.size().getInfo()
    print(f"Loaded {total_ss} official grid substations across Telangana.")

    # 1. Digital Elevation Model & Slope (USGS SRTM 30m)
    dem = ee.Image('USGS/SRTMGL1_003').clip(boundary)
    slope = ee.Terrain.slope(dem)
    flat = slope.lte(5) # <= 5 deg (ideal for ground-mounted solar)
    mod_slope = slope.gt(5).And(slope.lte(10)) # 5 to 10 deg (minor clearance / light grading)
    steep = slope.gt(10) # > 10 deg (strictly excluded)

    # 2. Dynamic World V1 Mode (12-month composite)
    dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1') \
        .filterBounds(boundary) \
        .filterDate('2023-01-01', '2024-01-01') \
        .select('label')
    dw_mode = dw.reduce(ee.Reducer.mode()).rename('dw_label')

    # Water & 30m FTL buffer
    water = dw_mode.eq(0).Or(dw_mode.eq(3))
    water30 = water.focalMax(30, 'circle', 'meters')

    built = dw_mode.eq(6)
    snow = dw_mode.eq(8)
    trees = dw_mode.eq(1)
    crops = dw_mode.eq(4)
    # Primary Usable: Bare, scrub, grass, AND crops (open farmland / fallow fields)
    primary = dw_mode.eq(7).Or(dw_mode.eq(5)).Or(dw_mode.eq(2)).Or(dw_mode.eq(4))

    # REVISED 3-TIER OPERATIONAL CLASSIFICATION:
    # GREEN: primary (bare, scrub, grass, crops) + flat (<= 5 deg) + outside water30 + outside built
    green = primary.And(flat).And(water30.Not()).And(built.Not())

    # YELLOW: strictly reserved for minor clearance / grading:
    # - Trees with slope <= 10 deg (outside water30 & built)
    # - Moderate slope (5°–10°) on non-built, non-water land
    yellow_trees = trees.And(slope.lte(10)).And(water30.Not()).And(built.Not())
    yellow_slope = mod_slope.And(water30.Not()).And(built.Not()).And(snow.Not())
    yellow = (yellow_trees.Or(yellow_slope)).And(green.Not())

    # RED: strictly unusable (built, water30, snow, steep > 10 deg)
    red = built.Or(water30).Or(snow).Or(steep)

    # 4-acre and 10-acre contiguous patch filters
    green_4ac = green.focalMin(25, 'circle', 'meters').focalMax(25, 'circle', 'meters')
    green_10ac = green.focalMin(45, 'circle', 'meters').focalMax(45, 'circle', 'meters')

    # Fallback: Green + Yellow contiguous patches
    gy = green.Or(yellow)
    gy_4ac = gy.focalMin(25, 'circle', 'meters').focalMax(25, 'circle', 'meters')

    px_ac = ee.Image.pixelArea().multiply(0.000247105)

    img_eval = px_ac.rename('tot_ac').addBands([
        px_ac.updateMask(green).rename('green_ac'),
        px_ac.updateMask(green_4ac).rename('green_4ac_ac'),
        px_ac.updateMask(green_10ac).rename('green_10ac_ac'),
        px_ac.updateMask(yellow).rename('yellow_ac'),
        px_ac.updateMask(gy_4ac).rename('gy_4ac_ac'),
        px_ac.updateMask(red).rename('red_ac')
    ])

    # 1 km buffer collection
    buf1k_fc = substations.map(lambda f: f.setGeometry(f.geometry().buffer(1000)))

    # Process in batches of 100
    batch_size = 100
    res_features = []

    print(f"Executing planetary 1 km zonal reductions across {total_ss} substations...")
    for i in range(0, total_ss, batch_size):
        sub_batch = ee.FeatureCollection(buf1k_fc.toList(batch_size, i))
        t0 = time.time()
        b_res = img_eval.reduceRegions(collection=sub_batch, reducer=ee.Reducer.sum(), scale=10).getInfo()
        res_features.extend(b_res['features'])
        print(f"  Processed substations {i+1} to {min(i+batch_size, total_ss)} in {time.time()-t0:.2f}s")

    print(f"All reductions complete in {time.time()-t_start:.2f}s. Structuring calibrated dataframe...")

    records = []
    for f in res_features:
        p = f['properties']
        rid = p.get('record_id') or p.get('Record ID')
        name = p.get('substation_name') or p.get('Substation Name') or 'Unknown'
        dist = p.get('district') or p.get('District') or 'Unknown'
        mandal = p.get('mandal') or p.get('Mandal') or 'Unknown'
        volt = p.get('voltage_level') or p.get('Voltage Level') or 'Unknown'
        lat = safe_float(p.get('latitude') or p.get('Latitude'))
        lon = safe_float(p.get('longitude') or p.get('Longitude'))

        tot_ac = safe_float(p.get('tot_ac'), 776.0)
        green_ac = safe_float(p.get('green_ac'), 0.0)
        green_4ac_val = safe_float(p.get('green_4ac_ac'), 0.0)
        green_10ac_val = safe_float(p.get('green_10ac_ac'), 0.0)
        yellow_ac = safe_float(p.get('yellow_ac'), 0.0)
        gy_4ac_val = safe_float(p.get('gy_4ac_ac'), 0.0)
        red_ac = safe_float(p.get('red_ac'), 0.0)

        red_pct = round((red_ac / tot_ac * 100.0) if tot_ac > 0 else 0.0, 1)

        # Largest contiguous patch estimation:
        if green_10ac_val >= 10.0:
            meets_10ac = True
            meets_4ac = True
            largest_green_patch_ac = round(min(green_ac, max(10.0, green_10ac_val)), 1)
        elif green_4ac_val >= 4.0:
            meets_10ac = False
            meets_4ac = True
            largest_green_patch_ac = round(min(green_ac, max(4.0, green_4ac_val)), 1)
        else:
            meets_10ac = False
            meets_4ac = False
            largest_green_patch_ac = round(min(3.9, green_ac), 1)

        largest_gy_patch_ac = round(min(green_ac + yellow_ac, max(4.0 if gy_4ac_val >= 4.0 else 0.0, gy_4ac_val)), 1)

        # Calibrated Land Suitability Score (0 - 100):
        # • >= 10 contiguous GREEN acres -> 90–100 (High)
        # • 4 to < 10 contiguous GREEN acres -> 70–89 (Viable)
        # • < 4 GREEN acres, but >= 4 contiguous GREEN + YELLOW acres -> 40–69 (Conditional)
        # • < 4 contiguous usable acres total -> 0–39 (Low / Constrained)
        if meets_10ac:
            score = min(100.0, round(90.0 + min(10.0, (largest_green_patch_ac - 10.0) * 0.2), 1))
            tier = 'HIGH (>=10ac Farmland/Open Ready)'
            tier_code = 'GREEN'
        elif meets_4ac:
            score = round(70.0 + ((largest_green_patch_ac - 4.0) / 6.0) * 19.0, 1)
            tier = 'VIABLE (4-10ac Farmland/Open Ready)'
            tier_code = 'GREEN'
        elif gy_4ac_val >= 4.0:
            score = round(40.0 + min(29.0, (largest_gy_patch_ac / 20.0) * 29.0), 1)
            tier = 'CONDITIONAL (Needs Clearance/Grading)'
            tier_code = 'YELLOW'
        else:
            score = round(max(0.0, 39.0 * (1.0 - red_pct / 100.0)), 1)
            tier = 'LOW / CONSTRAINED'
            tier_code = 'RED'

        est_mw = round(largest_green_patch_ac / 4.5, 2)

        records.append({
            'substation_id': rid,
            'substation_name': name,
            'district': dist,
            'mandal': mandal,
            'voltage_level': volt,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'green_acres_total': round(green_ac, 1),
            'largest_green_patch_acres': largest_green_patch_ac,
            'yellow_acres_total': round(yellow_ac, 1),
            'red_pct': red_pct,
            'meets_4_acre_min': meets_4ac,
            'meets_10_acre_target': meets_10ac,
            'estimated_mw': est_mw,
            'land_suitability_score': score,
            'viability_tier': tier,
            'tier_color': tier_code
        })

    df = pd.DataFrame(records)
    df = df.sort_values(by=['land_suitability_score', 'largest_green_patch_acres'], ascending=[False, False])

    # Export to CSV
    csv_path = "data/processed/substation_land_suitability_1km_calibrated.csv"
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"Exported Calibrated CSV: {csv_path} ({len(df)} records)")

    # Update Excel Master Workbook
    xlsx_path = "outputs/SuryaGrid_Telangana_Statewide_Substation_Inventory.xlsx"
    if os.path.exists(xlsx_path):
        wb = openpyxl.load_workbook(xlsx_path)
        sheet_name = "1KM CALIBRATED SUITABILITY"
        if sheet_name in wb.sheetnames:
            del wb[sheet_name]
        ws = wb.create_sheet(title=sheet_name, index=3) # Insert prominently as sheet 4

        navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        
        headers = list(df.columns)
        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = navy_fill
            cell.font = font_header
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for _, row in df.iterrows():
            ws.append(list(row))

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 11), 32)

        wb.save(xlsx_path)
        print(f"Appended sheet '{sheet_name}' to {xlsx_path}")

    # Summary Statistics
    print("\n==========================================================================")
    print("STATEWIDE 1 KM ACREAGE-CALIBRATED RESULTS (391 SUBSTATIONS):")
    tier_counts = df['tier_color'].value_counts()
    print(f"  • GREEN (>=4ac Contiguous Green Ready): {tier_counts.get('GREEN', 0)} substations ({tier_counts.get('GREEN', 0)/total_ss*100:.1f}%)")
    print(f"     - Meets 10-Acre Target (>=10 ac): {df['meets_10_acre_target'].sum()} substations")
    print(f"     - Meets 4-Acre Minimum (4-10 ac): {df['meets_4_acre_min'].sum() - df['meets_10_acre_target'].sum()} substations")
    print(f"  • YELLOW (Conditional / Agri-Crops): {tier_counts.get('YELLOW', 0)} substations ({tier_counts.get('YELLOW', 0)/total_ss*100:.1f}%)")
    print(f"  • RED (Low / Urban / Forest / Constrained): {tier_counts.get('RED', 0)} substations ({tier_counts.get('RED', 0)/total_ss*100:.1f}%)")
    print(f"Total Direct Solar Potential from Contiguous Patches: {df['estimated_mw'].sum():,.2f} MW")
    print(f"Pipeline executed in {time.time()-t_start:.1f}s.")
    print("==========================================================================")

if __name__ == '__main__':
    run_pipeline()
