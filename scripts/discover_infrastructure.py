#!/usr/bin/env python3
"""
scripts/discover_infrastructure.py
Main statewide infrastructure discovery and synthesis engine:
1. Loads all public electrical infrastructure features across Telangana.
2. Applies strict voltage parsing and infrastructure categorization.
3. Performs point-in-polygon spatial join with official 33 districts and mandals.
4. Matches against 2,555 government PDF substation records.
5. Preserves all candidates without inventing missing fields.
Outputs:
- data/results/telangana_statewide_facilities.csv
- data/candidates/discovered_candidates_master.csv
"""

import os
import sys
import json
import logging
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from classify_voltage import classify_facility, parse_voltage_string
from administrative_matching import perform_administrative_join
from match_government_records import match_facility_to_pdf
from validate_coordinates import is_valid_coordinate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/discover_infrastructure.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("discover_infrastructure")

def build_statewide_inventory():
    logger.info("Starting statewide electrical infrastructure inventory build...")

    # Load candidates discovered across Telangana
    cands_path = "data/results/geocoding_candidates.csv"
    if not os.path.exists(cands_path):
        logger.error(f"Missing {cands_path}")
        sys.exit(1)

    df_cands = pd.read_csv(cands_path)
    logger.info(f"Loaded {len(df_cands)} raw discovered candidates from {cands_path}")

    # Load government PDF dataset for matching
    pdf_aliases_path = "data/processed/substation_aliases.csv"
    df_pdf = pd.read_csv(pdf_aliases_path)
    logger.info(f"Loaded {len(df_pdf)} government PDF substation records for cross-referencing.")

    # Convert candidates to GeoDataFrame for Point-in-Polygon spatial joins
    valid_mask = [is_valid_coordinate(r["latitude"], r["longitude"]) for _, r in df_cands.iterrows()]
    df_cands = df_cands[valid_mask].copy()
    logger.info(f"Retained {len(df_cands)} candidates with valid spatial coordinates.")

    gdf = gpd.GeoDataFrame(
        df_cands,
        geometry=[Point(float(lon), float(lat)) for lon, lat in zip(df_cands["longitude"], df_cands["latitude"])],
        crs="EPSG:4326"
    )

    # Perform Point-in-Polygon Administrative Matching
    logger.info("Executing Point-in-Polygon spatial joins against official 33 Districts and Mandals...")
    gdf_admin = perform_administrative_join(gdf)

    # Build Master Inventory rows matching Sheet 1 specification
    master_records = []
    for idx, row in gdf_admin.iterrows():
        raw_name = str(row["candidate_name"]).strip()
        power_type = str(row["power_classification"]).strip()
        substation_type = str(row["substation_type"]).strip()
        raw_voltage = str(row["voltage"]).strip() if pd.notna(row["voltage"]) else ""
        operator = str(row["operator"]).strip() if pd.notna(row["operator"]) and str(row["operator"]).strip() != "" else "UNKNOWN"

        # Classify Voltage and Infrastructure Category
        std_v, p_kv, s_kv, ratio = parse_voltage_string(raw_voltage)
        infra_cat, sub_type_desc = classify_facility(power_type, substation_type, raw_voltage, raw_name)

        district = str(row["District"]).strip()
        mandal = str(row["Mandal"]).strip()
        lat = float(row["latitude"])
        lon = float(row["longitude"])

        # Match with government PDF records
        match_info = match_facility_to_pdf(raw_name, district, mandal, df_pdf)

        # Missing information tracking
        missing_fields = []
        if std_v == "UNKNOWN":
            missing_fields.append("Voltage")
        if operator == "UNKNOWN":
            missing_fields.append("Operator")
        missing_fields.append("Transformer Capacity")
        missing_fields.append("Installed Generation Capacity")
        missing_fields.append("Village")
        missing_str = ", ".join(missing_fields)

        record_id = f"SG_TG_{idx+1:05d}"

        master_records.append({
            "Record ID": record_id,
            "Facility Name": raw_name,
            "Alternative Name": str(row["name_alt"]).strip() if pd.notna(row["name_alt"]) and str(row["name_alt"]).strip() != "" else "UNKNOWN",
            "Infrastructure Category": infra_cat,
            "Substation Type": sub_type_desc,
            "Voltage Level": std_v,
            "Primary Voltage (kV)": p_kv,
            "Secondary Voltage (kV)": s_kv,
            "Transformer Ratio": ratio,
            "Transformer Count": "UNKNOWN",
            "Transformer Capacity (MVA)": "UNKNOWN",
            "Installed Capacity (MW)": "UNKNOWN",
            "DISCOM / Operator": operator,
            "State": "Telangana",
            "District": district,
            "Mandal": mandal,
            "Village": "UNKNOWN", # Strict anti-hallucination: not inferred without cadastral revenue records
            "Locality": mandal if mandal != "UNKNOWN" else district,
            "Latitude": round(lat, 7),
            "Longitude": round(lon, 7),
            "Discovery Source": str(row["source"]),
            "Source Feature ID": str(row["candidate_id"]),
            "Source URL": str(row["source_url"]),
            "PDF Match Status": match_info["PDF Match Status"],
            "PDF Serial Number": match_info["PDF Serial Number"],
            "Original PDF Substation Name": match_info["Original PDF Substation Name"],
            "Matching Score": match_info["Matching Score"],
            "Verification Status": match_info["Verification Status"],
            "Missing Information": missing_str,
            "Remarks": match_info["Remarks"]
        })

    master_df = pd.DataFrame(master_records)
    logger.info(f"Master Inventory compiled: {len(master_df)} facilities.")

    # Save outputs
    out_csv = "data/results/telangana_statewide_facilities.csv"
    candidates_csv = "data/candidates/discovered_candidates_master.csv"
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(candidates_csv), exist_ok=True)

    master_df.to_csv(out_csv, index=False, encoding="utf-8")
    master_df.to_csv(candidates_csv, index=False, encoding="utf-8")
    logger.info(f"Saved master statewide inventory to {out_csv} and {candidates_csv}")

    # Summary breakdown
    logger.info(f"Infrastructure Breakdown:\n{master_df['Infrastructure Category'].value_counts().to_string()}")
    logger.info(f"PDF Match Status Breakdown:\n{master_df['PDF Match Status'].value_counts().to_string()}")
    logger.info(f"Total Unique Districts represented: {master_df['District'].nunique()} / 33")
    logger.info(f"Total Unique Mandals represented: {master_df['Mandal'].nunique()}")

    return master_df

if __name__ == "__main__":
    build_statewide_inventory()
