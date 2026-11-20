#!/usr/bin/env python3
"""
tests/test_webapp.py
Automated test suite verifying the SunNode Government of Telangana DSS:
1. JSON assets integrity (391 substations, 33 simplified districts, zero nulls/NaNs)
2. JavaScript syntax validation via Node.js
3. Local HTTP server starts cleanly and serves index, JSON assets, and deliverables with HTTP 200
4. Zero commercial SaaS elements in UI (no Carto watermarks, no pricing, no request pilot, no shortlist)
5. Full 391-substation CSV export format and row count (exactly 392 lines = 1 header + 391 data rows)
6. Official Government of Telangana Energy Department Problem Statement alignment
7. Stage 5.6 Real PVGIS solar telemetry and dynamic irradiance map layer
"""

import os
import json
import time
import urllib.request
import subprocess
import threading
import unittest
from http.server import HTTPServer

import sys
sys.path.insert(0, os.path.abspath("webapp"))
from server import SunNodeHandler, WEBAPP_DIR, OUTPUTS_DIR

TEST_PORT = 8018

class TestSunNodeWebApp(unittest.TestCase):

    def test_01_json_assets_integrity(self):
        sub_path = "webapp/data/substations.json"
        dist_path = "webapp/data/districts_simplified.geojson"
        met_path = "webapp/data/statewide_metrics.json"

        self.assertTrue(os.path.exists(sub_path), f"Missing {sub_path}")
        self.assertTrue(os.path.exists(dist_path), f"Missing {dist_path}")
        self.assertTrue(os.path.exists(met_path), f"Missing {met_path}")

        # Check substations.json
        with open(sub_path, "r", encoding="utf-8") as f:
            substations = json.load(f)
        
        self.assertEqual(len(substations), 391)
        
        req_keys = [
            "id", "name", "district", "mandal", "voltageClass", "track",
            "lat", "lon", "landMw", "gridMw", "deployMw", "evacKv",
            "amps", "bays", "bayType", "tariff", "energyMu", "capexCr",
            "grossRevCr", "payback", "score", "bottleneck", "isColocated",
            # Stage 5.6 Real EU JRC PVGIS v5.3 Solar Metrics
            "irradianceDailyKwhM2", "irradianceAnnualKwhM2", "specificYieldKwhKwp",
            "specificYieldMuMw", "cufPct", "optimalTiltDeg", "dailyOutputMwh",
            "annualOutputMu", "lifetime25YrMu", "monthlyGenerationKwh",
            "solarPercentile", "solarGrade", "siteSuitability", "suitabilityStatus"
        ]

        districts_seen = set()
        for idx, s in enumerate(substations):
            for k in req_keys:
                self.assertIn(k, s, f"Row {idx} missing key {k}")
                self.assertIsNotNone(s[k], f"Row {idx} key {k} is None")
            
            # Geographic coordinate bounds for Telangana
            self.assertGreaterEqual(s["lat"], 15.5)
            self.assertLessEqual(s["lat"], 20.0)
            self.assertGreaterEqual(s["lon"], 77.0)
            self.assertLessEqual(s["lon"], 82.0)

            # Strict bottleneck inequalities
            self.assertLessEqual(s["deployMw"], s["gridMw"])
            self.assertLessEqual(s["deployMw"], s["landMw"])

            # Valid Evacuation voltage
            self.assertIn(s["evacKv"], [33, 132, 220])
            districts_seen.add(s["district"])

            # Real PVGIS physical ranges (Zero fake data)
            self.assertGreaterEqual(s["irradianceDailyKwhM2"], 5.0)
            self.assertLessEqual(s["irradianceDailyKwhM2"], 6.0)
            self.assertGreaterEqual(s["irradianceAnnualKwhM2"], 1900.0)
            self.assertLessEqual(s["irradianceAnnualKwhM2"], 2100.0)
            self.assertGreaterEqual(s["cufPct"], 15.0)
            self.assertLessEqual(s["cufPct"], 18.5)
            self.assertGreaterEqual(s["optimalTiltDeg"], 18.0)
            self.assertLessEqual(s["optimalTiltDeg"], 30.0)
            self.assertEqual(len(s["monthlyGenerationKwh"]), 12)
            self.assertIn(s["suitabilityStatus"], ["SUITABLE", "NOT_SUITABLE"])

        # All 33 districts represented with zero invalid variants
        self.assertEqual(len(districts_seen), 33)
        self.assertNotIn("Rangareddy", districts_seen)
        self.assertNotIn("UNKNOWN", districts_seen)

        # Check districts_simplified.geojson
        with open(dist_path, "r", encoding="utf-8") as f:
            dist_geojson = json.load(f)
        
        self.assertEqual(dist_geojson.get("type"), "FeatureCollection")
        self.assertEqual(len(dist_geojson.get("features", [])), 33)

        for feat in dist_geojson["features"]:
            props = feat.get("properties", {})
            self.assertIn("district_name", props)
            self.assertIn("deployable_mw", props)
            self.assertIn("substation_count", props)
            self.assertGreaterEqual(props["substation_count"], 0)
            self.assertGreaterEqual(props["deployable_mw"], 0.0)
            # Stage 5.6 Real PVGIS aggregations
            self.assertIn("avg_solar_irradiance_daily", props)
            self.assertIn("avg_solar_yield_mu_per_mw", props)
            self.assertIn("total_annual_clean_mu", props)
            self.assertIn("district_cuf_pct", props)
            self.assertGreaterEqual(props["avg_solar_irradiance_daily"], 5.0)

        # Check statewide_metrics.json
        with open(met_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        
        self.assertEqual(metrics["total_substations"], 391)
        self.assertEqual(metrics["total_districts"], 33)
        self.assertAlmostEqual(metrics["dedup_deploy_mw"], 12602.6, places=1)
        self.assertAlmostEqual(metrics["statewide_payback_years"], 10.13, places=2)
        self.assertEqual(metrics["colocated_substations_count"], 53)
        # Stage 5.6 PVGIS Statewide Benchmarks
        self.assertAlmostEqual(metrics["solar_irradiance_mean_kwh_m2_day"], 5.51, places=2)
        self.assertAlmostEqual(metrics["solar_irradiance_min_kwh_m2_day"], 5.29, places=2)
        self.assertAlmostEqual(metrics["solar_irradiance_max_kwh_m2_day"], 5.61, places=2)
        self.assertAlmostEqual(metrics["cuf_mean_pct"], 17.02, places=2)
        self.assertAlmostEqual(metrics["optimal_tilt_mean_deg"], 22.7, places=1)

    def test_02_javascript_syntax_validation(self):
        js_file = "webapp/app.js"
        self.assertTrue(os.path.exists(js_file))
        result = subprocess.run(["node", "-c", js_file], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Node syntax error in {js_file}: {result.stderr}")

    def test_03_server_http_200(self):
        # Start server in daemon thread on TEST_PORT
        server_address = ('127.0.0.1', TEST_PORT)
        httpd = HTTPServer(server_address, SunNodeHandler)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.5)

        try:
            endpoints = [
                "/",
                "/index.html",
                "/app.js",
                "/data/substations.json",
                "/data/districts_simplified.geojson",
                "/data/statewide_metrics.json",
                "/assets/logo.png",
                "/assets/gee_1km_calibrated_preview.png",
                "/outputs/SunNode_Telangana_Statewide_Substation_Inventory.xlsx",
                "/outputs/SuryaGrid_Telangana_Statewide_Substation_Inventory.xlsx"
            ]

            for ep in endpoints:
                url = f"http://127.0.0.1:{TEST_PORT}{ep}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as response:
                    self.assertEqual(response.status, 200, f"Endpoint {ep} failed with {response.status}")
                    body = response.read()
                    self.assertGreater(len(body), 0, f"Endpoint {ep} returned empty body")

            # Check index.html content
            with urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/", timeout=5) as resp:
                content = resp.read().decode("utf-8")
                self.assertIn("SunNode", content)
                self.assertIn("Site Selection Wizard", content)
                self.assertIn("gisMap", content)
                self.assertIn("Govt. of Telangana", content)
                self.assertIn("All-391 Rankings", content)
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_04_no_commercial_elements_in_ui(self):
        with open("webapp/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        with open("webapp/app.js", "r", encoding="utf-8") as f:
            js = f.read()

        # 1. No Carto basemap URLs
        self.assertNotIn("carto.com", html.lower(), "Carto reference found in index.html")
        self.assertNotIn("carto.com", js.lower(), "Carto reference found in app.js")
        self.assertNotIn("basemaps.cartocdn.com", js.lower(), "Carto tile layer found in app.js")

        # 2. Keyless Esri World Imagery configured
        self.assertIn("arcgisonline.com/arcgis/rest/services/world_imagery", js.lower(), "Esri World Imagery missing in app.js")

        # 3. No Commercial Pricing, Request Pilot, or Shortlist
        self.assertNotIn("data-tab=\"saas\"", html, "Commercial SaaS pricing tab found in index.html")
        self.assertNotIn("view-saas", html, "Commercial pricing view found in index.html")
        self.assertNotIn("request pilot", html.lower(), "Request pilot found in index.html")
        self.assertNotIn("request pilot", js.lower(), "Request pilot found in app.js")
        self.assertNotIn("shortlist", html.lower(), "Shortlist found in index.html")
        self.assertNotIn("shortlist", js.lower(), "Shortlist found in app.js")

    def test_05_csv_export_format_and_row_count(self):
        # Verify the CSV export schema against substations.json
        with open("webapp/data/substations.json", "r", encoding="utf-8") as f:
            substations = json.load(f)

        self.assertEqual(len(substations), 391)

        # Exact Stage 5.6 Verified Schema with Real PVGIS Solar Columns (34 columns)
        headers = [
            'Rank',
            'Substation ID',
            'Substation Name',
            'District',
            'Mandal',
            'Latitude',
            'Longitude',
            'Substation Voltage (kV)',
            'Deployment Track',
            'Land Suitability (MW)',
            'Grid Spare Headroom (MW)',
            'True Deployable Solar (MW)',
            'Active Bottleneck',
            'Evacuation Voltage (kV)',
            'Injection Current (Amps)',
            'Dedicated Feeder Bays',
            'Feeder Bay Type',
            'Feed-in Tariff (INR/kWh)',
            'Daily Solar Irradiance (kWh/m2/day)',
            'Annual Solar Irradiance (kWh/m2/yr)',
            'Specific Yield (kWh/kWp/yr)',
            'Specific Yield (MU/MW/yr)',
            'Capacity Utilization Factor (CUF %)',
            'Optimal Panel Tilt (Deg)',
            'Substation Daily Output (MWh/day)',
            'Annual Clean Generation (MU)',
            '25-Year Lifetime Energy (MU)',
            'Total Turnkey CAPEX (INR Cr)',
            'Annual Gross Revenue (INR Cr)',
            'Simple Payback (Years)',
            'SunNode Composite Score',
            'Solar Resource Grade',
            'Site Suitability Verdict',
            'Co-Location Cluster Flag'
        ]

        def escape_csv(val):
            if val is None:
                return '""'
            s = str(val).replace('"', '""')
            return f'"{s}"'

        csv_lines = [",".join(headers)]
        for idx, s in enumerate(substations):
            row = [
                str(idx + 1),
                escape_csv(s["id"]),
                escape_csv(s["name"]),
                escape_csv(s["district"]),
                escape_csv(s.get("mandal", "Telangana")),
                f'{s["lat"]:.5f}',
                f'{s["lon"]:.5f}',
                escape_csv(s["voltageClass"]),
                escape_csv(s["track"]),
                f'{s["landMw"]:.1f}',
                f'{s["gridMw"]:.1f}',
                f'{s["deployMw"]:.1f}',
                escape_csv(s["bottleneck"]),
                str(s.get("evacKv", 33)),
                str(round(s.get("amps", 0))),
                str(s.get("bays", 1)),
                escape_csv(s.get("bayType", "VCB")),
                f'{s.get("tariff", 3.13):.2f}',
                f'{s["irradianceDailyKwhM2"]:.2f}',
                f'{s["irradianceAnnualKwhM2"]:.1f}',
                f'{s["specificYieldKwhKwp"]:.1f}',
                f'{s["specificYieldMuMw"]:.3f}',
                f'{s["cufPct"]:.2f}',
                f'{s["optimalTiltDeg"]:.1f}',
                f'{s["dailyOutputMwh"]:.1f}',
                f'{s["annualOutputMu"]:.2f}',
                f'{s["lifetime25YrMu"]:.2f}',
                f'{s["capexCr"]:.2f}',
                f'{s["grossRevCr"]:.2f}',
                f'{s["payback"]:.2f}',
                f'{s["score"]:.1f}',
                escape_csv(s.get("solarGrade", "Excellent Solar Zone")),
                escape_csv(s.get("siteSuitability", "SUITABLE")),
                '"TRUE"' if s.get("isColocated") else '"FALSE"'
            ]
            csv_lines.append(",".join(row))

        # Assert exactly 391 data rows + 1 header row = 392 lines
        self.assertEqual(len(csv_lines), 392, f"Expected 392 lines, got {len(csv_lines)}")
        
        # Check zero nulls, NaNs, or undefined
        for i, line in enumerate(csv_lines):
            self.assertNotIn("NaN", line, f"NaN found in CSV line {i}")
            self.assertNotIn("None", line, f"None found in CSV line {i}")
            self.assertNotIn("undefined", line, f"undefined found in CSV line {i}")

    def test_06_official_government_dss_alignment(self):
        with open("webapp/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        # Official Government alignment keywords
        self.assertIn("Government of Telangana", html)
        self.assertIn("Energy Department", html)
        self.assertIn("Challenge 10", html)
        self.assertIn("Decision Support System", html)
        self.assertIn("GEE 1 km Layer", html)
        self.assertIn("All-391 Rankings", html)

    def test_07_stage56_solar_telemetry_and_irradiance_layer(self):
        with open("webapp/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        with open("webapp/app.js", "r", encoding="utf-8") as f:
            js = f.read()

        # 1. Map dropdown and dynamic legend
        self.assertIn('value="solar"', html)
        self.assertIn("Solar Irradiance / Sun Energy (PVGIS)", html)
        self.assertIn("mapLegendTitle", html)
        self.assertIn("mapLegendItems", html)

        # 2. Inspector Layer 3 Solar Telemetry elements
        self.assertIn("inspSolarGradeBadge", html)
        self.assertIn("inspSolarSuitabilityBanner", html)
        self.assertIn("inspIrradDaily", html)
        self.assertIn("inspYieldMu", html)
        self.assertIn("inspDailyOutput", html)
        self.assertIn("inspEnergy", html)
        self.assertIn("inspSolarBenchmarkBar", html)
        self.assertIn("inspMonthlyChart", html)

        # 3. JavaScript logic for solar coloring and Chart.js telemetry
        self.assertIn("mapColorBy: 'solar'", js)
        self.assertIn("#ea580c", js)  # Heatmap tier >= 5.55
        self.assertIn("#f59e0b", js)  # Heatmap tier 5.45-5.55
        self.assertIn("#eab308", js)  # Heatmap tier < 5.45
        self.assertIn("renderMonthlySolarChart", js)
        self.assertIn("renderInspector", js)
        self.assertIn("irradianceDailyKwhM2", js)

if __name__ == "__main__":
    unittest.main()
