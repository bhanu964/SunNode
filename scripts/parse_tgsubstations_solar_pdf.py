#!/usr/bin/env python3
"""
scripts/parse_tgsubstations_solar_pdf.py
Parses the 151-page official Telangana DISCOM/TRANSCO document:
'Details of 132/33 kV Substations and Associated 33/11 KV Substation in TSSPDCL & TSNPDCL for Solar Bidding'

Extracts:
- 132/33 kV Grid Substations and their PTR capacity & available hosting headroom (MW)
- 33 kV Feeders and their solar injection feasibility (MW)
- Downstream 33/11 kV Substations on each feeder
- District-wise summaries
"""

import os
import re
import pdfplumber
import pandas as pd

def clean_str(val):
    if not val:
        return ''
    s = str(val).replace('\n', ' ')
    s = ' '.join(s.split())
    return s.strip()

COLLISION_FIXES = {
    73: {'name': 'Bhainsa', 'sl_no': '3', 'ptr': '2x31.5 = 63', 'avail_mw': 30.0, 'bay_ext': 'No', 'bay_avail': 'Yes', 'space_avail': 'Yes'},
    83: {'name': 'Penubally', 'sl_no': '2', 'ptr': '2x31.5 = 63', 'avail_mw': 18.0, 'bay_ext': 'No', 'bay_avail': 'Yes', 'space_avail': 'Yes'},
    111: {'name': 'Shanigaram', 'sl_no': '19', 'ptr': '2x16 = 32', 'avail_mw': 15.0, 'bay_ext': 'No', 'bay_avail': 'Yes', 'space_avail': 'Yes'},
    112: {'name': 'Yellareddypet', 'sl_no': '21', 'ptr': '1x25 + 1x16 = 41', 'avail_mw': 19.0, 'bay_ext': 'No', 'bay_avail': 'Yes', 'space_avail': 'Yes'},
    130: {'name': 'Banswada', 'sl_no': '16', 'ptr': '1x10/16 + 1x31.5 = 47.5', 'avail_mw': 23.0, 'bay_ext': 'Yes', 'bay_avail': 'Yes', 'space_avail': 'Yes'},
    144: {'name': 'Peddanagaram', 'sl_no': '12', 'ptr': '2x16 = 32', 'avail_mw': 15.0, 'bay_ext': 'No', 'bay_avail': 'Yes', 'space_avail': 'Yes'},
    148: {'name': 'Warangal', 'sl_no': '16', 'ptr': '1x50 + 1x80 = 130', 'avail_mw': 62.0, 'bay_ext': 'Yes', 'bay_avail': 'No', 'space_avail': 'No'},
}

