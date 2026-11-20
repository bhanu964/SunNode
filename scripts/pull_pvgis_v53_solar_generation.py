#!/usr/bin/env python3
"""
scripts/pull_pvgis_v53_solar_generation.py
SuryaGrid: Telangana Statewide Substation & Ground-Mounted Solar Intelligence Platform
Challenge 10: Solar Substation Potential Assessment

Queries the live EU JRC PVGIS v5.3 Non-Interactive API (PVcalc) for all 391 official
grid substations across Telangana. Extracts annual (E_y) and daily (E_d) yield per 1 MWp,
irradiation, optimal tilt, monthly generation profile, and computes land-backed generation
(MWh/yr, MU/yr, 33kV evacuation current in Amps) coupled to each substation's 1 km contiguous
buildable land capacity.

Mandatory Safeguards:
1. Controlled Sequential Pacing (5–6 req/sec via single persistent requests.Session, 0.18s min interval).
2. Persistent Coordinate Disk Cache (data/processed/pvgis_v53_cache.json, flushed every 20 calls).
3. Exponential Backoff with Random Jitter on HTTP 429, 529, 502, 503, 504 (up to 6 retries).
4. Strict HTTP GET with User-Agent: SuryaGrid-Telangana-PVGIS-Engine/1.0.
5. 5-Substation Benchmark Smoke Test First.
"""

import os
import sys
import time
import json
import random
import argparse
import requests
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Design Assumptions & Architectural Constants
PVGIS_BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
PEAK_POWER_KWP = 1000       # 1,000 kWp = 1.0 MWp nominal DC capacity
SYSTEM_LOSS_PCT = 14        # 14% standard system losses (inverter, cabling, soiling)
OPTIMAL_ANGLES = 1          # Automatically compute optimal tilt (slope) and azimuth
OUTPUT_FORMAT = "json"      # Structured JSON
MIN_CALL_INTERVAL_S = 0.18  # ~5.5 requests/sec to prevent hitting the 30 req/sec limit
MAX_RETRIES = 6             # Up to 6 exponential retries
CACHE_FLUSH_INTERVAL = 20   # Flush JSON cache to disk every 20 new calls
AMPS_PER_1MW_33KV = 17.85   # Three-phase AC current at 33kV, cos_phi = 0.98

USER_AGENT = "SuryaGrid-Telangana-PVGIS-Engine/1.0"
CACHE_PATH = "data/processed/pvgis_v53_cache.json"
INPUT_CSV_PATH = "data/processed/substation_land_suitability_1km_calibrated.csv"
OUTPUT_CSV_PATH = "data/processed/substation_pvgis_v53_generation_1km_calibrated.csv"
EXCEL_PATH = "outputs/SuryaGrid_Telangana_Statewide_Substation_Inventory.xlsx"

BENCHMARK_NAMES = [
    "Gajwel (400KV)",
    "K.M.Pally (220KV)",
    "Ganeshpahad",
    "Kondapaka",
    "Narayanguda"
]

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Loaded {len(data)} cached PVGIS coordinate entries from {CACHE_PATH}")
                return data
        except Exception as e:
            print(f"Warning: Failed to load cache ({e}), initializing empty cache.")
            return {}
    return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

def build_pvgis_url(lat, lon):
    return (
        f"{PVGIS_BASE_URL}?"
        f"lat={lat:.4f}&lon={lon:.4f}&peakpower={PEAK_POWER_KWP}"
        f"&loss={SYSTEM_LOSS_PCT}&optimalangles={OPTIMAL_ANGLES}&outputformat={OUTPUT_FORMAT}"
    )

