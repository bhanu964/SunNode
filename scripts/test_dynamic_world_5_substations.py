import time
import ee
import pandas as pd
import json

print("Initializing Earth Engine...")
ee.Initialize(project='ai-voice-agent-crm')

# 1. Load substations asset & select 5 diverse sample substations
asset_id = 'projects/ai-voice-agent-crm/assets/suryagrid_tgrac_tgtransco_official'
all_ss = ee.FeatureCollection(asset_id)

# Pick 5 diverse sample substations:
# 1 rural prime (Medaram 400kV), 1 suburban (Gajwel 400kV), 1 urban (Narayanguda 132kV), 
# 1 agricultural (Kondapaka 220kV), 1 water-adjacent (Chalakurthy 220kV)
sample_names = ['Medaram (400KV)', 'Gajwel (400KV)', 'Narayanguda', 'Kondapaka', 'Chalakurthy']
sample_fc = all_ss.filter(ee.Filter.inList('substation_name', sample_names))
print("Sample substations count:", sample_fc.size().getInfo())

# 2. Dynamic World V1 (12-month mode reduction)
boundary = ee.FeatureCollection('projects/ai-voice-agent-crm/assets/suryagrid_telangana_boundary')

# Filter over 12 months
dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1') \
    .filterBounds(sample_fc.geometry().buffer(5000)) \
    .filterDate('2023-01-01', '2024-01-01') \
    .select('label')

dw_mode = dw.reduce(ee.Reducer.mode()).rename('dw_label')

# Classes:
# 0: water, 1: trees, 2: grass, 3: flooded_vegetation, 4: crops,
# 5: shrub_and_scrub, 6: built, 7: bare, 8: snow_and_ice
water = dw_mode.eq(0).Or(dw_mode.eq(3))
built = dw_mode.eq(6)
trees = dw_mode.eq(1)
crops = dw_mode.eq(4) # Agricultural / conditional

# 30m Water Exclusion Buffer (Telangana FTL rule)
water_buffer30m = water.focalMax(30, 'circle', 'meters')

# Excluded (Red): built, trees, water + 30m buffer
excluded = built.Or(trees).Or(water_buffer30m)

# Primary Usable classes: bare (7), shrub (5), grass (2)
primary_land = dw_mode.eq(7).Or(dw_mode.eq(5)).Or(dw_mode.eq(2))

# 3. Terrain Slope Filter (USGS SRTM 30m)
dem = ee.Image('USGS/SRTMGL1_003')
slope = ee.Terrain.slope(dem)
flat = slope.lte(5) # Slope <= 5 deg

# Raw Primary Usable Mask: primary land + flat slope, strictly excluding water+30m buffer, built, trees
raw_usable = primary_land.And(flat).And(excluded.Not())

# 4. Contiguous Usable Area Filter (>= 5 acres = 20,235 m2)
# At 10m Sentinel/Dynamic World scale: 1 px = 100 m2 -> 202 pixels = 20,200 m2
connected_px = raw_usable.connectedPixelCount(250, True)
contiguous_5ac = connected_px.gte(202)
final_usable = raw_usable.And(contiguous_5ac)

# Pixel area in acres: 1 m2 = 0.000247105 acres (1 acre = 4046.86 m2)
px_acres = ee.Image.pixelArea().multiply(0.000247105)

total_acres_img = px_acres.rename('total_acres')
usable_acres_img = px_acres.updateMask(final_usable).rename('usable_acres')
crops_acres_img = px_acres.updateMask(crops).rename('crops_acres')
water_acres_img = px_acres.updateMask(water_buffer30m).rename('water_acres')
built_acres_img = px_acres.updateMask(built).rename('built_acres')
trees_acres_img = px_acres.updateMask(trees).rename('trees_acres')

analysis_img = total_acres_img.addBands([
    usable_acres_img, crops_acres_img, water_acres_img, built_acres_img, trees_acres_img
])

