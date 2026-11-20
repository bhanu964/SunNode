#!/usr/bin/env python3
"""
webapp/build_webapp_data.py
Pre-bundles Stage 4.5 & 5.6 data into clean, lightweight JSON assets inside webapp/data/:
1. substations.json (all 391 substations with 4 layers + coordinates + real PVGIS solar telemetry)
2. top20_eht.json (Top 20 Utility EHT substations)
3. top20_kusum.json (Top 20 PM-KUSUM substations)
4. top20_golden.json (Top 20 Overall Golden substations)
5. districts_simplified.geojson (Simplified 33-district polygons with aggregated solar stats)
6. statewide_metrics.json (Statewide totals, impacts, and PVGIS solar benchmarks)
"""

import os
import json
import pandas as pd
import geopandas as gpd

print("Starting SunNode WebApp Data Bundler (Stage 5.6 Real PVGIS Solar Upgrade)...")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "webapp", "data")
os.makedirs(OUT_DIR, exist_ok=True)

# 1. Load Master Techno-Economic CSV
master_csv = os.path.join(BASE_DIR, "data", "processed", "suryagrid_master_391_techno_economic.csv")
df_master = pd.read_csv(master_csv)
print(f"Loaded {len(df_master)} substations from {master_csv}")

# Compute exact solar percentile across all 391 substations (100% real PVGIS v5.3 data)
df_master['solar_pctile'] = df_master['pvgis_hi_d_kwh_m2'].rank(pct=True) * 100.0

# Standardize fields for JSON
substations = []
for idx, r in df_master.iterrows():
    volt = str(r['voltage_level'])
    is_eht = ('220' in volt) or ('400' in volt)
    track = 'EHT' if is_eht else 'KUSUM'

    pct = round(float(r['solar_pctile']), 1)
    if pct >= 66.6:
        solar_grade = "Excellent Solar Zone"
    elif pct >= 33.3:
        solar_grade = "High Solar Zone"
    else:
        solar_grade = "Good Solar Zone"

    dep_mw = round(float(r['deployable_solar_mw']), 1)
    if dep_mw > 0:
        suitability_verdict = f"SUITABLE ({dep_mw:.1f} MW Ready)"
        suitability_status = "SUITABLE"
    else:
        suitability_verdict = "NOT SUITABLE (Urban / 0 MW Land)"
        suitability_status = "NOT_SUITABLE"

    annual_mu = round(float(r['deployable_annual_mu']), 2)
    lifetime_25yr_mu = round(annual_mu * 25 * 0.91, 2)

    monthly_kwh = [
        round(float(r.get('pvgis_jan_kwh', 0))),
        round(float(r.get('pvgis_feb_kwh', 0))),
        round(float(r.get('pvgis_mar_kwh', 0))),
        round(float(r.get('pvgis_apr_kwh', 0))),
        round(float(r.get('pvgis_may_kwh', 0))),
        round(float(r.get('pvgis_jun_kwh', 0))),
        round(float(r.get('pvgis_jul_kwh', 0))),
        round(float(r.get('pvgis_aug_kwh', 0))),
        round(float(r.get('pvgis_sep_kwh', 0))),
        round(float(r.get('pvgis_oct_kwh', 0))),
        round(float(r.get('pvgis_nov_kwh', 0))),
        round(float(r.get('pvgis_dec_kwh', 0)))
    ]

    substations.append({
        "id": str(r.get('substation_id', f"ss-{idx+1}")),
        "name": str(r['substation_name']),
        "district": str(r['district']),
        "mandal": str(r.get('mandal', 'Telangana')),
        "voltageClass": volt,
        "track": track,
        "lat": round(float(r['lat']), 5),
        "lon": round(float(r['lon']), 5),
        "landMw": round(float(r['land_solar_mw']), 1),
        "gridMw": round(float(r['grid_spare_mw']), 1),
        "deployMw": dep_mw,
        "evacKv": int(r['evacuation_voltage_kv']),
        "amps": round(float(r['deployable_current_amps']), 1),
        "bays": int(r['required_feeder_bays']),
        "bayType": str(r['feeder_bay_type']),
        "tariff": round(float(r['tariff_inr_per_kwh']), 2),
        "tariffTier": str(r['tariff_tier']),
        "energyMu": annual_mu,
        "capexCr": round(float(r['turnkey_capex_cr']), 2),
        "grossRevCr": round(float(r['annual_gross_revenue_cr']), 2),
        "netEbitdaCr": round(float(r['annual_net_ebitda_cr']), 2),
        "payback": round(float(r['simple_payback_years']), 2),
        "profit25Cr": round(float(r['lifetime_25yr_net_profit_cr']), 2),
        "score": round(float(r['suryagrid_master_score']), 1),
        "rank": int(r.get('master_rank', idx + 1)),
        "bottleneck": str(r['active_bottleneck']),
        "isColocated": bool(r['is_colocated_overlap']),
        "overlapFactor": round(float(r['overlap_factor']), 4),
        "greenAcres": round(float(r.get('largest_green_patch_acres', 0)), 1),
        "redPct": round(float(r.get('red_pct', 0)), 1),
        
        # Real PVGIS v5.3 Solar Telemetry
        "irradianceDailyKwhM2": round(float(r['pvgis_hi_d_kwh_m2']), 2),
        "irradianceAnnualKwhM2": round(float(r['pvgis_hi_y_kwh_m2']), 1),
        "specificYieldKwhKwp": round(float(r['pvgis_ey_kwh_per_mwp']) / 1000.0, 1),
        "specificYieldMuMw": round(float(r['pvgis_ey_kwh_per_mwp']) / 1000000.0, 3),
        "cufPct": round(float(r['pvgis_dc_cuf_pct']), 2),
        "optimalTiltDeg": round(float(r['pvgis_optimal_tilt_deg']), 1),
        "dailyOutputMwh": round(float(r['deployable_daily_mwh']), 1),
        "annualOutputMu": annual_mu,
        "lifetime25YrMu": lifetime_25yr_mu,
        "monthlyGenerationKwh": monthly_kwh,
        "solarPercentile": pct,
        "solarGrade": solar_grade,
        "siteSuitability": suitability_verdict,
        "suitabilityStatus": suitability_status
    })