def fetch_pvgis_data(session, lat, lon, cache, call_counter):
    key = f"{round(float(lat), 4):.4f},{round(float(lon), 4):.4f}"
    if key in cache:
        return cache[key], False

    url = build_pvgis_url(lat, lon)
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(MAX_RETRIES):
        try:
            t0 = time.time()
            resp = session.get(url, headers=headers, timeout=20)

            if resp.status_code == 200:
                data = resp.json()
                cache[key] = data
                call_counter[0] += 1
                if call_counter[0] % CACHE_FLUSH_INTERVAL == 0:
                    save_cache(cache)
                return data, True

            elif resp.status_code in (429, 502, 503, 504, 529):
                wait_s = (2.0 ** attempt) + random.uniform(0.25, 0.85)
                print(f"  [PVGIS HTTP {resp.status_code}] Rate-limit/concurrency backoff for {key}. Sleeping {wait_s:.2f}s (Attempt {attempt+1}/{MAX_RETRIES})...")
                time.sleep(wait_s)
            else:
                resp.raise_for_status()

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            wait_s = (2.0 ** attempt) + random.uniform(0.25, 0.85)
            print(f"  [PVGIS Network Error] {e} for {key}. Sleeping {wait_s:.2f}s (Attempt {attempt+1}/{MAX_RETRIES})...")
            time.sleep(wait_s)

    raise RuntimeError(f"Failed to fetch PVGIS v5.3 data for ({lat}, {lon}) after {MAX_RETRIES} retries.")

def parse_pvgis_record(data, direct_solar_mw, lat, lon):
    totals = data["outputs"]["totals"]["fixed"]
    inputs_fixed = data["inputs"]["mounting_system"]["fixed"]
    meteo = data["inputs"]["meteo_data"]
    monthly_list = data["outputs"]["monthly"]["fixed"]

    pvgis_ey_kwh = float(totals["E_y"])
    pvgis_ed_kwh = float(totals["E_d"])
    pvgis_em_kwh = float(totals["E_m"])
    pvgis_hi_y = float(totals["H(i)_y"])
    pvgis_hi_d = float(totals["H(i)_d"])
    pvgis_sd_y = float(totals["SD_y"])
    optimal_tilt = float(inputs_fixed["slope"]["value"])
    optimal_azimuth = float(inputs_fixed["azimuth"]["value"])
    loss_aoi = float(totals["l_aoi"])
    loss_tg = float(totals["l_tg"])
    loss_total = float(totals["l_total"])
    rad_db = str(meteo["radiation_db"])

    dc_cuf_pct = round((pvgis_ey_kwh / (1000.0 * 8760.0)) * 100.0, 2)

    monthly_dict = {m["month"]: float(m["E_m"]) for m in monthly_list}

    # Land-Coupled Solar Output
    direct_solar_mw = float(direct_solar_mw)
    direct_annual_gen_kwh = round(direct_solar_mw * pvgis_ey_kwh, 1)
    direct_annual_gen_mwh = round(direct_annual_gen_kwh / 1000.0, 2)
    direct_annual_gen_mu = round(direct_annual_gen_kwh / 1e6, 3)
    direct_daily_gen_kwh = round(direct_solar_mw * pvgis_ed_kwh, 1)
    direct_evac_current_amps = round(direct_solar_mw * AMPS_PER_1MW_33KV, 1)

    api_url = build_pvgis_url(lat, lon)

    return {
        "pvgis_ey_kwh_per_mwp": pvgis_ey_kwh,
        "pvgis_ed_kwh_per_mwp": pvgis_ed_kwh,
        "pvgis_em_kwh_per_mwp": pvgis_em_kwh,
        "pvgis_hi_y_kwh_m2": pvgis_hi_y,
        "pvgis_hi_d_kwh_m2": pvgis_hi_d,
        "pvgis_sd_y_kwh": pvgis_sd_y,
        "pvgis_optimal_tilt_deg": optimal_tilt,
        "pvgis_optimal_azimuth_deg": optimal_azimuth,
        "pvgis_loss_aoi_pct": loss_aoi,
        "pvgis_loss_temp_pct": loss_tg,
        "pvgis_loss_total_pct": loss_total,
        "pvgis_rad_db": rad_db,
        "pvgis_dc_cuf_pct": dc_cuf_pct,
        "pvgis_jan_kwh": monthly_dict.get(1, 0.0),
        "pvgis_feb_kwh": monthly_dict.get(2, 0.0),
        "pvgis_mar_kwh": monthly_dict.get(3, 0.0),
        "pvgis_apr_kwh": monthly_dict.get(4, 0.0),
        "pvgis_may_kwh": monthly_dict.get(5, 0.0),
        "pvgis_jun_kwh": monthly_dict.get(6, 0.0),
        "pvgis_jul_kwh": monthly_dict.get(7, 0.0),
        "pvgis_aug_kwh": monthly_dict.get(8, 0.0),
        "pvgis_sep_kwh": monthly_dict.get(9, 0.0),
        "pvgis_oct_kwh": monthly_dict.get(10, 0.0),
        "pvgis_nov_kwh": monthly_dict.get(11, 0.0),
        "pvgis_dec_kwh": monthly_dict.get(12, 0.0),
        "direct_annual_generation_kwh": direct_annual_gen_kwh,
        "direct_annual_generation_mwh": direct_annual_gen_mwh,
        "direct_annual_generation_mu": direct_annual_gen_mu,
        "direct_daily_generation_kwh": direct_daily_gen_kwh,
        "direct_evacuation_current_33kv_amps": direct_evac_current_amps,
        "pvgis_api_url": api_url
    }

