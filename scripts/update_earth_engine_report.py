#!/usr/bin/env python3
"""
scripts/update_earth_engine_report.py
Updates reports/earth_engine_report.html with Stage 4.5 Data Integrity,
Voltage-Tier Evacuation, Before vs After Delta Table, and Split Leaderboards.
"""

import os
import pandas as pd

df_master = pd.read_csv('data/processed/suryagrid_master_391_techno_economic.csv')
df_golden = pd.read_csv('data/processed/suryagrid_top20_golden_substations.csv')
df_eht = pd.read_csv('data/processed/suryagrid_top20_utility_eht_substations.csv')
df_kusum = pd.read_csv('data/processed/suryagrid_top20_pm_kusum_substations.csv')

# Compute deduplicated and raw totals
raw_land_mw = df_master['land_solar_mw'].sum()
dedup_land_mw = (df_master['land_solar_mw'] * df_master['overlap_factor']).sum()

raw_deploy_mw = df_master['deployable_solar_mw'].sum()
dedup_deploy_mw = (df_master['deployable_solar_mw'] * df_master['overlap_factor']).sum()

raw_capex_cr = df_master['turnkey_capex_cr'].sum()
dedup_capex_cr = (df_master['turnkey_capex_cr'] * df_master['overlap_factor']).sum()

raw_rev_cr = df_master['annual_gross_revenue_cr'].sum()
dedup_rev_cr = (df_master['annual_gross_revenue_cr'] * df_master['overlap_factor']).sum()

dedup_ebitda_cr = (df_master['annual_net_ebitda_cr'] * df_master['overlap_factor']).sum()
strict_payback_yrs = dedup_capex_cr / dedup_ebitda_cr

raw_profit_cr = df_master['lifetime_25yr_net_profit_cr'].sum()
dedup_profit_cr = (df_master['lifetime_25yr_net_profit_cr'] * df_master['overlap_factor']).sum()

coloc_count = df_master['is_colocated_overlap'].sum()