sub_path = os.path.join(OUT_DIR, "substations.json")
with open(sub_path, "w", encoding="utf-8") as f:
    json.dump(substations, f, indent=2)
print(f"✅ Created {sub_path} ({len(substations)} items, {os.path.getsize(sub_path)/1024:.1f} KB)")

# 2. Leaderboards
for lb_name, src_file, out_file in [
    ("top20_eht", "suryagrid_top20_utility_eht_substations.csv", "top20_eht.json"),
    ("top20_kusum", "suryagrid_top20_pm_kusum_substations.csv", "top20_kusum.json"),
    ("top20_golden", "suryagrid_top20_golden_substations.csv", "top20_golden.json"),
]:
    p = os.path.join(BASE_DIR, "data", "processed", src_file)
    if os.path.exists(p):
        df_lb = pd.read_csv(p)
        lb_list = []
        for idx, r in df_lb.iterrows():
            dep_mw = round(float(r['deployable_solar_mw']), 1)
            lb_list.append({
                "id": str(r.get('substation_id', f"lb-{idx+1}")),
                "name": str(r['substation_name']),
                "district": str(r['district']),
                "voltageClass": str(r['voltage_level']),
                "track": 'EHT' if ('220' in str(r['voltage_level']) or '400' in str(r['voltage_level'])) else 'KUSUM',
                "landMw": round(float(r['land_solar_mw']), 1),
                "gridMw": round(float(r['grid_spare_mw']), 1),
                "deployMw": dep_mw,
                "evacKv": int(r['evacuation_voltage_kv']),
                "amps": round(float(r['deployable_current_amps']), 1),
                "bays": int(r['required_feeder_bays']),
                "bayType": str(r['feeder_bay_type']),
                "tariff": round(float(r['tariff_inr_per_kwh']), 2),
                "tariffTier": str(r['tariff_tier']),
                "energyMu": round(float(r['deployable_annual_mu']), 2),
                "capexCr": round(float(r['turnkey_capex_cr']), 2),
                "grossRevCr": round(float(r['annual_gross_revenue_cr']), 2),
                "payback": round(float(r['simple_payback_years']), 2),
                "score": round(float(r['suryagrid_master_score']), 1),
                "rank": int(r.get('master_rank', idx + 1)),
                "bottleneck": str(r['active_bottleneck']),
                "isColocated": bool(r['is_colocated_overlap']),
                "irradianceDailyKwhM2": round(float(r['pvgis_hi_d_kwh_m2']), 2),
                "specificYieldMuMw": round(float(r['pvgis_ey_kwh_per_mwp']) / 1000000.0, 3),
                "cufPct": round(float(r['pvgis_dc_cuf_pct']), 2),
                "suitabilityStatus": "SUITABLE" if dep_mw > 0 else "NOT_SUITABLE"
            })
        out_p = os.path.join(OUT_DIR, out_file)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(lb_list, f, indent=2)
        print(f"✅ Created {out_p} ({len(lb_list)} items)")