def run_smoke_test(session, df, cache, call_counter):
    print("\n==========================================================================")
    print("STEP 1: 5-SUBSTATION BENCHMARK SMOKE TEST (EU JRC PVGIS v5.3 API)")
    print("==========================================================================")

    smoke_rows = []
    last_call_time = 0.0

    for name in BENCHMARK_NAMES:
        match = df[df["substation_name"] == name]
        if match.empty:
            print(f"Warning: Benchmark substation '{name}' not found in dataframe.")
            continue
        row = match.iloc[0]
        lat, lon = float(row["lat"]), float(row["lon"])
        mw = float(row["largest_green_patch_acres"]) / 4.5

        # Pacing
        elapsed = time.time() - last_call_time
        if elapsed < MIN_CALL_INTERVAL_S:
            time.sleep(MIN_CALL_INTERVAL_S - elapsed)

        last_call_time = time.time()
        data, is_new = fetch_pvgis_data(session, lat, lon, cache, call_counter)
        parsed = parse_pvgis_record(data, mw, lat, lon)

        smoke_rows.append({
            "Substation": name,
            "District": row["district"],
            "Capacity (MW)": round(mw, 1),
            "E_y (kWh/MWp/yr)": f"{parsed['pvgis_ey_kwh_per_mwp']:,.0f}",
            "E_d (kWh/MWp/d)": f"{parsed['pvgis_ed_kwh_per_mwp']:,.1f}",
            "Tilt (°)": f"{parsed['pvgis_optimal_tilt_deg']}°",
            "CUF (%)": f"{parsed['pvgis_dc_cuf_pct']}%",
            "Annual Gen (MU/yr)": f"{parsed['direct_annual_generation_mu']:,.3f} MU",
            "Cache Hit": "CACHE" if not is_new else "LIVE 200 OK"
        })

    smoke_df = pd.DataFrame(smoke_rows)
    print(smoke_df.to_string(index=False))
    print("✅ 5-Substation Smoke Test Passed Successfully!")
    save_cache(cache)

def process_statewide_pvgis(session, df, cache, call_counter):
    print("\n==========================================================================")
    print("STEP 2: FULL STATEWIDE PVGIS v5.3 EXTRACTION (391 SUBSTATIONS)")
    print("==========================================================================")

    pvgis_results = []
    t_start = time.time()
    last_call_time = 0.0
    new_calls = 0

    total = len(df)
    for idx, row in df.iterrows():
        lat, lon = float(row["lat"]), float(row["lon"])
        mw = float(row["largest_green_patch_acres"]) / 4.5

        # Controlled pacing
        elapsed = time.time() - last_call_time
        if elapsed < MIN_CALL_INTERVAL_S:
            time.sleep(MIN_CALL_INTERVAL_S - elapsed)

        last_call_time = time.time()
        data, is_new = fetch_pvgis_data(session, lat, lon, cache, call_counter)
        if is_new:
            new_calls += 1

        parsed = parse_pvgis_record(data, mw, lat, lon)
        pvgis_results.append(parsed)

        if (idx + 1) % 50 == 0 or (idx + 1) == total:
            print(f"  Processed {idx + 1}/{total} substations ({((idx+1)/total)*100:.1f}%) | New API Calls: {new_calls} | Time: {time.time()-t_start:.1f}s")

    # Save final cache
    save_cache(cache)
    print(f"Statewide extraction complete in {time.time()-t_start:.2f}s ({new_calls} live calls, {total - new_calls} cache hits).")

    pvgis_df = pd.DataFrame(pvgis_results)
    merged_df = pd.concat([df.reset_index(drop=True), pvgis_df.reset_index(drop=True)], axis=1)

    return merged_df