# Build HTML blocks
summary_cards_html = f"""  <div class="grid" style="margin-top: -0.75rem;">
    <div class="card">
      <div class="card-title">1 km Land Potential (Farmland Ready)</div>
      <div class="card-value" style="color: #22c55e;">{dedup_land_mw:,.0f} MW <span style="font-size:12px;color:#94a3b8;">({raw_land_mw:,.0f} MW Raw)</span></div>
      <div class="card-sub">Deduplicated (-617 MW Overlap across {coloc_count} Co-Located Substations)</div>
    </div>
    <div class="card">
      <div class="card-title">True Deployable Capacity (min(Land, Grid))</div>
      <div class="card-value" style="color: #38bdf8;">{dedup_deploy_mw:,.0f} MW <span style="font-size:12px;color:#94a3b8;">({raw_deploy_mw:,.0f} MW Raw)</span></div>
      <div class="card-sub">247 SS Grid Constrained (63.2%) | 130 SS Land Constrained (33.2%)</div>
    </div>
    <div class="card">
      <div class="card-title">Annual Clean Generation (Deployable)</div>
      <div class="card-value" style="color: #f59e0b;">18,793 MU/yr</div>
      <div class="card-sub">Million Units (GWh/yr) via PVGIS v5.3 Irradiance</div>
    </div>
    <div class="card">
      <div class="card-title">25-Year Cumulative Net Profit</div>
      <div class="card-value" style="color: #a855f7;">₹{dedup_profit_cr:,.0f} Cr <span style="font-size:12px;color:#94a3b8;">(₹{raw_profit_cr:,.0f} Cr Raw)</span></div>
      <div class="card-sub">Statewide Cash-Flow Payback: strictly {strict_payback_yrs:.2f} Years</div>
    </div>
  </div>

  <div class="notice-box">
    <strong>Stage 4.5 Data Integrity, Voltage-Tier Evacuation & Leaderboard Split:</strong> All 391 official TGRAC substations feature 1-to-1 Annexure-D matching (eliminating duplicate spare allocations), spatial overlap deduplication for 53 co-located substations (< 2 km), voltage-class aligned evacuation (33 kV VCB, 132 kV SF6, 220 kV SF6), tiered tariffs (PM-KUSUM ₹3.13 vs Utility STU ₹2.75), strict cash-flow payback ({strict_payback_yrs:.2f} yrs), and 33 normalized Telangana districts!
  </div>

  <!-- Stage 4.5 Before vs After Audit Delta Matrix -->
  <div style="background: #1e293b; padding: 1.25rem; border-radius: 0.75rem; border: 1px solid #334155; margin-bottom: 2rem; overflow-x: auto;">
    <h3 style="margin-top:0; color:#38bdf8; font-size: 1.15rem;">Stage 4.5 Before vs After Audit Delta Matrix</h3>
    <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
      <thead>
        <tr style="border-bottom:2px solid #334155; color:#94a3b8;">
          <th style="padding:6px;">Dimension / Metric</th>
          <th style="padding:6px;">Stage 4 (Before Audit)</th>
          <th style="padding:6px;">Stage 4.5 (After Audit & Dedup)</th>
          <th style="padding:6px;">Engineering & Commercial Significance</th>
        </tr>
      </thead>
      <tbody>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">Co-Located Overlaps (&lt; 2 km)</td>
          <td style="padding:6px; color:#ef4444;">Ignored (Double-counted)</td>
          <td style="padding:6px; color:#22c55e; font-weight:bold;">53 Substations Flagged &amp; Deduplicated</td>
          <td style="padding:6px; color:#94a3b8;">Spatial buffer overlap factors eliminate double-counting shared farmland.</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">Statewide Land Potential (MW)</td>
          <td style="padding:6px; color:#94a3b8;">29,983.9 MW (Raw sum)</td>
          <td style="padding:6px; color:#22c55e; font-weight:bold;">29,366.4 MW (Deduplicated)</td>
          <td style="padding:6px; color:#94a3b8;">Eliminates 617.5 MW of overlapping 1 km farmland buffers across 27 clusters.</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">True Deployable Solar Capacity</td>
          <td style="padding:6px; color:#94a3b8;">12,202.8 MW (Raw sum)</td>
          <td style="padding:6px; color:#38bdf8; font-weight:bold;">12,602.6 MW (Dedup) / 12,949.9 MW (Raw)</td>
          <td style="padding:6px; color:#94a3b8;">Enforces 1-to-1 Annexure-D matching; corrects Dichpally 400kV (650.3 MW) &amp; 220kV (143.0 MW).</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">Evacuation Voltage Classes</td>
          <td style="padding:6px; color:#ef4444;">Blanket 33 kV on all substations</td>
          <td style="padding:6px; color:#facc15; font-weight:bold;">33 kV (275 SS), 132 kV (85 SS), 220 kV (31 SS)</td>
          <td style="padding:6px; color:#94a3b8;">Matches TGTRANSCO Grid Code: 33kV VCB bays, 132kV SF6 bays, 220kV SF6 line bays.</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">Tariff &amp; Revenue Modeling</td>
          <td style="padding:6px; color:#ef4444;">Blanket ₹3.13/kWh across all</td>
          <td style="padding:6px; color:#a855f7; font-weight:bold;">Dual-Tier: ₹3.13 (PM-KUSUM) &amp; ₹2.75 (Utility STU)</td>
          <td style="padding:6px; color:#94a3b8;">Decentralized distribution feeder solar vs Utility-scale transmission STU pooling.</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">Statewide Simple Payback Period</td>
          <td style="padding:6px; color:#ef4444;">9.20 Years (Mean of ratios)</td>
          <td style="padding:6px; color:#38bdf8; font-weight:bold;">strictly 10.13 Years (Aggregate Cash Flows)</td>
          <td style="padding:6px; color:#94a3b8;">Reconciled strictly via Total CAPEX / (Total Revenue - Total OPEX &amp; Lease).</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">25-Year Cumulative Net Profit</td>
          <td style="padding:6px; color:#94a3b8;">₹65,642.0 Cr (No availability multiplier)</td>
          <td style="padding:6px; color:#22c55e; font-weight:bold;">₹58,857.9 Cr (Dedup) / ₹61,805.6 Cr (Raw)</td>
          <td style="padding:6px; color:#94a3b8;">Incorporates 0.91 lifetime degradation (0.940) &amp; grid availability (0.970) factor.</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">District Normalization</td>
          <td style="padding:6px; color:#ef4444;">35 spelling variants (Rangareddy, UNKNOWN)</td>
          <td style="padding:6px; color:#22c55e; font-weight:bold;">Exactly 33 Official Districts</td>
          <td style="padding:6px; color:#94a3b8;">Fully clean administrative boundary join with telangana_33_districts.geojson.</td>
        </tr>
        <tr>
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">Leaderboard Architecture</td>
          <td style="padding:6px; color:#ef4444;">Single mixed leaderboard (Score saturated)</td>
          <td style="padding:6px; color:#38bdf8; font-weight:bold;">Split: Top 20 EHT vs Top 20 PM-KUSUM</td>
          <td style="padding:6px; color:#94a3b8;">Recalibrated 150 MW capacity cap; clear operational split for DISCOM vs STU tenders.</td>
        </tr>
      </tbody>
    </table>
  </div>
"""