# 3. Simplify Districts GeoJSON and attach District Solar Stats
dist_file = os.path.join(BASE_DIR, "data", "boundaries", "telangana_33_districts.geojson")
gdf_dist = gpd.read_file(dist_file)

# Pre-calculate district-level solar stats from df_master
dist_stats = {}
for dist_name, g in df_master.groupby('district'):
    sub_cnt = len(g)
    dep_mw = round(float((g['deployable_solar_mw'] * g['overlap_factor']).sum()), 1)
    lnd_mw = round(float((g['land_solar_mw'] * g['overlap_factor']).sum()), 1)
    
    kusum_g = g[g['tariff_tier'].str.contains('PM-KUSUM', case=False, na=False)]
    eht_g = g[g['tariff_tier'].str.contains('Utility', case=False, na=False)]
    
    kusum_mw = round(float((kusum_g['deployable_solar_mw'] * kusum_g['overlap_factor']).sum()), 1)
    eht_mw = round(float((eht_g['deployable_solar_mw'] * eht_g['overlap_factor']).sum()), 1)
    
    # Real PVGIS District Aggregations
    avg_irrad_daily = round(float(g['pvgis_hi_d_kwh_m2'].mean()), 2)
    avg_yield_mu = round(float((g['pvgis_ey_kwh_per_mwp'] / 1e6).mean()), 3)
    total_clean_mu = round(float((g['deployable_annual_mu'] * g['overlap_factor']).sum()), 1)
    avg_cuf = round(float(g['pvgis_dc_cuf_pct'].mean()), 2)

    top_ss = g.sort_values(by='suryagrid_master_score', ascending=False).iloc[0]
    
    dist_stats[dist_name.lower().strip()] = {
        "district": dist_name,
        "substation_count": sub_cnt,
        "deployable_mw": dep_mw,
        "land_mw": lnd_mw,
        "pm_kusum_mw": kusum_mw,
        "utility_eht_mw": eht_mw,
        "avg_solar_irradiance_daily": avg_irrad_daily,
        "avg_solar_yield_mu_per_mw": avg_yield_mu,
        "total_annual_clean_mu": total_clean_mu,
        "district_cuf_pct": avg_cuf,
        "top_substation": str(top_ss['substation_name']),
        "top_score": round(float(top_ss['suryagrid_master_score']), 1)
    }

# Simplify geometries
gdf_dist_simple = gdf_dist.copy()
gdf_dist_simple['geometry'] = gdf_dist.geometry.simplify(0.003, preserve_topology=True)

# Update properties
features = []
for idx, r in gdf_dist_simple.iterrows():
    d_name = r.get('dtname') or r.get('district_name') or r.get('NAME') or f"District {idx}"
    d_key = d_name.lower().strip()
    st = dist_stats.get(d_key, {
        "district": d_name,
        "substation_count": 0,
        "deployable_mw": 0.0,
        "land_mw": 0.0,
        "pm_kusum_mw": 0.0,
        "utility_eht_mw": 0.0,
        "avg_solar_irradiance_daily": 5.51,
        "avg_solar_yield_mu_per_mw": 1.491,
        "total_annual_clean_mu": 0.0,
        "district_cuf_pct": 17.02,
        "top_substation": "None",
        "top_score": 0.0
    })
    
    props = {
        "district_name": d_name,
        "substation_count": st["substation_count"],
        "deployable_mw": st["deployable_mw"],
        "land_mw": st["land_mw"],
        "pm_kusum_mw": st["pm_kusum_mw"],
        "utility_eht_mw": st["utility_eht_mw"],
        "avg_solar_irradiance_daily": st["avg_solar_irradiance_daily"],
        "avg_solar_yield_mu_per_mw": st["avg_solar_yield_mu_per_mw"],
        "total_annual_clean_mu": st["total_annual_clean_mu"],
        "district_cuf_pct": st["district_cuf_pct"],
        "top_substation": st["top_substation"],
        "top_score": st["top_score"]
    }
    
    geom = json.loads(gpd.GeoSeries([r.geometry]).to_json())['features'][0]['geometry']
    features.append({
        "type": "Feature",
        "properties": props,
        "geometry": geom
    })

