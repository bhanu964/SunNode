# SunNode — Telangana Solar Substation Potential Assessment
## Government of Telangana Energy Department · Challenge 10 Decision Support System (DSS)

**SunNode** is an end-to-end geospatial intelligence and techno-economic Decision Support System (DSS) developed for the **Government of Telangana Energy Department (Challenge 10)**. It identifies, evaluates, and ranks electrical substations across all 33 Telangana districts for ground-mounted solar power deployment (Utility-Scale EHT & PM-KUSUM Component-A).

---

## ☀️ System Capabilities

1. **Google Earth Engine (GEE) 1 km Calibrated Land Suitability Engine:**
   - 10 m resolution Sentinel Dynamic World V1 12-month mode composite + USGS SRTM 30 m slope.
   - 3-tier operational classification: Green (Primary Usable Farmland / Bare / Scrub, slope $\le 5^\circ$), Yellow (Conditional Canopy/Orchards), Red (Excluded Urban/Built-up + 30 m water body FTL buffer).
   - Contiguous patch opening ($\ge 4$ acres / ~16,187 m²) isolating solar-buildable core areas.

2. **Official DISCOM / TGRAC Grid Capacity Integration:**
   - Evaluates transformer MVA ratings and official spare capacity headroom across all 391 substations.
   - Computes strict bottleneck matching: $\text{Deployable MW} = \min(\text{Land MW}, \text{Grid Spare MW})$.
   - 33 kV, 132 kV, and 220 kV AC injection current (Amps) and dedicated feeder bay requirements.

3. **100% Real EU JRC PVGIS v5.3 Solar Generation Telemetry:**
   - Direct location-specific queries for all 391 substations (zero synthetic or estimated data).
   - Real global horizontal irradiation ($GHI$), plane-of-array irradiance ($H_i$), specific yield ($kWh/kWp/yr$), capacity utilization factor ($CUF\%$), optimal panel tilt, and 12-month Jan–Dec generation curves.

4. **Multi-Criteria Ranking & Techno-Economic Financial Modeling:**
   - Levelized feed-in tariff modeling (Utility-Scale STU at ₹2.75/kWh; PM-KUSUM Feeder at ₹3.13/kWh).
   - Turnkey EPC CAPEX (₹3.75 Cr/MW), annual gross revenue, EBITDA, simple payback, and 25-year net profit.
   - De-duplicated statewide totals accounting for co-located yards within 2 km.

5. **Production Web Application (DSS):**
   - Interactive GIS Leaflet map with satellite imagery, 23-sheet master Excel export, 300 DPI cartographic PDF atlas, and Google Earth 3D KMZ packages.

---

## 📊 Key Statewide Findings (Telangana)

| Metric | Statewide Value | Description |
| :--- | :--- | :--- |
| **Analyzed Substations** | **391** | Official TGRAC & TGTRANSCO grid nodes |
| **Revenue Districts** | **33 / 33** | 100% statewide geographic coverage |
| **Deduplicated Deployable Solar** | **12,602.6 MW** | True bottleneck-limited buildable solar |
| **Annual Clean Generation** | **18,771.6 MU/yr** | 18.77 Billion kWh clean electricity |
| **Annual Landowner Lease Income** | **₹252.05 Cr/yr** | Paid directly to rural agricultural landholders |
| **Annual CO₂ Abatement** | **13.65 Million Tonnes** | Avoided coal-fired thermal emissions |
| **Mean Daily Solar Irradiance** | **5.51 kWh/m²/day** | Real EU JRC PVGIS v5.3 satellite observation |
| **Mean Specific Solar Yield** | **1,491.2 kWh/kWp/yr** | 1.49 MU/MW/yr clean generation rate |
| **Statewide Average Payback** | **10.13 Years** | Turnkey CAPEX payback at regulated tariffs |

---

## 🚀 Running the Local Decision Support System (DSS)

```bash
# 1. Clone repository
git clone https://github.com/bhanu964/SunNode.git
cd SunNode

# 2. Launch production web application
./run_webapp.sh
# Server opens at http://localhost:8000 (or auto-assigned free port 8001+)
```

---

## 🧪 Verification & Automated Testing

Run the full automated test suite verifying data integrity, zero nulls/NaNs, server endpoints, and PVGIS telemetry:

```bash
python3 -m unittest discover -s tests
# Ran 16 tests — OK (100% Passing)
```

---

## 🏛️ Government Alignment & Submission Deliverables

- **Challenge:** Challenge 10 — Solar Substation Potential Assessment
- **Authority:** Energy Department, Government of Telangana
- **Master Excel Inventory:** `outputs/SunNode_Telangana_Statewide_Substation_Inventory.xlsx`
- **Cartographic Map Atlas:** `outputs/SunNode_Telangana_Substations_Map_Atlas.pdf`
- **Google Earth 3D Package:** `outputs/SunNode_Telangana_Substations_Offline.kmz`