# Benchmark table
benchmarks = [
    ("Gajwel (400KV)", "Siddipet", "121.2 MW", "38.0 MW", "38.0 MW", "GRID TRANSFORMER CONSTRAINED", "101.8 A @ 220kV (1 x 220 kV SF6 Line Bay)", "Utility STU (₹2.75)", "57.28 MU", "10.89 y", "58.5"),
    ("K.M.Pally (220KV)", "Nalgonda", "119.6 MW", "158.0 MW", "119.6 MW", "1 KM LAND RADIUS CONSTRAINED", "533.4 A @ 132kV (3 x 132 kV SF6 Line Bays)", "Utility STU (₹2.75)", "178.44 MU", "11.02 y", "75.0"),
    ("Ganeshpahad", "Nalgonda", "132.6 MW", "15.0 MW", "15.0 MW", "GRID TRANSFORMER CONSTRAINED", "267.8 A @ 33kV (1 x 33 kV VCB Feeder Bay)", "PM-KUSUM (₹3.13)", "21.91 MU", "9.57 y", "48.8"),
    ("Kondapaka", "Siddipet", "85.9 MW", "28.4 MW", "28.4 MW", "GRID TRANSFORMER CONSTRAINED", "506.9 A @ 33kV (2 x 33 kV VCB Feeder Bays)", "PM-KUSUM (₹3.13)", "42.66 MU", "9.26 y", "56.9"),
    ("Narayanguda", "Hyderabad", "0.0 MW", "45.0 MW", "0.0 MW", "LAND / URBAN EXCLUDED (0 MW)", "0.0 A @ 33kV (0 Bays)", "None (0 MW)", "0.00 MU", "0.00 y", "0.0")
]

benchmark_html = """  <div style="background: #1e293b; padding: 1.25rem; border-radius: 0.75rem; border: 1px solid #334155; margin-bottom: 2rem; overflow-x: auto;">
    <h3 style="margin-top:0; color:#38bdf8; font-size: 1.15rem;">Stage 4.5 Benchmark Substations: Land vs Grid Spare vs Evacuation Voltage &amp; Tariff</h3>
    <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
      <thead>
        <tr style="border-bottom:2px solid #334155; color:#94a3b8;">
          <th style="padding:6px;">Substation</th>
          <th style="padding:6px;">District</th>
          <th style="padding:6px;">Land MW</th>
          <th style="padding:6px;">Grid MW</th>
          <th style="padding:6px;">Deployable MW</th>
          <th style="padding:6px;">Active Bottleneck</th>
          <th style="padding:6px;">Grid Evacuation &amp; Feeder Bays</th>
          <th style="padding:6px;">Tariff Tier</th>
          <th style="padding:6px;">Annual MU</th>
          <th style="padding:6px;">Payback</th>
          <th style="padding:6px;">Master Score</th>
        </tr>
      </thead>
      <tbody>
"""
for name, dist, lmw, gmw, dmw, bneck, evac, tariff, mu, pb, sc in benchmarks:
    b_color = "#facc15" if "GRID" in bneck else ("#38bdf8" if "LAND" in bneck else "#ef4444")
    dmw_color = "#38bdf8" if "0.0" not in dmw else "#ef4444"
    benchmark_html += f"""        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:6px; font-weight:bold; color:#f8fafc;">{name}</td>
          <td style="padding:6px; color:#94a3b8;">{dist}</td>
          <td style="padding:6px; color:#22c55e;">{lmw}</td>
          <td style="padding:6px; color:#facc15;">{gmw}</td>
          <td style="padding:6px; color:{dmw_color}; font-weight:bold;">{dmw}</td>
          <td style="padding:6px; color:{b_color}; font-weight:bold; font-size:11px;">{bneck}</td>
          <td style="padding:6px; color:#a855f7;">{evac}</td>
          <td style="padding:6px; color:#94a3b8;">{tariff}</td>
          <td style="padding:6px; font-weight:bold; color:#22c55e;">{mu}</td>
          <td style="padding:6px;">{pb}</td>
          <td style="padding:6px; font-weight:bold; color:#38bdf8;">{sc}</td>
        </tr>
"""
benchmark_html += """      </tbody>
    </table>
  </div>
"""

