#!/usr/bin/env python3
"""
scripts/enrich_master_inventory_with_solar.py
Enriches SuryaGrid Master Substation Inventory and TGRAC Official Substations with:
1. Solar Bidding Headroom & Feeder Capacities (from 151-page TGsubstationsdata.pdf)
2. Existing Synchronized / Commissioned Solar Plants (from Solar_Projects_Synchronised_Grid.xls)
3. Generates updated Master Excel Workbook with all formatted sheets.
"""

import os
import re
import json
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from rapidfuzz import process, fuzz

def clean_name(n):
    if not n or pd.isna(n):
        return ''
    s = str(n).replace('\n', ' ')
    s = re.sub(r'\(.*?\)', '', s)
    s = re.sub(r'\b(ss|substation|switching|sws|indoor|gis|feeder)\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(400|220|132|33|11)\s*kv\b', '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    return ' '.join(s.lower().split()).strip()

def enrich_inventory():
    print("Enriching SuryaGrid Inventory with Solar Feasibility & Connected Generation...")
    
    # 1. Load parsed solar data
    df_feeders = pd.read_csv('data/processed/solar_bidding_feeders_substations.csv')
    df_132 = pd.read_csv('data/processed/solar_bidding_132_substations.csv')
    df_solar_proj = pd.read_csv('data/processed/telangana_synchronized_solar_projects.csv')
    
    # Aggregate 132/33 kV substation solar headroom
    # Group by cleaned name
    df_132['clean_name'] = df_132['ss_132_name'].apply(clean_name)
    substation_headroom = {}
    for _, r in df_132.iterrows():
        cname = r['clean_name']
        if cname and (cname not in substation_headroom or r['max_available_capacity_mw'] > substation_headroom[cname]['headroom_mw']):
            substation_headroom[cname] = {
                'raw_name': r['ss_132_name'],
                'district': r['district'],
                'headroom_mw': r['max_available_capacity_mw'],
                'ptr_capacity': r['ptr_capacity'],
                'bay_ext_feasible': r['bay_extension_feasible']
            }
            
    # Also aggregate feeder count & list per 132 substation
    feeders_by_132 = {}
    for _, r in df_feeders.iterrows():
        cname = clean_name(r['ss_132_33'])
        if cname:
            if cname not in feeders_by_132:
                feeders_by_132[cname] = set()
            if pd.notna(r['feeder_33']) and str(r['feeder_33']).strip():
                feeders_by_132[cname].add(str(r['feeder_33']).strip())
                
    # Aggregate solar projects by injection substation
    solar_by_substation = {}
    for _, r in df_solar_proj.iterrows():
        inj = r['Injection Substation']
        if pd.notna(inj) and str(inj).strip():
            cinj = clean_name(inj)
            if cinj:
                if cinj not in solar_by_substation:
                    solar_by_substation[cinj] = {
                        'total_mw': 0.0,
                        'projects': []
                    }
                cap = float(r['Commissioned Capacity (MW)']) if pd.notna(r['Commissioned Capacity (MW)']) else 0.0
                solar_by_substation[cinj]['total_mw'] += cap
                comp = str(r['Company Name']).strip()
                solar_by_substation[cinj]['projects'].append(f"{comp} ({cap:.1f} MW)")

    # 2. Match with TGRAC Official Substations
    tgrac_csv = 'data/processed/tgrac_substations_official.csv'
    df_tgrac = pd.read_csv(tgrac_csv)
    
    tgrac_headroom_col = []
    tgrac_feeder_cnt_col = []
    tgrac_solar_mw_col = []
    tgrac_solar_proj_col = []
    
    headroom_keys = list(substation_headroom.keys())
    solar_keys = list(solar_by_substation.keys())
    
    matched_headroom_tgrac = 0
    matched_solar_tgrac = 0
    
    for _, r in df_tgrac.iterrows():
        ss_name = r['Substation Name']
        c_name = clean_name(ss_name)
        
        # Match headroom
        hr_val = 0.0
        f_cnt = 0
        if c_name in substation_headroom:
            hr_val = substation_headroom[c_name]['headroom_mw']
            f_cnt = len(feeders_by_132.get(c_name, []))
            matched_headroom_tgrac += 1
        else:
            best = process.extractOne(c_name, headroom_keys, scorer=fuzz.token_sort_ratio)
            if best and best[1] >= 82:
                hr_val = substation_headroom[best[0]]['headroom_mw']
                f_cnt = len(feeders_by_132.get(best[0], []))
                matched_headroom_tgrac += 1
                
        # Match connected solar
        sol_mw = 0.0
        sol_projs = ""
        if c_name in solar_by_substation:
            sol_mw = solar_by_substation[c_name]['total_mw']
            sol_projs = "; ".join(solar_by_substation[c_name]['projects'])
            matched_solar_tgrac += 1
        else:
            best_s = process.extractOne(c_name, solar_keys, scorer=fuzz.token_sort_ratio)
            if best_s and best_s[1] >= 82:
                sol_mw = solar_by_substation[best_s[0]]['total_mw']
                sol_projs = "; ".join(solar_by_substation[best_s[0]]['projects'])
                matched_solar_tgrac += 1
                
        tgrac_headroom_col.append(hr_val if hr_val > 0 else "Pending Feeder Audit")
        tgrac_feeder_cnt_col.append(f_cnt if f_cnt > 0 else "N/A")
        tgrac_solar_mw_col.append(sol_mw if sol_mw > 0 else 0.0)
        tgrac_solar_proj_col.append(sol_projs if sol_projs else "None")
        
    df_tgrac['Available Solar Headroom (MW)'] = tgrac_headroom_col
    df_tgrac['33kV Feeders Count'] = tgrac_feeder_cnt_col
    df_tgrac['Existing Solar Connected (MW)'] = tgrac_solar_mw_col
    df_tgrac['Connected Solar Power Plants'] = tgrac_solar_proj_col
    
    df_tgrac.to_csv(tgrac_csv, index=False)
    print(f"Enriched TGRAC: {matched_headroom_tgrac} matched with Solar Bidding Headroom, {matched_solar_tgrac} matched with Solar Plants.")

    # 3. Match with Master Statewide Inventory
    with open('outputs/telangana_electrical_infrastructure.geojson') as f:
        master_gj = json.load(f)
        
    for feat in master_gj['features']:
        props = feat['properties']
        fname = props.get('Facility Name', '')
        c_name = clean_name(fname)
        
        hr_val = 0.0
        if c_name in substation_headroom:
            hr_val = substation_headroom[c_name]['headroom_mw']
        else:
            best = process.extractOne(c_name, headroom_keys, scorer=fuzz.token_sort_ratio)
            if best and best[1] >= 82:
                hr_val = substation_headroom[best[0]]['headroom_mw']
                
        sol_mw = 0.0
        sol_projs = ""
        if c_name in solar_by_substation:
            sol_mw = solar_by_substation[c_name]['total_mw']
            sol_projs = "; ".join(solar_by_substation[c_name]['projects'])
        else:
            best_s = process.extractOne(c_name, solar_keys, scorer=fuzz.token_sort_ratio)
            if best_s and best_s[1] >= 82:
                sol_mw = solar_by_substation[best_s[0]]['total_mw']
                sol_projs = "; ".join(solar_by_substation[best_s[0]]['projects'])
                
        props['Available Solar Headroom (MW)'] = hr_val if hr_val > 0 else "Pending Feeder Audit"
        props['Existing Solar Connected (MW)'] = sol_mw if sol_mw > 0 else 0.0
        props['Connected Solar Plants'] = sol_projs if sol_projs else "None"
        
    with open('outputs/telangana_electrical_infrastructure.geojson', 'w') as f:
        json.dump(master_gj, f, indent=2)
    print("Enriched outputs/telangana_electrical_infrastructure.geojson with solar attributes.")

    # 4. Update Excel Workbook
    wb_path = 'outputs/SuryaGrid_Telangana_Statewide_Substation_Inventory.xlsx'
    wb = openpyxl.load_workbook(wb_path)
    
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # Sheet: SOLAR BIDDING FEASIBILITY
    if 'SOLAR BIDDING FEASIBILITY' in wb.sheetnames:
        del wb['SOLAR BIDDING FEASIBILITY']
    ws_sb = wb.create_sheet('SOLAR BIDDING FEASIBILITY')
    
    sb_cols = [
        'District', '132/33 kV Substation', 'PTR Capacity', 'Max Available Capacity (MW)',
        '132kV Bay Extension Feasible', '33kV Bays Available', 'Space for Bay Extension',
        '33 kV Feeder Name', 'Downstream 33/11 kV Substation', 'Feeder Solar Feasibility (MW)', 'Document Page'
    ]
    ws_sb.append(sb_cols)
    for col_idx in range(1, len(sb_cols) + 1):
        cell = ws_sb.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for _, r in df_feeders.iterrows():
        row_vals = [
            r['district'], r['ss_132_33'], r['ptr_capacity'], r['ss_132_max_avail_mw'],
            r['bay_ext_feasible'], r['bays_available'], r['space_available'],
            r['feeder_33'], r['substation_33_11'], r['feeder_feasibility_mw'], r['page']
        ]
        ws_sb.append(row_vals)
        for c_idx in range(1, len(row_vals) + 1):
            c = ws_sb.cell(row=ws_sb.max_row, column=c_idx)
            c.font = data_font
            c.border = border_thin

    # Sheet: SYNCHRONIZED SOLAR PLANTS
    if 'SYNCHRONIZED SOLAR PLANTS' in wb.sheetnames:
        del wb['SYNCHRONIZED SOLAR PLANTS']
    ws_sp = wb.create_sheet('SYNCHRONIZED SOLAR PLANTS')
    
    sp_cols = [
        'Scheme', 'Company / Developer Name', 'Location / District',
        'Contracted Capacity (MW)', 'Commissioned Capacity (MW)', 'Voltage Level',
        'Injection Substation', 'COD / Commissioning Date'
    ]
    ws_sp.append(sp_cols)
    for col_idx in range(1, len(sp_cols) + 1):
        cell = ws_sp.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for _, r in df_solar_proj.iterrows():
        row_vals = [
            r['Scheme'], r['Company Name'], r['Location / District'],
            r['Allocated Capacity (MW)'], r['Commissioned Capacity (MW)'], r['Voltage Level'],
            r['Injection Substation'], r['COD / Commissioning Date']
        ]
        ws_sp.append(row_vals)
        for c_idx in range(1, len(row_vals) + 1):
            c = ws_sp.cell(row=ws_sp.max_row, column=c_idx)
            c.font = data_font
            c.border = border_thin

    # Update TGRAC TGTRANSCO OFFICIAL sheet with new columns
    if 'TGRAC TGTRANSCO OFFICIAL' in wb.sheetnames:
        del wb['TGRAC TGTRANSCO OFFICIAL']
    ws_tg = wb.create_sheet('TGRAC TGTRANSCO OFFICIAL', index=3)
    
    tg_cols = list(df_tgrac.columns)
    ws_tg.append(tg_cols)
    for col_idx in range(1, len(tg_cols) + 1):
        cell = ws_tg.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
    for _, r in df_tgrac.iterrows():
        ws_tg.append(list(r.values))
        for c_idx in range(1, len(tg_cols) + 1):
            c = ws_tg.cell(row=ws_tg.max_row, column=c_idx)
            c.font = data_font
            c.border = border_thin

    # Auto-fit column widths
    for sheet in [ws_sb, ws_sp, ws_tg]:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col[:50])
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

    wb.save(wb_path)
    print(f"Updated Excel workbook: {wb_path} with {len(wb.sheetnames)} sheets.")

if __name__ == '__main__':
    enrich_inventory()