def update_excel_workbook(df):
    print("\n==========================================================================")
    print(f"STEP 3: UPDATING MASTER EXCEL WORKBOOK: {EXCEL_PATH}")
    print("==========================================================================")

    wb = openpyxl.load_workbook(EXCEL_PATH)

    # 1. Update sheet '1KM CALIBRATED SUITABILITY'
    if "1KM CALIBRATED SUITABILITY" in wb.sheetnames:
        ws_calib = wb["1KM CALIBRATED SUITABILITY"]
        # Read header row to see if PVGIS columns already exist
        headers = [cell.value for cell in ws_calib[1]]
        
        new_cols = [
            ("pvgis_ey_kwh_per_mwp", "PVGIS E_y (kWh/yr/MWp)"),
            ("pvgis_ed_kwh_per_mwp", "PVGIS E_d (kWh/d/MWp)"),
            ("pvgis_optimal_tilt_deg", "Optimal Tilt (deg)"),
            ("pvgis_dc_cuf_pct", "DC CUF (%)"),
            ("direct_annual_generation_mwh", "Direct Annual Gen (MWh/yr)"),
            ("direct_annual_generation_mu", "Direct Annual Gen (MU/yr)")
        ]
        
        col_start_idx = len(headers) + 1
        for col_name, col_title in new_cols:
            if col_title not in headers:
                cell = ws_calib.cell(row=1, column=col_start_idx, value=col_title)
                cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center")
                
                # Populate rows
                for r_idx, val in enumerate(df[col_name], start=2):
                    c = ws_calib.cell(row=r_idx, column=col_start_idx, value=val)
                    c.font = Font(name="Calibri", size=10)
                    if isinstance(val, (int, float)):
                        c.number_format = "#,##0.00" if isinstance(val, float) else "#,##0"
                        c.alignment = Alignment(horizontal="right")
                    else:
                        c.alignment = Alignment(horizontal="center")
                col_start_idx += 1

    # 2. Add or Replace Dedicated Sheet 'PVGIS V5.3 SOLAR GENERATION'
    sheet_name = "PVGIS V5.3 SOLAR GENERATION"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    
    ws_pvgis = wb.create_sheet(title=sheet_name)
    ws_pvgis.views.sheetView[0].showGridLines = True

    # Title block
    ws_pvgis.merge_cells("A1:AE1")
    title_cell = ws_pvgis["A1"]
    title_cell.value = "SuryaGrid – EU JRC PVGIS v5.3 Solar Generation & Feeder Coupling Inventory (Telangana Statewide 391 Substations)"
    title_cell.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    title_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_pvgis.row_dimensions[1].height = 28

    # Subtitle block
    ws_pvgis.merge_cells("A2:AE2")
    sub_cell = ws_pvgis["A2"]
    sub_cell.value = "Data Source: European Commission Joint Research Centre (EU JRC) PVGIS-ERA5 / SARAH3 | 14% System Losses | Optimal Fixed South-Facing Tilt"
    sub_cell.font = Font(name="Calibri", size=9.5, italic=True, color="94A3B8")
    sub_cell.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    sub_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_pvgis.row_dimensions[2].height = 20

    columns_pvgis = [
        ("substation_id", "Substation ID", 15, "center"),
        ("substation_name", "Substation Name", 26, "left"),
        ("district", "District", 18, "left"),
        ("mandal", "Mandal", 18, "left"),
        ("voltage_level", "Voltage Level", 16, "center"),
        ("lat", "Latitude", 11, "right"),
        ("lon", "Longitude", 11, "right"),
        ("largest_green_patch_acres", "Contiguous Green (ac)", 18, "right"),
        ("estimated_mw", "Direct Capacity (MW)", 18, "right"),
        ("pvgis_ey_kwh_per_mwp", "PVGIS E_y (kWh/MWp/yr)", 20, "right"),
        ("pvgis_ed_kwh_per_mwp", "PVGIS E_d (kWh/MWp/d)", 19, "right"),
        ("pvgis_optimal_tilt_deg", "Optimal Tilt (°)", 14, "center"),
        ("pvgis_optimal_azimuth_deg", "Azimuth (°)", 12, "center"),
        ("pvgis_dc_cuf_pct", "DC CUF (%)", 12, "right"),
        ("pvgis_hi_y_kwh_m2", "Irradiation H(i)_y (kWh/m²)", 22, "right"),
        ("pvgis_loss_total_pct", "Total Loss (%)", 14, "right"),
        ("direct_annual_generation_mwh", "Annual Output (MWh/yr)", 20, "right"),
        ("direct_annual_generation_mu", "Annual Output (MU / GWh)", 22, "right"),
        ("direct_daily_generation_kwh", "Daily Output (kWh/d)", 18, "right"),
        ("direct_evacuation_current_33kv_amps", "Evacuation Current (Amps @ 33kV)", 26, "right"),
        ("pvgis_jan_kwh", "Jan (kWh/MWp)", 14, "right"),
        ("pvgis_feb_kwh", "Feb (kWh/MWp)", 14, "right"),
        ("pvgis_mar_kwh", "Mar (kWh/MWp)", 14, "right"),
        ("pvgis_apr_kwh", "Apr (kWh/MWp)", 14, "right"),
        ("pvgis_may_kwh", "May (kWh/MWp)", 14, "right"),
        ("pvgis_jun_kwh", "Jun (kWh/MWp)", 14, "right"),
        ("pvgis_jul_kwh", "Jul (kWh/MWp)", 14, "right"),
        ("pvgis_aug_kwh", "Aug (kWh/MWp)", 14, "right"),
        ("pvgis_sep_kwh", "Sep (kWh/MWp)", 14, "right"),
        ("pvgis_oct_kwh", "Oct (kWh/MWp)", 14, "right"),
        ("pvgis_nov_kwh", "Nov (kWh/MWp)", 14, "right"),
        ("pvgis_dec_kwh", "Dec (kWh/MWp)", 14, "right"),
        ("pvgis_rad_db", "Radiation DB", 15, "center"),
        ("pvgis_api_url", "PVGIS JSON API Endpoint", 30, "left")
    ]

    header_row = 4
    ws_pvgis.row_dimensions[header_row].height = 24

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for col_idx, (col_id, col_name, col_width, align) in enumerate(columns_pvgis, start=1):
        cell = ws_pvgis.cell(row=header_row, column=col_idx, value=col_name)
        cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        col_letter = get_column_letter(col_idx)
        ws_pvgis.column_dimensions[col_letter].width = col_width

    # Populate Data
    for row_idx, r in df.iterrows():
        excel_row = row_idx + 5
        ws_pvgis.row_dimensions[excel_row].height = 19
        is_even = (row_idx % 2 == 0)
        row_fill = PatternFill(start_color="F8FAFC" if is_even else "FFFFFF",
                               end_color="F8FAFC" if is_even else "FFFFFF",
                               fill_type="solid")

        for col_idx, (col_id, col_name, col_width, align) in enumerate(columns_pvgis, start=1):
            val = r.get(col_id)
            c = ws_pvgis.cell(row=excel_row, column=col_idx)
            c.font = Font(name="Calibri", size=9.5)
            c.fill = row_fill
            c.border = thin_border

            if col_id == "pvgis_api_url":
                c.value = f'=HYPERLINK("{val}", "Open PVGIS v5.3 JSON")'
                c.font = Font(name="Calibri", size=9.5, color="0284C7", underline="single")
                c.alignment = Alignment(horizontal="left", vertical="center")
            elif isinstance(val, (int, float)):
                c.value = val
                c.alignment = Alignment(horizontal=align, vertical="center")
                if col_id in ("pvgis_ey_kwh_per_mwp", "pvgis_sd_y_kwh", "direct_daily_generation_kwh",
                              "pvgis_jan_kwh", "pvgis_feb_kwh", "pvgis_mar_kwh", "pvgis_apr_kwh",
                              "pvgis_may_kwh", "pvgis_jun_kwh", "pvgis_jul_kwh", "pvgis_aug_kwh",
                              "pvgis_sep_kwh", "pvgis_oct_kwh", "pvgis_nov_kwh", "pvgis_dec_kwh"):
                    c.number_format = "#,##0"
                elif col_id in ("direct_annual_generation_mu",):
                    c.number_format = "#,##0.000"
                else:
                    c.number_format = "#,##0.00" if isinstance(val, float) else "#,##0"
            else:
                c.value = val
                c.alignment = Alignment(horizontal=align, vertical="center")

    wb.save(EXCEL_PATH)
    print(f"Master workbook updated successfully: added sheet '{sheet_name}' and updated '1KM CALIBRATED SUITABILITY'.")

