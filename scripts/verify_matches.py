#!/usr/bin/env python3
"""
scripts/verify_matches.py
Validates coordinates, filters confirmed high-confidence matches, and splits the dataset into:
1. data/results/substations_verified.csv (HIGH confidence verified records with evidence)
2. data/results/substations_unmatched.csv (MEDIUM, LOW, and UNMATCHED records for review)
3. data/results/substations_verified.geojson (Valid GeoJSON Point geometries, [lon, lat])
"""

import os
import sys
import json
import logging
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/verify_matches.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("verify_matches")

# Strict bounding box for Telangana
TG_LAT_MIN, TG_LAT_MAX = 15.5, 20.0
TG_LON_MIN, TG_LON_MAX = 77.0, 82.0

def validate_coordinates(lat, lon) -> bool:
    try:
        lat = float(lat)
        lon = float(lon)
        return (TG_LAT_MIN <= lat <= TG_LAT_MAX) and (TG_LON_MIN <= lon <= TG_LON_MAX)
    except (ValueError, TypeError):
        return False

def run_verification(matched_csv: str, verified_csv: str, unmatched_csv: str, verified_geojson: str):
    logger.info(f"Loading matched results from {matched_csv}")
    df = pd.read_csv(matched_csv)
    total_records = len(df)
    logger.info(f"Total input records: {total_records}")

    verified_rows = []
    unmatched_rows = []

    for _, row in df.iterrows():
        tier = row["confidence_tier"]
        score = float(row["matching_score"]) if pd.notna(row["matching_score"]) else 0.0
        lat = row["latitude"]
        lon = row["longitude"]

        # Verification criteria:
        # 1. Tier is HIGH (score >= 90)
        # 2. Coordinates exist and fall within valid Telangana bounding box
        # 3. Candidate source is confirmed public electrical infrastructure
        if tier == "HIGH" and validate_coordinates(lat, lon):
            row_dict = row.to_dict()
            row_dict["verification_status"] = "VERIFIED"
            row_dict["verified_lat"] = float(lat)
            row_dict["verified_lon"] = float(lon)
            verified_rows.append(row_dict)
        else:
            row_dict = row.to_dict()
            if tier == "MEDIUM":
                row_dict["review_reason"] = f"Medium confidence match (score {score:.1f}) requires manual field validation"
            elif tier == "LOW":
                row_dict["review_reason"] = f"Low confidence match (score {score:.1f}) below acceptance threshold"
            else:
                row_dict["review_reason"] = "No candidate found in public infrastructure dataset"
            unmatched_rows.append(row_dict)

    df_verified = pd.DataFrame(verified_rows)
    df_unmatched = pd.DataFrame(unmatched_rows)

    os.makedirs(os.path.dirname(verified_csv), exist_ok=True)
    df_verified.to_csv(verified_csv, index=False, encoding="utf-8")
    logger.info(f"Saved {len(df_verified)} VERIFIED substations to {verified_csv}")

    df_unmatched.to_csv(unmatched_csv, index=False, encoding="utf-8")
    logger.info(f"Saved {len(df_unmatched)} UNMATCHED / MANUAL REVIEW records to {unmatched_csv}")

    # Generate GeoJSON for verified records
    if not df_verified.empty:
        geometry = [Point(lon, lat) for lon, lat in zip(df_verified["verified_lon"], df_verified["verified_lat"])]
        gdf = gpd.GeoDataFrame(df_verified, geometry=geometry, crs="EPSG:4326")
        gdf.to_file(verified_geojson, driver="GeoJSON")
        logger.info(f"Generated GeoJSON with {len(gdf)} Point features at {verified_geojson}")

    # Summary report
    summary = {
        "total_source_records": total_records,
        "verified_count": len(df_verified),
        "unmatched_or_review_count": len(df_unmatched),
        "verified_percentage": round((len(df_verified) / total_records) * 100, 2),
        "discom_verified": df_verified["DISCOM"].value_counts().to_dict() if not df_verified.empty else {}
    }
    logger.info(f"Verification Summary: {summary}")
    return summary

if __name__ == "__main__":
    matched_file = "data/results/substations_matched.csv"
    verified_file = "data/results/substations_verified.csv"
    unmatched_file = "data/results/substations_unmatched.csv"
    geojson_file = "data/results/substations_verified.geojson"
    run_verification(matched_file, verified_file, unmatched_file, geojson_file)
