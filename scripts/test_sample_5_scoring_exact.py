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

# 1. Elevation & Slope
dem = ee.Image('USGS/SRTMGL1_003').clip(boundary)
slope = ee.Terrain.slope(dem)
flat = slope.lte(5) # <= 5 deg (ideal for ground-mounted solar)
mod_slope = slope.gt(5).And(slope.lte(10)) # 5 to 10 deg (minor clearance / light grading)
steep = slope.gt(10) # > 10 deg (strictly excluded)

# 2. Dynamic World V1 Mode (12-month)
dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1') \
    .filterBounds(sample.geometry().buffer(2000)) \
    .filterDate('2023-01-01', '2024-01-01') \
    .select('label')
dw_mode = dw.reduce(ee.Reducer.mode()).rename('dw_label')

water = dw_mode.eq(0).Or(dw_mode.eq(3))
water30 = water.focalMax(30, 'circle', 'meters')

built = dw_mode.eq(6)
snow = dw_mode.eq(8)
trees = dw_mode.eq(1)
crops = dw_mode.eq(4)
# Primary includes bare, scrub, grass, AND crops (open farmland / fallow fields)
primary = dw_mode.eq(7).Or(dw_mode.eq(5)).Or(dw_mode.eq(2)).Or(dw_mode.eq(4))

# OPERATIONAL CLASSIFICATION:
# GREEN: Primary (bare, scrub, grass, crops) + flat (<= 5 deg) + outside water30 + outside built
green = primary.And(flat).And(water30.Not()).And(built.Not())

# YELLOW: Strictly reserved for minor clearance / grading:
# - Trees with slope <= 10 deg (outside water30 & built)
# - Moderate slope (5°–10°) on non-built, non-water land
yellow_trees = trees.And(slope.lte(10)).And(water30.Not()).And(built.Not())
yellow_slope = mod_slope.And(water30.Not()).And(built.Not()).And(snow.Not())
yellow = (yellow_trees.Or(yellow_slope)).And(green.Not())

# RED: Strictly excluded (built, water30, snow, steep > 10 deg)
red = built.Or(water30).Or(snow).Or(steep)

# 4-acre and 10-acre contiguous patch filters
# 25m radius opening filters noise and keeps patches >= 4 acres
green_4ac = green.focalMin(25, 'circle', 'meters').focalMax(25, 'circle', 'meters')
green_10ac = green.focalMin(45, 'circle', 'meters').focalMax(45, 'circle', 'meters')

# Fallback: Green + Yellow contiguous patches
gy = green.Or(yellow)
gy_4ac = gy.focalMin(25, 'circle', 'meters').focalMax(25, 'circle', 'meters')

px_ac = ee.Image.pixelArea().multiply(0.000247105)

img_bands = px_ac.rename('tot_ac').addBands([
    px_ac.updateMask(green).rename('green_ac'),
    px_ac.updateMask(green_4ac).rename('green_4ac_ac'),
    px_ac.updateMask(green_10ac).rename('green_10ac_ac'),
    px_ac.updateMask(yellow).rename('yellow_ac'),
    px_ac.updateMask(gy_4ac).rename('gy_4ac_ac'),
    px_ac.updateMask(red).rename('red_ac')
])

buf1k = sample.map(lambda f: f.setGeometry(f.geometry().buffer(1000)))

t0 = time.time()
res = img_bands.reduceRegions(collection=buf1k, reducer=ee.Reducer.sum(), scale=10).getInfo()
print(f"5 substations 1km reduced in {time.time()-t0:.2f}s")

records = []
for f in res['features']:
    p = f['properties']
    name = p['substation_name']
    
    tot_ac = float(p.get('tot_ac') or 776.0)
    green_ac = float(p.get('green_ac') or 0.0)
    green_4ac_val = float(p.get('green_4ac_ac') or 0.0)
    green_10ac_val = float(p.get('green_10ac_ac') or 0.0)
    yellow_ac = float(p.get('yellow_ac') or 0.0)
    gy_4ac_val = float(p.get('gy_4ac_ac') or 0.0)
    red_ac = float(p.get('red_ac') or 0.0)
    
    red_pct = round((red_ac / tot_ac * 100.0) if tot_ac > 0 else 0.0, 1)
    
    # Largest contiguous patch estimation:
    # If 10-acre filter survives, largest patch >= 10 acres.
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
    
    # Scoring calibration:
    # • >= 10 contiguous GREEN acres -> 90–100 (High)
    # • 4 to < 10 contiguous GREEN acres -> 70–89 (Viable)
    # • < 4 GREEN acres, but >= 4 contiguous GREEN + YELLOW acres -> 40–69 (Conditional)
    # • < 4 contiguous usable acres total -> 0–39 (Low / Constrained)
    if meets_10ac:
        score = min(100.0, round(90.0 + min(10.0, (largest_green_patch_ac - 10.0) * 0.2), 1))
        tier = 'HIGH (>=10ac Green Ready)'
    elif meets_4ac:
        score = round(70.0 + ((largest_green_patch_ac - 4.0) / 6.0) * 19.0, 1)
        tier = 'VIABLE (4-10ac Green Ready)'
    elif gy_4ac_val >= 4.0:
        score = round(40.0 + min(29.0, (largest_gy_patch_ac / 20.0) * 29.0), 1)
        tier = 'CONDITIONAL (>=4ac with Agri/Trees)'
    else:
        score = round(max(0.0, 39.0 * (1.0 - red_pct / 100.0)), 1)
        tier = 'LOW / CONSTRAINED'
        
    est_mw = round(largest_green_patch_ac / 4.5, 2)
    
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
        'land_suitability_score': score,
        'viability_tier': tier
    })

df = pd.DataFrame(records)
print("\n=== SAMPLE 5 SUBSTATIONS VALIDATION RESULTS ===")
print(df[['substation_name', 'green_acres_total', 'largest_green_patch_acres', 'yellow_acres_total', 'red_pct', 'meets_4_acre_min', 'meets_10_acre_target', 'estimated_mw', 'land_suitability_score', 'viability_tier']].to_string(index=False))