# Helper to render table from dataframe
def render_table(df, title, title_color, badge_text):
    html = f"""  <div style="background: #1e293b; padding: 1.25rem; border-radius: 0.75rem; border: 1px solid #334155; margin-bottom: 2rem; overflow-x: auto;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
      <h3 style="margin:0; color:{title_color}; font-size: 1.15rem;">{title}</h3>
      <span style="background:#0f172a; color:#38bdf8; padding:3px 10px; border-radius:4px; font-size:11px; border:1px solid #334155;">{badge_text}</span>
    </div>
    <table style="width:100%; border-collapse:collapse; font-size:11.5px; text-align:left;">
      <thead>
        <tr style="border-bottom:2px solid #334155; color:#94a3b8;">
          <th style="padding:6px;">Rank</th>
          <th style="padding:6px;">Substation</th>
          <th style="padding:6px;">District</th>
          <th style="padding:6px;">Voltage</th>
          <th style="padding:6px;">Land MW</th>
          <th style="padding:6px;">Grid MW</th>
          <th style="padding:6px;">Deploy MW</th>
          <th style="padding:6px;">Evacuation &amp; Bays</th>
          <th style="padding:6px;">Tariff</th>
          <th style="padding:6px;">Annual MU</th>
          <th style="padding:6px;">CAPEX (₹ Cr)</th>
          <th style="padding:6px;">Gross Rev (₹ Cr/yr)</th>
          <th style="padding:6px;">Payback</th>
          <th style="padding:6px;">Score</th>
        </tr>
      </thead>
      <tbody>
"""
    for idx, row in df.iterrows():
        rank = idx + 1 if 'master_rank' not in row else row['master_rank']
        b_color = "#facc15" if "GRID" in str(row['active_bottleneck']) else "#38bdf8"
        html += f"""        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:5px;">#{rank}</td>
          <td style="padding:5px;"><b>{row['substation_name']}</b></td>
          <td style="padding:5px; color:#94a3b8;">{row['district']}</td>
          <td style="padding:5px;">{row['voltage_level']}</td>
          <td style="padding:5px; color:#22c55e;">{row['land_solar_mw']:.1f} MW</td>
          <td style="padding:5px; color:#facc15;">{row['grid_spare_mw']:.1f} MW</td>
          <td style="padding:5px; color:#38bdf8; font-weight:bold;">{row['deployable_solar_mw']:.1f} MW</td>
          <td style="padding:5px; color:#a855f7;">{row['deployable_current_amps']:.1f}A @ {row['evacuation_voltage_kv']}kV ({row['required_feeder_bays']} bays)</td>
          <td style="padding:5px;">₹{row['tariff_inr_per_kwh']:.2f}</td>
          <td style="padding:5px; color:#22c55e; font-weight:bold;">{row['deployable_annual_mu']:.2f} MU</td>
          <td style="padding:5px;">₹{row['turnkey_capex_cr']:.1f} Cr</td>
          <td style="padding:5px; color:#22c55e;">₹{row['annual_gross_revenue_cr']:.2f} Cr</td>
          <td style="padding:5px;">{row['simple_payback_years']:.2f} y</td>
          <td style="padding:5px; color:#38bdf8; font-weight:bold;">{row['suryagrid_master_score']:.1f}</td>
        </tr>
"""
    html += """      </tbody>
    </table>
  </div>
"""
    return html

eht_html = render_table(df_eht, "Top 20 Utility-Scale EHT Substations (220 kV / 400 kV)", "#f59e0b", "Utility STU Tariff: ₹2.75/kWh | 132/220 kV Line Bays")
kusum_html = render_table(df_kusum, "Top 20 Decentralized PM-KUSUM Substations (132 kV / 33 kV)", "#22c55e", "PM-KUSUM Tariff: ₹3.13/kWh | 33 kV VCB Feeder Bays")
golden_html = render_table(df_golden, "Top 20 Overall Golden Substations (Statewide Master Leaderboard)", "#38bdf8", "Calibrated 150 MW Cap | Multi-Criteria Master Score")

# Combine all new middle content
new_middle = summary_cards_html + benchmark_html + eht_html + kusum_html + golden_html

# Read existing HTML
html_path = 'reports/earth_engine_report.html'
with open(html_path, 'r', encoding='utf-8') as f:
    full_html = f.read()

# Replace from `<div class="grid" style="margin-top: -0.75rem;">` up to `<h2 style="color: #38bdf8; font-size: 1.3rem;">Interactive Spatial Verification Map (Telangana)</h2>`
start_marker = '<div class="grid" style="margin-top: -0.75rem;">'
end_marker = '<h2 style="color: #38bdf8; font-size: 1.3rem;">Interactive Spatial Verification Map (Telangana)</h2>'

idx_start = full_html.find(start_marker)
idx_end = full_html.find(end_marker)

if idx_start == -1 or idx_end == -1:
    print(f"Error: Markers not found. start={idx_start}, end={idx_end}")
    exit(1)

updated_html = full_html[:idx_start] + new_middle + "\n  " + full_html[idx_end:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(updated_html)

print(f"✅ Successfully updated {html_path} ({len(updated_html):,} bytes)")
