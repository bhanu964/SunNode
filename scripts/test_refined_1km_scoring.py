import time
import ee
import pandas as pd

print("Initializing Earth Engine...")
ee.Initialize(project='ai-voice-agent-crm')

p = 'projects/ai-voice-agent-crm/assets/'
substations = ee.FeatureCollection(p + 'suryagrid_tgrac_tgtransco_official')
boundary = ee.FeatureCollection(p + 'suryagrid_telangana_boundary')

test_names = ['Narayanguda', 'K.M.Pally (220KV)', 'Ganeshpahad', 'Kondapaka', 'Gajwel (400KV)']
sample = substations.filter(ee.Filter.inList('substation_name', test_names))

# 1. Digital Elevation Model & Slope
dem = ee.Image('USGS/SRTMGL1_003').clip(boundary)
slope = ee.Terrain.slope(dem)
flat = slope.lte(5) # <= 5 deg
steep = slope.gt(5) # > 5 deg

# 2. Dynamic World V1 Mode (12 months)
dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1') \
    .filterBounds(sample.geometry().buffer(2000)) \
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
bare = dw_mode.eq(7)
scrub = dw_mode.eq(5)
grass = dw_mode.eq(2)

# --- REVISED 3-TIER OPERATIONAL ZONES ---
# GREEN — Primary Usable (Ready): bare, scrub, grass with slope <= 5° (outside 30 m water buffer & outside built)
primary_veg = bare.Or(scrub).Or(grass)
green = primary_veg.And(flat).And(water30.Not()).And(built.Not())

# YELLOW — Conditional (Needs Ground Verification / Clearance): trees and crops with slope <= 5° (outside 30m water & outside built)
cond_veg = trees.Or(crops)
yellow = cond_veg.And(flat).And(water30.Not()).And(built.Not())

# RED — Strictly Unusable (Excluded): built, water (+ 30m buffer), flooded_vegetation, snow, or terrain slope > 5°
red = built.Or(water30).Or(snow).Or(steep)

# --- Contiguous Patch Connected Component Analysis ---
# 10m pixels: 1 px = 100 m2. 1 acre = 4046.86 m2 (~40.47 px). 4 acres = 162 px. 10 acres = 405 px.
green_conn = green.connectedPixelCount(1024, True) # counts up to 1024 px (~25.3 acres)
gy_conn = green.Or(yellow).connectedPixelCount(1024, True)

px_ac = ee.Image.pixelArea().multiply(0.000247105)

# Image with bands to reduce:
# 1. Total acres
# 2. Green acres
# 3. Yellow acres
# 4. Red acres
# 5. Max green connected count (to get largest patch)
# 6. Max green+yellow connected count
img_eval = px_ac.rename('tot_ac').addBands([
    px_ac.updateMask(green).rename('green_ac'),
    px_ac.updateMask(yellow).rename('yellow_ac'),
    px_ac.updateMask(red).rename('red_ac'),
    green_conn.rename('max_green_px'),
    gy_conn.rename('max_gy_px')
])

# 1 km buffer
buf1k = sample.map(lambda f: f.setGeometry(f.geometry().buffer(1000)))

print("Computing 1 km buffer metrics...")
t0 = time.time()
res = img_eval.reduceRegions(
    collection=buf1k,
    reducer=ee.Reducer.sum().combine(ee.Reducer.max(), sharedInputs=True),
    scale=10
).getInfo()
print(f"Computed in {time.time()-t0:.2f}s")

records = []
for f in res['features']:
    p = f['properties']
    name = p['substation_name']
    
    tot_ac = float(p.get('tot_ac_sum') or 776.0)
    green_ac = float(p.get('green_ac_sum') or 0.0)
    yellow_ac = float(p.get('yellow_ac_sum') or 0.0)
    red_ac = float(p.get('red_ac_sum') or 0.0)
    
    red_pct = round((red_ac / tot_ac * 100.0) if tot_ac > 0 else 0.0, 1)
    
    # Largest contiguous patch
    max_green_px = float(p.get('max_green_px_max') or 0.0)
    max_gy_px = float(p.get('max_gy_px_max') or 0.0)
    
    # Convert pixels to acres (1 px at 10m = 100 m2 = 0.0247105 acres)
    largest_green_patch_ac = round(max_green_px * 0.0247105, 2)
    largest_gy_patch_ac = round(max_gy_px * 0.0247105, 2)
    
    meets_4ac = largest_green_patch_ac >= 4.0
    meets_10ac = largest_green_patch_ac >= 10.0
    
    # Estimated MW = largest_green_patch_acres / 4.5
    est_mw = round(largest_green_patch_ac / 4.5, 2)
    
    # Acreage-calibrated Land Suitability Score (0 - 100)
    if meets_10ac:
        # 90 to 100
        score = min(100.0, round(90.0 + min(10.0, (largest_green_patch_ac - 10.0) * 0.5), 1))
    elif meets_4ac:
        # 70 to 89
        score = round(70.0 + ((largest_green_patch_ac - 4.0) / 6.0) * 19.0, 1)
    elif largest_gy_patch_ac >= 4.0:
        # 40 to 69
        score = round(40.0 + min(29.0, (largest_gy_patch_ac / 10.0) * 29.0), 1)
    else:
        # 0 to 39
        score = round(max(0.0, 39.0 * (largest_gy_patch_ac / 4.0) * (1.0 - red_pct / 100.0)), 1)
        
    records.append({
        'substation_id': p.get('record_id') or p.get('Record ID'),
        'substation_name': name,
        'district': p.get('district'),
        'mandal': p.get('mandal'),
        'voltage_level': p.get('voltage_level'),
        'lat': round(float(p['latitude']), 4),
        'lon': round(float(p['longitude']), 4),
        'green_acres_total': round(green_ac, 1),
        'largest_green_patch_acres': largest_green_patch_ac,
        'yellow_acres_total': round(yellow_ac, 1),
        'red_pct': red_pct,
        'meets_4_acre_min': meets_4ac,
        'meets_10_acre_target': meets_10ac,
        'estimated_mw': est_mw,
        'land_suitability_score': score
    })

df = pd.DataFrame(records)
print("\n=== REFINED 1 KM CALIBRATED RESULTS (5 SAMPLE SUBSTATIONS) ===")
print(df[['substation_name', 'green_acres_total', 'largest_green_patch_acres', 'yellow_acres_total', 'red_pct', 'meets_4_acre_min', 'meets_10_acre_target', 'estimated_mw', 'land_suitability_score']].to_string(index=False))