# 5. Buffer Analysis (1,000m and 2,000m)
buf1k_fc = sample_fc.map(lambda f: f.setGeometry(f.geometry().buffer(1000)))
buf2k_fc = sample_fc.map(lambda f: f.setGeometry(f.geometry().buffer(2000)))

print("Computing 1 km buffer statistics (10m scale)...")
t0 = time.time()
res_1k = analysis_img.reduceRegions(collection=buf1k_fc, reducer=ee.Reducer.sum(), scale=10).getInfo()
print(f"1 km buffer done in {time.time()-t0:.2f}s")

print("Computing 2 km buffer statistics (10m scale)...")
t1 = time.time()
res_2k = analysis_img.reduceRegions(collection=buf2k_fc, reducer=ee.Reducer.sum(), scale=10).getInfo()
print(f"2 km buffer done in {time.time()-t1:.2f}s")

# Structure records
dict_2k = {f['properties']['substation_name']: f['properties'] for f in res_2k['features']}

results = []
for f in res_1k['features']:
    p1 = f['properties']
    name = p1['substation_name']
    p2 = dict_2k.get(name, {})
    
    tot_1k = float(p1.get('total_acres') or 776.0) # ~3.14 km2 = ~776 acres
    use_1k = float(p1.get('usable_acres') or 0.0)
    crp_1k = float(p1.get('crops_acres') or 0.0)
    wat_1k = float(p1.get('water_acres') or 0.0)
    bld_1k = float(p1.get('built_acres') or 0.0)
    trs_1k = float(p1.get('trees_acres') or 0.0)
    
    tot_2k = float(p2.get('total_acres') or 3103.0) # ~12.56 km2 = ~3,103 acres
    use_2k = float(p2.get('usable_acres') or 0.0)
    crp_2k = float(p2.get('crops_acres') or 0.0)
    wat_2k = float(p2.get('water_acres') or 0.0)
    bld_2k = float(p2.get('built_acres') or 0.0)
    trs_2k = float(p2.get('trees_acres') or 0.0)
    
    pct_use_1k = (use_1k / tot_1k) * 100.0 if tot_1k > 0 else 0.0
    pct_use_2k = (use_2k / tot_2k) * 100.0 if tot_2k > 0 else 0.0
    has_5ac = (use_1k >= 5.0) or (use_2k >= 5.0)
    
    # Solar capacity targeting 4.5 acres per MW
    solar_cap_1k = round(use_1k / 4.5, 2)
    solar_cap_2k = round(use_2k / 4.5, 2)
    
    # Score (0 - 100)
    score = min(100.0, round(
        (min(pct_use_1k, 50.0) * 1.0) +
        (min(pct_use_2k, 50.0) * 0.6) +
        (20.0 if has_5ac else 0.0), 1
    ))
    
    results.append({
        'Substation Name': name,
        'District': p1.get('district'),
        'Mandal': p1.get('mandal'),
        'Voltage': p1.get('voltage_level'),
        '1km Total (ac)': round(tot_1k, 1),
        '1km Usable (ac)': round(use_1k, 1),
        '1km Usable (%)': round(pct_use_1k, 1),
        '1km Crops (%)': round((crp_1k/tot_1k)*100, 1),
        '1km Water (%)': round((wat_1k/tot_1k)*100, 1),
        '1km Built (%)': round((bld_1k/tot_1k)*100, 1),
        '1km Solar MW': solar_cap_1k,
        '2km Total (ac)': round(tot_2k, 1),
        '2km Usable (ac)': round(use_2k, 1),
        '2km Usable (%)': round(pct_use_2k, 1),
        '2km Solar MW': solar_cap_2k,
        'Has >=5ac Contiguous': has_5ac,
        'Suitability Score': score
    })

df_res = pd.DataFrame(results)
print("\n=== SAMPLE 5 SUBSTATIONS TEST RESULTS ===")
print(df_res.to_string(index=False))