geojson_obj = {
    "type": "FeatureCollection",
    "features": features
}

dist_out_path = os.path.join(OUT_DIR, "districts_simplified.geojson")
with open(dist_out_path, "w", encoding="utf-8") as f:
    json.dump(geojson_obj, f)
print(f"✅ Created {dist_out_path} ({len(features)} districts, {os.path.getsize(dist_out_path)/1024:.1f} KB)")

# 4. Statewide Metrics
raw_land = float(df_master['land_solar_mw'].sum())
dedup_land = float((df_master['land_solar_mw'] * df_master['overlap_factor']).sum())

raw_deploy = float(df_master['deployable_solar_mw'].sum())
dedup_deploy = float((df_master['deployable_solar_mw'] * df_master['overlap_factor']).sum())

total_capex = float((df_master['turnkey_capex_cr'] * df_master['overlap_factor']).sum())
total_rev = float((df_master['annual_gross_revenue_cr'] * df_master['overlap_factor']).sum())
total_ebitda = float((df_master['annual_net_ebitda_cr'] * df_master['overlap_factor']).sum())
total_profit25 = float((df_master['lifetime_25yr_net_profit_cr'] * df_master['overlap_factor']).sum())
statewide_payback = round(total_capex / total_ebitda, 2) if total_ebitda > 0 else 10.13

# Real PVGIS Statewide Solar Metrics
solar_irrad_min = round(float(df_master['pvgis_hi_d_kwh_m2'].min()), 2)
solar_irrad_mean = round(float(df_master['pvgis_hi_d_kwh_m2'].mean()), 2)
solar_irrad_max = round(float(df_master['pvgis_hi_d_kwh_m2'].max()), 2)

solar_yield_min = round(float(df_master['pvgis_ey_kwh_per_mwp'].min() / 1000.0), 1)
solar_yield_mean = round(float(df_master['pvgis_ey_kwh_per_mwp'].mean() / 1000.0), 1)
solar_yield_max = round(float(df_master['pvgis_ey_kwh_per_mwp'].max() / 1000.0), 1)

statewide_metrics = {
    "total_substations": len(df_master),
    "total_districts": len(dist_stats),
    "raw_land_mw": round(raw_land, 1),
    "dedup_land_mw": round(dedup_land, 1),
    "raw_deploy_mw": round(raw_deploy, 1),
    "dedup_deploy_mw": round(dedup_deploy, 1),
    "statewide_turnkey_capex_cr": round(total_capex, 1),
    "statewide_annual_revenue_cr": round(total_rev, 1),
    "statewide_annual_ebitda_cr": round(total_ebitda, 1),
    "statewide_payback_years": statewide_payback,
    "statewide_25yr_profit_cr": round(total_profit25, 1),
    "colocated_substations_count": int(df_master['is_colocated_overlap'].sum()),
    
    # Real PVGIS v5.3 Benchmarks
    "solar_irradiance_min_kwh_m2_day": solar_irrad_min,
    "solar_irradiance_mean_kwh_m2_day": solar_irrad_mean,
    "solar_irradiance_max_kwh_m2_day": solar_irrad_max,
    "specific_yield_min_kwh_kwp": solar_yield_min,
    "specific_yield_mean_kwh_kwp": solar_yield_mean,
    "specific_yield_max_kwh_kwp": solar_yield_max,
    "cuf_mean_pct": round(float(df_master['pvgis_dc_cuf_pct'].mean()), 2),
    "optimal_tilt_mean_deg": round(float(df_master['pvgis_optimal_tilt_deg'].mean()), 1),

    "socio_economic_impact": {
        "annual_farmer_lease_income_cr": 252.05,
        "annual_clean_generation_mu": 18771.6,
        "annual_co2_offset_tonnes": 13646954,
        "avoided_stranded_capex_cr": 62864.0
    }
}

metrics_path = os.path.join(OUT_DIR, "statewide_metrics.json")
with open(metrics_path, "w", encoding="utf-8") as f:
    json.dump(statewide_metrics, f, indent=2)
print(f"✅ Created {metrics_path}")

print("✨ Stage 5.6 Data Bundling Complete!")