def parse_solar_bidding_pdf(pdf_path='TGsubstationsdata.pdf'):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    print(f"Reading {pdf_path} (151 pages)...")
    
    feeder_records = []
    substation_132_records = {}
    district_totals = {}
    
    current_district = 'NALGONDA'
    current_ss = {}
    current_feeder = ''
    current_feeder_feasibility = ''
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            tables = page.extract_tables()
            if not tables or not tables[0]:
                continue
            
            # Check if this page has a known printing collision in row 0
            if page_num in COLLISION_FIXES:
                fix = COLLISION_FIXES[page_num]
                ss_key = f"{current_district}_{fix['name']}"
                current_ss = {
                    'district': current_district,
                    'ss_132_name': fix['name'],
                    'ss_raw_name': fix['name'],
                    'ptr_capacity': fix['ptr'],
                    'max_available_capacity_mw': fix['avail_mw'],
                    'bay_extension_feasible': fix['bay_ext'],
                    'bays_available': fix['bay_avail'],
                    'space_available': fix['space_avail'],
                    'first_page': page_num
                }
                substation_132_records[ss_key] = current_ss
                current_feeder = ''
                current_feeder_feasibility = ''
                
            for r_idx, row in enumerate(tables[0]):
                if not row or not any(row):
                    continue
                cells = [clean_str(c) for c in row]
                while len(cells) < 10:
                    cells.append('')
                
                c0, c1, c2, c3, c4, c5, c6, c7, c8, c9 = cells[:10]
                row_text = ' '.join(cells).upper()
                
                # Check for district header
                for d in ['NALGONDA', 'RANGA REDDY', 'MAHABOOBNAGAR', 'MEDAK', 'ADILABAD', 'KHAMMAM', 'KARIMNAGAR', 'NIZAMABAD', 'WARANGAL']:
                    if d in row_text and ('SL. NO.' not in row_text or 'TOTAL:' in row_text):
                        if 'TOTAL:' not in row_text:
                            current_district = d
                            current_ss = {}
                            current_feeder = ''
                            current_feeder_feasibility = ''
                
                # Check for Total row
                if 'TOTAL:' in c0.upper() or 'TOTAL:' in c1.upper():
                    tot_val = c3 or c2 or c1
                    tot_num = re.sub(r'[^0-9.]', '', tot_val)
                    if tot_num:
                        district_totals[current_district] = float(tot_num)
                    continue
                
                # If page had collision fix, skip row 0 and row 1 header processing for SS detection
                if page_num in COLLISION_FIXES and r_idx in [0, 1]:
                    pass
                else:
                    # Skip header rows
                    if 'SL. NO.' in c0.upper() or 'NAME OF 132/33' in c1.upper() or (c0 in ['1', '2', '3', '4', '5'] and c1 in ['2', 'Sub-Station', '']):
                        continue
                    
                    # Check if new 132/33 kV Substation row
                    clean_c1 = re.sub(r'^[0-9\s]+', '', c1).strip()
                    clean_c1 = re.sub(r'\s+[0-9]$', '', clean_c1).strip()
                    name_norm = re.sub(r'^(132\s*/\s*33\s*kv\s*(ss)?|132\s*kv\s*(ss)?)\s*', '', clean_c1, flags=re.IGNORECASE).strip()
                    
                    if name_norm and name_norm.upper() not in ['NAME OF 132/33 KV', 'SUB-STATION', '']:
                        ss_key = f"{current_district}_{name_norm}"
                        # Clean available capacity
                        avail_clean = c3.strip()
                        avail_clean = re.sub(r'\s+[0-9]$', '', avail_clean)
                        avail_mw_match = re.search(r'([0-9]+(?:\.[0-9]+)?)', avail_clean)
                        avail_mw = float(avail_mw_match.group(1)) if avail_mw_match else 0.0
                        
                        current_ss = {
                            'district': current_district,
                            'ss_132_name': name_norm,
                            'ss_raw_name': clean_c1,
                            'ptr_capacity': c2,
                            'max_available_capacity_mw': avail_mw,
                            'bay_extension_feasible': c4,
                            'bays_available': c5,
                            'space_available': c6,
                            'first_page': page_num
                        }
                        substation_132_records[ss_key] = current_ss
                        current_feeder = ''
                        current_feeder_feasibility = ''
                
                # Check 33 kV Feeder
                clean_c7 = re.sub(r'\s+[0-9]$', '', c7).strip()
                if clean_c7 and clean_c7.upper() not in ['NO. OF 33 KV FEEDERS AVAILABLE; MENTION THE NAMES OF 33 KV FEEDERS', '8']:
                    current_feeder = clean_c7
                    if c9:
                        current_feeder_feasibility = c9
                
                if c9:
                    current_feeder_feasibility = c9
                    
                # Downstream 33/11 kV Substation
                clean_c8 = c8.strip()
                if clean_c8 and clean_c8.upper() not in ['NAME OF 33/11KV SUBSTATIONS ON THE FEEDER', '9']:
                    feeder_mw_match = re.search(r'([0-9]+(?:\.[0-9]+)?)', current_feeder_feasibility)
                    feeder_mw = float(feeder_mw_match.group(1)) if feeder_mw_match else 0.0
                    
                    feeder_records.append({
                        'district': current_district,
                        'ss_132_33': current_ss.get('ss_132_name', ''),
                        'ss_132_raw': current_ss.get('ss_raw_name', ''),
                        'ptr_capacity': current_ss.get('ptr_capacity', ''),
                        'ss_132_max_avail_mw': current_ss.get('max_available_capacity_mw', 0.0),
                        'bay_ext_feasible': current_ss.get('bay_extension_feasible', ''),
                        'bays_available': current_ss.get('bays_available', ''),
                        'space_available': current_ss.get('space_available', ''),
                        'feeder_33': current_feeder,
                        'substation_33_11': clean_c8,
                        'feeder_feasibility_mw': feeder_mw,
                        'page': page_num
                    })
    
    df_feeders = pd.DataFrame(feeder_records)
    df_132 = pd.DataFrame(list(substation_132_records.values()))
    
    os.makedirs('data/processed', exist_ok=True)
    df_feeders.to_csv('data/processed/solar_bidding_feeders_substations.csv', index=False)
    df_132.to_csv('data/processed/solar_bidding_132_substations.csv', index=False)
    
    print("\n--- Extraction Results ---")
    print(f"Total 33/11 kV Substation Feeder Mappings: {len(df_feeders)}")
    print(f"Unique 33/11 kV Substations: {df_feeders['substation_33_11'].nunique()}")
    print(f"Unique 132/33 kV Grid Substations: {len(df_132)}")
    print(f"Total 132/33 kV Headroom Capacity: {df_132['max_available_capacity_mw'].sum():.1f} MW")
    print(f"District Summaries: {district_totals}")
    
    return df_feeders, df_132, district_totals

if __name__ == '__main__':
    parse_solar_bidding_pdf()
