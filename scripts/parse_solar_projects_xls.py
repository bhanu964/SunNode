#!/usr/bin/env python3
"""
scripts/parse_solar_projects_xls.py
Parses the official TSSPDCL/TGTRANSCO document:
'Solar_Projects_Synchronised_Grid_30.04.2016_(1).xls'

Extracts all grid-synchronized and commissioned solar power projects:
- RPSSGP Scheme (JNNSM)
- Bundled Power (NVVN) Scheme
- Solar Bidding 2012 (Competitive Bidding)
- Solar Bidding Open Offer 2013
- Solar Bidding 2014 (Competitive Bidding)
- REC Mechanism / Third Party & Captive
"""

import os
import re
import pandas as pd

def parse_solar_projects_xls(excel_path=None):
    if excel_path is None:
        candidates = [
            '/Users/bhanuprasad/.gemini/antigravity/brain/fd0a8b34-ef7b-47ae-9d33-8e2736284ecd/.user_uploaded/media_1795164291533_833d6818.xls',
            'data/raw/Solar_Projects_Synchronised_Grid_30.04.2016_(1).xls'
        ]
        for c in candidates:
            if os.path.exists(c):
                excel_path = c
                break
                
    if not excel_path or not os.path.exists(excel_path):
        raise FileNotFoundError(f"Solar projects Excel file not found!")

    print(f"Reading solar projects from: {excel_path}")
    xl = pd.ExcelFile(excel_path, engine='xlrd')
    
    all_projects = []
    
    for sheet in xl.sheet_names:
        if sheet == 'Abstract':
            continue
        df = xl.parse(sheet)
        
        # Locate header row
        header_idx = None
        for idx, r in df.iterrows():
            vals = [str(v).lower() for v in r.values if pd.notna(v)]
            if any('name of the company' in v for v in vals) or any('company' in v for v in vals):
                header_idx = idx
                break
        if header_idx is None:
            continue
        
        for r_idx in range(header_idx + 1, len(df)):
            row = df.iloc[r_idx]
            if row.dropna().empty:
                continue
            c0 = str(row.iloc[0]).strip()
            c1 = str(row.iloc[1]).strip() if df.shape[1] > 1 else ''
            if any(k in c0.lower() for k in ['total', 'sub-total', 'sub total']) or any(k in c1.lower() for k in ['total', 'sub-total', 'sub total']):
                continue
            if 'list of customers' in c1.lower():
                continue
                
            company = str(row.iloc[1]).replace('\n', ' ').strip() if pd.notna(row.iloc[1]) else ''
            if not company or company == 'nan':
                continue
                
            proj = {
                'Scheme': sheet,
                'Company Name': company,
                'Allocated Capacity (MW)': None,
                'Commissioned Capacity (MW)': None,
                'Voltage Level': None,
                'Injection Substation': None,
                'Location / District': None,
                'COD / Commissioning Date': None
            }
            
            if sheet in ['RPSSGP Scheme', 'NVVN Scheme']:
                proj['Location / District'] = str(row.iloc[2]).replace('\n', ' ').strip() if pd.notna(row.iloc[2]) else ''
                proj['Voltage Level'] = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ''
                val_mw = float(row.iloc[4]) if pd.notna(row.iloc[4]) else None
                proj['Commissioned Capacity (MW)'] = val_mw
                proj['Allocated Capacity (MW)'] = val_mw
                proj['COD / Commissioning Date'] = str(row.iloc[6]).strip() if df.shape[1] > 6 and pd.notna(row.iloc[6]) else ''
            elif sheet in ['Solar Bidding 2012', 'Solar Bidding Open Offer', 'Solar Bidding 2014']:
                proj['Allocated Capacity (MW)'] = float(row.iloc[2]) if pd.notna(row.iloc[2]) and str(row.iloc[2]).replace('.', '', 1).isdigit() else None
                proj['Commissioned Capacity (MW)'] = float(row.iloc[3]) if pd.notna(row.iloc[3]) and str(row.iloc[3]).replace('.', '', 1).isdigit() else None
                proj['Voltage Level'] = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
                proj['Injection Substation'] = str(row.iloc[5]).replace('\n', ' ').strip() if pd.notna(row.iloc[5]) else ''
                proj['COD / Commissioning Date'] = str(row.iloc[7]).strip() if df.shape[1] > 7 and pd.notna(row.iloc[7]) else ''
            elif sheet == 'Third Party & Captive':
                proj['Allocated Capacity (MW)'] = float(row.iloc[2]) if pd.notna(row.iloc[2]) and str(row.iloc[2]).replace('.', '', 1).isdigit() else None
                proj['Commissioned Capacity (MW)'] = float(row.iloc[3]) if pd.notna(row.iloc[3]) and str(row.iloc[3]).replace('.', '', 1).isdigit() else None
                proj['Voltage Level'] = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
                proj['Injection Substation'] = str(row.iloc[5]).replace('\n', ' ').strip() if pd.notna(row.iloc[5]) else ''
                proj['Location / District'] = str(row.iloc[6]).strip() if df.shape[1] > 6 and pd.notna(row.iloc[6]) else ''
                proj['COD / Commissioning Date'] = str(row.iloc[7]).strip() if df.shape[1] > 7 and pd.notna(row.iloc[7]) else ''
                
            all_projects.append(proj)
            
    df_projects = pd.DataFrame(all_projects)
    
    # Save copy to data/raw and data/processed
    os.makedirs('data/processed', exist_ok=True)
    df_projects.to_csv('data/processed/telangana_synchronized_solar_projects.csv', index=False)
    
    print("\n--- Solar Projects Summary ---")
    print(f"Total Commissioned/Synchronized Projects: {len(df_projects)}")
    print(f"Total Synchronized Solar Capacity: {df_projects['Commissioned Capacity (MW)'].sum():.2f} MW")
    print(f"Total Contracted Capacity: {df_projects['Allocated Capacity (MW)'].sum():.2f} MW")
    print("\nBreakdown by Scheme:")
    print(df_projects.groupby('Scheme')['Commissioned Capacity (MW)'].agg(['count', 'sum']))
    
    return df_projects

if __name__ == '__main__':
    parse_solar_projects_xls()
