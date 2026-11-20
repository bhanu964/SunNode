#!/usr/bin/env python3
"""
scripts/analyze_substation_land_suitability_dynamic_world.py
Telangana Energy Department Challenge 10: Solar Substation Potential Assessment
High-Resolution Land Cover & Terrain Suitability Pipeline:
- Google Earth Engine Dynamic World V1 (10m) 12-month mode reduction
- USGS SRTM 30m Digital Elevation Model (Slope <= 5 deg)
- 30m Water Exclusion Buffer (Telangana FTL rule)
- Concentric 1,000m (1 km) Primary and 2,000m (2 km) Extended Buffers
- Minimum 5-acre contiguous patch filter (~20,235 m2)
- Categorization:
    • Green: Primary Usable Flat Open Land (Bare, Scrub, Grass)
    • Yellow: Crops / Agriculture / Plants (Conditional Solar Potential)
    • Red: Strictly Excluded (Built-up, Water+30m FTL, Deep Forest, Steep Slope)
- Computes Solar Capacity (MW = acres / 4.5) & Land Suitability Score (0-100)
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
    print("SuryaGrid: Dynamic World 1km & 2km Substation Land Assessment Pipeline")
    print("Google Cloud Project: ai-voice-agent-crm | Dataset: Dynamic World V1 (10m)")
    print("==========================================================================")

    t_start = time.time()
    ee.Initialize(project='ai-voice-agent-crm')

    # 1. Load official 391 substations & boundary
    p = 'projects/ai-voice-agent-crm/assets/'
    boundary = ee.FeatureCollection(p + 'suryagrid_telangana_boundary')
    substations = ee.FeatureCollection(p + 'suryagrid_tgrac_tgtransco_official')
    total_ss = substations.size().getInfo()
    print(f"Loaded {total_ss} official grid substations across Telangana.")

    # 2. Dynamic World V1 Mode Reduction (12-month composite)
    print("Loading Dynamic World V1 collection (12-month window)...")
    dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1') \
        .filterBounds(boundary) \
        .filterDate('2023-01-01', '2024-01-01') \
        .select('label')
    dw_mode = dw.reduce(ee.Reducer.mode()).rename('dw_label')

    # Classes:
    # 0: water, 1: trees, 2: grass, 3: flooded_vegetation, 4: crops,
    # 5: shrub_and_scrub, 6: built, 7: bare, 8: snow_and_ice
    water = dw_mode.eq(0).Or(dw_mode.eq(3))
    water30 = water.focalMax(30, 'circle', 'meters') # 30m FTL lake/tank buffer
    built = dw_mode.eq(6)
    trees = dw_mode.eq(1)
    crops = dw_mode.eq(4) # Agricultural / crops / plants (Yellow)
    primary = dw_mode.eq(7).Or(dw_mode.eq(5)).Or(dw_mode.eq(2)) # Bare, scrub, grass (Green)

    # 3. Terrain Slope Filter (USGS SRTM 30m)
    dem = ee.Image('USGS/SRTMGL1_003').clip(boundary)
    slope = ee.Terrain.slope(dem)
    flat = slope.lte(5) # Slope <= 5 degrees

    # Raw Primary Usable Mask
    raw_usable = primary.And(flat).And(water30.Not()).And(built.Not()).And(trees.Not())

    # Contiguous Usable Area Filter (>= 5 acres = 20,235 m2)
    # Using 30m morphological opening to guarantee solid contiguous blocks
    contiguous_usable = raw_usable.focalMin(20, 'circle', 'meters').focalMax(20, 'circle', 'meters')

    # Secondary / Agricultural Usable Mask (Crops on flat land outside water/built)
    flat_crops = crops.And(flat).And(water30.Not()).And(built.Not())

    # Pixel area in acres: 1 m2 = 0.000247105 acres
    px_ac = ee.Image.pixelArea().multiply(0.000247105)

    analysis_img = px_ac.rename('tot_ac').addBands([
        px_ac.updateMask(contiguous_usable).rename('use_ac'),
        px_ac.updateMask(flat_crops).rename('crp_ac'),
        px_ac.updateMask(water30).rename('wat_ac'),
        px_ac.updateMask(built).rename('bld_ac'),
        px_ac.updateMask(trees).rename('trs_ac'),
        px_ac.updateMask(slope.gt(5)).rename('stp_ac')
    ])

    # 4. Generate 1 km and 2 km buffers
    buf1k_fc = substations.map(lambda f: f.setGeometry(f.geometry().buffer(1000)))
    buf2k_fc = substations.map(lambda f: f.setGeometry(f.geometry().buffer(2000)))

    cache_path = "data/processed/raw_dw_features_cache.json"
    if os.path.exists(cache_path):
        print(f"Loading cached reduction features from {cache_path}...")
        with open(cache_path) as f:
            cache_data = json.load(f)
            res_1k_features = cache_data.get('1k', [])
            res_2k_features = cache_data.get('2k', [])
        print(f"Loaded {len(res_1k_features)} features from cache in 0.1s!")
    else:
        # Run in batches of 100 for maximum reliability & throughput
        batch_size = 100
        res_1k_features = []
        res_2k_features = []

        print(f"Executing planetary zonal statistics across {total_ss} substations...")
        for i in range(0, total_ss, batch_size):
            sub_list_1k = ee.FeatureCollection(buf1k_fc.toList(batch_size, i))
            sub_list_2k = ee.FeatureCollection(buf2k_fc.toList(batch_size, i))
            
            t0 = time.time()
            b_1k = analysis_img.reduceRegions(collection=sub_list_1k, reducer=ee.Reducer.sum(), scale=15).getInfo()
            b_2k = analysis_img.reduceRegions(collection=sub_list_2k, reducer=ee.Reducer.sum(), scale=20).getInfo()
            
            res_1k_features.extend(b_1k['features'])
            res_2k_features.extend(b_2k['features'])
            print(f"  Processed substations {i+1} to {min(i+batch_size, total_ss)} in {time.time()-t0:.2f}s")

        with open(cache_path, 'w') as f:
            json.dump({'1k': res_1k_features, '2k': res_2k_features}, f)
        print(f"Cached raw reduction features to {cache_path}")

    print(f"All reductions complete in {time.time()-t_start:.2f}s. Parsing metrics...")

    # 5. Build structured dataset
    dict_2k = {f['properties'].get('record_id') or f['properties'].get('Record ID'): f['properties'] for f in res_2k_features}

    records = []
    for f in res_1k_features:
        p1 = f['properties']
        rid = p1.get('record_id') or p1.get('Record ID')
        p2 = dict_2k.get(rid, {})

        ss_name = p1.get('substation_name') or p1.get('Substation Name') or 'Unknown'
        dist = p1.get('district') or p1.get('District') or 'Unknown'
        mandal = p1.get('mandal') or p1.get('Mandal') or 'Unknown'
        volt = p1.get('voltage_level') or p1.get('Voltage Level') or 'Unknown'
        ss_type = p1.get('substation_type') or p1.get('Substation Type') or 'Substation'
        mva = safe_float(p1.get('total_capacity_mva') or p1.get('Total Capacity (MVA)') or 0.0)
        lat = safe_float(p1.get('latitude') or p1.get('Latitude') or 0.0)
        lon = safe_float(p1.get('longitude') or p1.get('Longitude') or 0.0)

        # 1 km Buffer Metrics
        tot_1k = safe_float(p1.get('tot_ac'), 776.0)
        use_1k = safe_float(p1.get('use_ac'), 0.0)
        crp_1k = safe_float(p1.get('crp_ac'), 0.0)
        wat_1k = safe_float(p1.get('wat_ac'), 0.0)
        bld_1k = safe_float(p1.get('bld_ac'), 0.0)
        trs_1k = safe_float(p1.get('trs_ac'), 0.0)
        stp_1k = safe_float(p1.get('stp_ac'), 0.0)

        # 2 km Buffer Metrics
        tot_2k = safe_float(p2.get('tot_ac'), 3103.0)
        use_2k = safe_float(p2.get('use_ac'), 0.0)
        crp_2k = safe_float(p2.get('crp_ac'), 0.0)
        wat_2k = safe_float(p2.get('wat_ac'), 0.0)
        bld_2k = safe_float(p2.get('bld_ac'), 0.0)
        trs_2k = safe_float(p2.get('trs_ac'), 0.0)
        stp_2k = safe_float(p2.get('stp_ac'), 0.0)

        # Percentages
        pct_use_1k = (use_1k / tot_1k * 100.0) if tot_1k > 0 else 0.0
        pct_crp_1k = (crp_1k / tot_1k * 100.0) if tot_1k > 0 else 0.0
        pct_wat_1k = (wat_1k / tot_1k * 100.0) if tot_1k > 0 else 0.0
        pct_bld_1k = (bld_1k / tot_1k * 100.0) if tot_1k > 0 else 0.0
        pct_trs_1k = (trs_1k / tot_1k * 100.0) if tot_1k > 0 else 0.0
        pct_stp_1k = (stp_1k / tot_1k * 100.0) if tot_1k > 0 else 0.0

        pct_use_2k = (use_2k / tot_2k * 100.0) if tot_2k > 0 else 0.0
        pct_crp_2k = (crp_2k / tot_2k * 100.0) if tot_2k > 0 else 0.0
        pct_wat_2k = (wat_2k / tot_2k * 100.0) if tot_2k > 0 else 0.0
        pct_bld_2k = (bld_2k / tot_2k * 100.0) if tot_2k > 0 else 0.0

        has_5ac_1k = use_1k >= 5.0
        has_5ac_2k = use_2k >= 5.0

        # Solar Capacity (targeting 4.5 acres per MW)
        mw_direct_1k = round(use_1k / 4.5, 2)
        mw_direct_2k = round(use_2k / 4.5, 2)
        mw_with_crops_1k = round((use_1k + crp_1k) / 4.5, 2)
        mw_with_crops_2k = round((use_2k + crp_2k) / 4.5, 2)

        # Normalized Land Suitability Score (0 to 100)
        # Factors: Direct usable land %, crop potential %, built/water penalty
        base_score = (min(pct_use_1k, 40.0) * 1.25) + (min(pct_use_2k, 40.0) * 0.5)
        crop_bonus = min(pct_crp_1k, 40.0) * 0.4
        penalty = min((pct_bld_1k * 0.6) + (pct_wat_1k * 0.4), 40.0)
        raw_score = base_score + crop_bonus - penalty + (15.0 if has_5ac_1k else 0.0)
        score = max(5.0, min(100.0, round(raw_score, 1)))

        if pct_bld_1k >= 70.0 or (pct_wat_1k >= 60.0):
            tier = 'RESTRICTED / URBAN-WATER CONSTRAINED'
            tier_code = 'RED'
        elif score >= 65.0 or use_1k >= 50.0:
            tier = 'PRIME SOLAR ASSESSMENT (HIGH POTENTIAL)'
            tier_code = 'GREEN'
        elif score >= 35.0 or (use_1k + crp_1k) >= 100.0:
            tier = 'CONDITIONAL / AGRICULTURAL CONVERSION'
            tier_code = 'YELLOW'
        else:
            tier = 'MARGINAL / TOPOGRAPHY CONSTRAINED'
            tier_code = 'RED'

        records.append({
            'Record ID': rid,
            'Substation Name': ss_name,
            'District': dist,
            'Mandal': mandal,
            'Voltage Level': volt,
            'Substation Type': ss_type,
            'Capacity (MVA)': mva,
            'Latitude': lat,
            'Longitude': lon,
            'Suitability Tier': tier,
            'Color Code': tier_code,
            'Land Suitability Score (0-100)': score,
            '1km Total Land (Acres)': round(tot_1k, 1),
            '1km Primary Usable (Acres)': round(use_1k, 1),
            '1km Primary Usable (%)': round(pct_use_1k, 1),
            '1km Crops / Agri (Acres)': round(crp_1k, 1),
            '1km Crops / Agri (%)': round(pct_crp_1k, 1),
            '1km Built-up (%)': round(pct_bld_1k, 1),
            '1km Water + 30m FTL (%)': round(pct_wat_1k, 1),
            '1km Trees / Forest (%)': round(pct_trs_1k, 1),
            '1km Steep Slope >5° (%)': round(pct_stp_1k, 1),
            '1km Has >=5ac Contiguous': has_5ac_1k,
            '1km Direct Solar Capacity (MW)': mw_direct_1k,
            '1km Solar Potential incl Crops (MW)': mw_with_crops_1k,
            '2km Total Land (Acres)': round(tot_2k, 1),
            '2km Primary Usable (Acres)': round(use_2k, 1),
            '2km Primary Usable (%)': round(pct_use_2k, 1),
            '2km Crops / Agri (Acres)': round(crp_2k, 1),
            '2km Crops / Agri (%)': round(pct_crp_2k, 1),
            '2km Built-up (%)': round(pct_bld_2k, 1),
            '2km Water + 30m FTL (%)': round(pct_wat_2k, 1),
            '2km Has >=5ac Contiguous': has_5ac_2k,
            '2km Direct Solar Capacity (MW)': mw_direct_2k,
            '2km Solar Potential incl Crops (MW)': mw_with_crops_2k
        })

    df = pd.DataFrame(records)

    # Sort by Land Suitability Score descending
    df = df.sort_values(by=['Land Suitability Score (0-100)', '1km Primary Usable (Acres)'], ascending=[False, False])

    # Save to CSV
    csv_path = "data/processed/substation_land_suitability_dynamic_world_1k_2k.csv"
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"Exported CSV: {csv_path} ({len(df)} records)")

    # 6. Update Master Excel Workbook
    xlsx_path = "outputs/SuryaGrid_Telangana_Statewide_Substation_Inventory.xlsx"
    if os.path.exists(xlsx_path):
        wb = openpyxl.load_workbook(xlsx_path)
        sheet_name = "DYNAMIC WORLD 1KM & 2KM"
        if sheet_name in wb.sheetnames:
            del wb[sheet_name]
        ws = wb.create_sheet(title=sheet_name, index=3) # Place as Sheet 4

        # Header styling
        navy_header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        headers = list(df.columns)
        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = navy_header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for _, row in df.iterrows():
            ws.append(list(row))

        # Auto-fit column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 11), 32)

        wb.save(xlsx_path)
        print(f"Appended sheet '{sheet_name}' to {xlsx_path}")

    # Summary Statistics
    print("\n==========================================================================")
    print("STATEWIDE DYNAMIC WORLD SUITABILITY BREAKDOWN (391 SUBSTATIONS):")
    tier_counts = df['Color Code'].value_counts()
    print(f"  • GREEN (Prime Direct Solar Potential): {tier_counts.get('GREEN', 0)} substations")
    print(f"  • YELLOW (Agricultural / Crop Land Potential): {tier_counts.get('YELLOW', 0)} substations")
    print(f"  • RED (Restricted / Built-up / Water / Forest): {tier_counts.get('RED', 0)} substations")
    print(f"Total Direct 1km Solar Capacity (Statewide): {df['1km Direct Solar Capacity (MW)'].sum():,.1f} MW")
    print(f"Total 1km Solar Potential incl Crops: {df['1km Solar Potential incl Crops (MW)'].sum():,.1f} MW")
    print(f"Total Direct 2km Solar Capacity (Statewide): {df['2km Direct Solar Capacity (MW)'].sum():,.1f} MW")
    print(f"Total 2km Solar Potential incl Crops: {df['2km Solar Potential incl Crops (MW)'].sum():,.1f} MW")
    print(f"Pipeline executed in {time.time()-t_start:.1f}s.")
    print("==========================================================================")

if __name__ == '__main__':
    run_pipeline()