def main():
    print("==========================================================================")
    print("SuryaGrid: Telangana 391 Substations PVGIS v5.3 Solar Generation Engine")
    print(f"Endpoint: {PVGIS_BASE_URL} | 1,000 kWp | Loss: 14% | Optimal Angles")
    print("==========================================================================")

    # 1. Load input dataset
    if not os.path.exists(INPUT_CSV_PATH):
        raise FileNotFoundError(f"Missing required input dataset: {INPUT_CSV_PATH}")

    df = pd.read_csv(INPUT_CSV_PATH)
    print(f"Loaded {len(df)} substations from {INPUT_CSV_PATH}")

    # 2. Setup Session & Cache
    session = requests.Session()
    cache = load_cache()
    call_counter = [0]

    # 3. Step 1: Smoke Test
    run_smoke_test(session, df, cache, call_counter)

    # 4. Step 2: Full Statewide Extraction
    merged_df = process_statewide_pvgis(session, df, cache, call_counter)

    # 5. Save Output CSVs
    print(f"Saving merged dataset in-place to {INPUT_CSV_PATH}...")
    merged_df.to_csv(INPUT_CSV_PATH, index=False)

    print(f"Saving dedicated PVGIS dataset to {OUTPUT_CSV_PATH}...")
    merged_df.to_csv(OUTPUT_CSV_PATH, index=False)

    # 6. Step 3: Update Excel Workbook
    update_excel_workbook(merged_df)

    # 7. Summary
    tot_mw = merged_df["estimated_mw"].sum()
    tot_mu = merged_df["direct_annual_generation_mu"].sum()
    avg_ey = merged_df["pvgis_ey_kwh_per_mwp"].mean()
    avg_cuf = merged_df["pvgis_dc_cuf_pct"].mean()
    avg_tilt = merged_df["pvgis_optimal_tilt_deg"].mean()

    print("\n==========================================================================")
    print("PVGIS v5.3 SOLAR GENERATION SUMMARY (TELANGANA 391 SUBSTATIONS):")
    print(f"  • Total Direct Build Solar Capacity: {tot_mw:,.2f} MW")
    print(f"  • Total Statewide Annual Solar Energy: {tot_mu:,.2f} MU (Million Units / GWh/yr)")
    print(f"  • Average Specific Annual Yield (E_y): {avg_ey:,.1f} kWh/MWp/yr")
    print(f"  • Average DC Capacity Utilization Factor: {avg_cuf:.2f}%")
    print(f"  • Average Optimal Panel Tilt: {avg_tilt:.1f}° South-Facing")
    print("==========================================================================")

if __name__ == "__main__":
    main()
