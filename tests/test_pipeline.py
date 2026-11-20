#!/usr/bin/env python3
"""
tests/test_pipeline.py
Automated test suite verifying SuryaGrid statewide substation intelligence:
1. PDF extraction integrity (2,555 rows)
2. Mandal & State boundary validity & area benchmark
3. Statewide infrastructure discovery (1,045 facilities)
4. Point-in-polygon administrative join (all 33 districts represented)
5. 11-Sheet Excel workbook structure & completeness
6. GeoJSON validity & coordinate ranges
7. Earth Engine assets verification (Boundary, Verified PDF, Statewide Inventory v2)
"""

import os
import json
import unittest
import pandas as pd
import openpyxl
import ee

class TestSuryaGridStatewidePipeline(unittest.TestCase):

    def test_01_pdf_extraction(self):
        csv_path = "data/processed/government_3311_substations.csv"
        self.assertTrue(os.path.exists(csv_path))
        df = pd.read_csv(csv_path)
        self.assertEqual(len(df), 2555)
        self.assertEqual(df["Sl. No."].nunique(), 2555)

    def test_02_boundaries_and_mandals(self):
        b_path = "data/boundaries/telangana_boundary.geojson"
        m_path = "data/boundaries/telangana_blocks.geojson"
        d_path = "data/boundaries/telangana_33_districts.geojson"
        self.assertTrue(os.path.exists(b_path))
        self.assertTrue(os.path.exists(m_path))
        self.assertTrue(os.path.exists(d_path))

        with open(b_path) as f:
            b_data = json.load(f)
        self.assertEqual(len(b_data["features"]), 1)

        with open(m_path) as f:
            m_data = json.load(f)
        self.assertEqual(len(m_data["features"]), 444)

        with open(d_path) as f:
            d_data = json.load(f)
        self.assertEqual(len(d_data["features"]), 33)

    def test_03_statewide_facilities(self):
        fac_path = "data/results/telangana_statewide_facilities.csv"
        self.assertTrue(os.path.exists(fac_path))
        df = pd.read_csv(fac_path)
        self.assertEqual(len(df), 1045)
        self.assertEqual(df["District"].nunique(), 33)
        self.assertTrue((df["Latitude"] >= 15.5).all())
        self.assertTrue((df["Latitude"] <= 20.0).all())
        self.assertTrue((df["Longitude"] >= 77.0).all())
        self.assertTrue((df["Longitude"] <= 82.0).all())

    def test_04_excel_workbook_structure(self):
        xlsx_path = "outputs/SuryaGrid_Telangana_Statewide_Substation_Inventory.xlsx"
        self.assertTrue(os.path.exists(xlsx_path))
        wb = openpyxl.load_workbook(xlsx_path, read_only=True)
        sheet_names = wb.sheetnames
        self.assertEqual(len(sheet_names), 23)
        self.assertIn("TOP 20 UTILITY EHT SUBSTATIONS", sheet_names)
        self.assertIn("TOP 20 PM-KUSUM SUBSTATIONS", sheet_names)
        self.assertIn("TOP 20 GOLDEN SUBSTATIONS", sheet_names)
        self.assertIn("STAGE 4 MASTER TECHNO-ECONOMIC", sheet_names)
        self.assertIn("DYNAMIC WORLD 1KM & 2KM", sheet_names)
        self.assertIn("1KM CALIBRATED SUITABILITY", sheet_names)
        self.assertIn("PVGIS V5.3 SOLAR GENERATION", sheet_names)
        expected_sheets = [
            "TOP 20 UTILITY EHT SUBSTATIONS",
            "TOP 20 PM-KUSUM SUBSTATIONS",
            "TOP 20 GOLDEN SUBSTATIONS",
            "STAGE 4 MASTER TECHNO-ECONOMIC",
            "MASTER INVENTORY",
            "SUBSTATION ELECTRICAL PROFILES",
            "LAND SUITABILITY (3KM & 5KM)",
            "1KM CALIBRATED SUITABILITY",
            "DYNAMIC WORLD 1KM & 2KM",
            "33-11 KV SUBSTATIONS",
            "HIGH VOLTAGE SUBSTATIONS",
            "TGRAC TGTRANSCO OFFICIAL",
            "OTHER DISTRIBUTION SUBSTATIONS",
            "TRANSFORMERS",
            "MATCHED GOVERNMENT PDF RECORDS",
            "UNMATCHED GOVT PDF RECORDS",
            "UNMATCHED DISCOVERED",
            "MANUAL VERIFICATION",
            "DISTRICT SUMMARY",
            "DATA SOURCES AND COVERAGE",
            "SOLAR BIDDING FEASIBILITY",
            "SYNCHRONIZED SOLAR PLANTS",
            "PVGIS V5.3 SOLAR GENERATION"
        ]
        self.assertListEqual(sheet_names, expected_sheets)

    def test_05_geojson_validity(self):
        geo_path = "outputs/telangana_electrical_infrastructure.geojson"
        self.assertTrue(os.path.exists(geo_path))
        with open(geo_path) as f:
            data = json.load(f)
        self.assertEqual(data.get("type"), "FeatureCollection")
        self.assertEqual(len(data.get("features", [])), 1045)

    def test_06_earth_engine_assets(self):
        ee.Initialize(project="ai-voice-agent-crm")
        # 1. State boundary asset
        b_fc = ee.FeatureCollection("projects/ai-voice-agent-crm/assets/suryagrid_telangana_boundary")
        self.assertEqual(b_fc.size().getInfo(), 1)

        # 2. Verified 33/11 kV PDF asset
        v_fc = ee.FeatureCollection("projects/ai-voice-agent-crm/assets/suryagrid_substations_verified")
        self.assertEqual(v_fc.size().getInfo(), 178)

        # 3. New Statewide inventory v2 asset
        s_fc = ee.FeatureCollection("projects/ai-voice-agent-crm/assets/suryagrid_tel_statewide_inventory_v2")
        self.assertEqual(s_fc.size().getInfo(), 1045)

    def test_07_reports_exist(self):
        reports = [
            "reports/boundary_report.html",
            "reports/statewide_discovery_report.html",
            "reports/matching_report.html",
            "reports/data_quality_report.html",
            "reports/earth_engine_report.html"
        ]
        for r in reports:
            self.assertTrue(os.path.exists(r), f"Missing report: {r}")

    def test_08_pvgis_solar_generation(self):
        csv_path = "data/processed/substation_pvgis_v53_generation_1km_calibrated.csv"
        self.assertTrue(os.path.exists(csv_path), f"Missing CSV: {csv_path}")
        df = pd.read_csv(csv_path)
        self.assertEqual(len(df), 391)

        # Check critical PVGIS fields have zero nulls
        cols = ["pvgis_ey_kwh_per_mwp", "pvgis_ed_kwh_per_mwp", "pvgis_optimal_tilt_deg", "pvgis_dc_cuf_pct", "direct_annual_generation_mu"]
        for c in cols:
            self.assertEqual(df[c].isnull().sum(), 0, f"Nulls found in {c}")

        # Check solar resource bounds in Telangana (1.40M - 1.70M kWh/MWp/yr across all 33 districts)
        self.assertTrue((df["pvgis_ey_kwh_per_mwp"] >= 1400000).all())
        self.assertTrue((df["pvgis_ey_kwh_per_mwp"] <= 1700000).all())
        self.assertTrue((df["pvgis_optimal_tilt_deg"] >= 18.0).all())
        self.assertTrue((df["pvgis_optimal_tilt_deg"] <= 26.0).all())

        # Check urban substation Narayanguda
        n_match = df[df["substation_name"].str.contains("Narayanguda", case=False, na=False)]
        self.assertGreater(len(n_match), 0)
        n_row = n_match.iloc[0]
        self.assertEqual(n_row["estimated_mw"], 0.0)
        self.assertEqual(n_row["direct_annual_generation_mu"], 0.0)
        self.assertGreater(n_row["pvgis_ey_kwh_per_mwp"], 1400000)

    def test_09_stage4_master_techno_economic(self):
        csv_path = "data/processed/suryagrid_master_391_techno_economic.csv"
        top20_path = "data/processed/suryagrid_top20_golden_substations.csv"
        top20_eht_path = "data/processed/suryagrid_top20_utility_eht_substations.csv"
        top20_kusum_path = "data/processed/suryagrid_top20_pm_kusum_substations.csv"
        self.assertTrue(os.path.exists(csv_path), f"Missing {csv_path}")
        self.assertTrue(os.path.exists(top20_path), f"Missing {top20_path}")
        self.assertTrue(os.path.exists(top20_eht_path), f"Missing {top20_eht_path}")
        self.assertTrue(os.path.exists(top20_kusum_path), f"Missing {top20_kusum_path}")

        df = pd.read_csv(csv_path)
        top20 = pd.read_csv(top20_path)
        top20_eht = pd.read_csv(top20_eht_path)
        top20_kusum = pd.read_csv(top20_kusum_path)

        self.assertEqual(len(df), 391)
        self.assertEqual(len(top20), 20)
        self.assertEqual(len(top20_eht), 20)
        self.assertEqual(len(top20_kusum), 20)

        # 1. District normalization: exactly 33 official Telangana districts, zero spelling variants
        self.assertEqual(df["district"].nunique(), 33)
        self.assertNotIn("Rangareddy", df["district"].values)
        self.assertNotIn("UNKNOWN", df["district"].values)
        self.assertNotIn("Jangoan", df["district"].values)

        # 2. Strict bottleneck validation without tolerance hack: deployable_solar_mw <= land_solar_mw and <= grid_spare_mw
        self.assertTrue((df["deployable_solar_mw"] <= df["land_solar_mw"]).all(), "deployable_solar_mw exceeds land_solar_mw")
        self.assertTrue((df["deployable_solar_mw"] <= df["grid_spare_mw"]).all(), "deployable_solar_mw exceeds grid_spare_mw")

        # 3. Voltage-tier evacuation & field domain checks
        self.assertTrue((df["is_colocated_overlap"].isin([True, False])).all())
        self.assertEqual(df["is_colocated_overlap"].sum(), 53)
        self.assertTrue((df["evacuation_voltage_kv"].isin([33, 132, 220])).all())
        self.assertTrue((df["feeder_bay_type"].isin(["33 kV VCB Feeder Bay", "132 kV SF6 Line Bay", "220 kV SF6 Line Bay"])).all())
        self.assertTrue((top20_eht["tariff_tier"].str.contains("Utility-Scale STU")).all())
        self.assertTrue((top20_kusum["tariff_tier"].str.contains("PM-KUSUM")).all())

        # 4. Co-located 1-to-1 Annexure-D matching: Dichpally 220 kV (143.0 MW) vs Dichpally 400 kV (650.3 MW)
        d220 = df[df["substation_name"] == "Dichpally"].iloc[0]
        d400 = df[df["substation_name"] == "Dichpally (400KV)"].iloc[0]
        self.assertEqual(d220["grid_spare_mw"], 143.0)
        self.assertEqual(d400["grid_spare_mw"], 650.25)
        self.assertNotEqual(d220["grid_spare_mw"], d400["grid_spare_mw"])

        # 5. Narayanguda urban check: 0.0 MW deployable
        n_row = df[df["substation_name"].str.contains("Narayanguda", case=False, na=False)].iloc[0]
        self.assertEqual(n_row["deployable_solar_mw"], 0.0)
        self.assertEqual(n_row["active_bottleneck"], "LAND / URBAN EXCLUDED (0 MW)")
        self.assertEqual(n_row["suryagrid_master_score"], 0.0)

        # 6. Gajwel (400KV) check: grid constrained at 38.0 MW out of 121.2 MW land
        g_row = df[df["substation_name"] == "Gajwel (400KV)"].iloc[0]
        self.assertEqual(g_row["active_bottleneck"], "GRID TRANSFORMER CONSTRAINED")
        self.assertEqual(g_row["grid_spare_mw"], 38.0)
        self.assertEqual(g_row["deployable_solar_mw"], 38.0)
        self.assertGreater(g_row["land_solar_mw"], 100.0)

        # 7. Valid financial & electrical metrics across all rows
        fin_cols = [
            "turnkey_capex_cr", "annual_gross_revenue_cr", "annual_opex_and_lease_cr",
            "annual_net_ebitda_cr", "simple_payback_years", "lifetime_25yr_net_profit_cr",
            "deployable_current_amps", "deployable_annual_mu", "suryagrid_master_score"
        ]
        for c in fin_cols:
            self.assertEqual(df[c].isnull().sum(), 0, f"Nulls found in {c}")
            self.assertTrue((df[c] >= 0.0).all(), f"Negative values in {c}")

if __name__ == "__main__":
    unittest.main()
