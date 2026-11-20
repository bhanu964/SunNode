#!/usr/bin/env python3
"""
scripts/discover_locations.py
Aggregates publicly accessible electrical infrastructure datasets across Telangana.
Extracts named substations, voltage levels, operators, and spatial coordinates.
Outputs a unified candidates pool: data/results/geocoding_candidates.csv
"""

import os
import sys
import json
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/discover_locations.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("discover_locations")

# Valid bounding box for Telangana State
TG_BBOX = {
    "min_lat": 15.5,
    "max_lat": 20.0,
    "min_lon": 77.0,
    "max_lon": 82.0
}

def is_within_telangana(lat: float, lon: float) -> bool:
    if lat is None or lon is None:
        return False
    return (TG_BBOX["min_lat"] <= lat <= TG_BBOX["max_lat"] and
            TG_BBOX["min_lon"] <= lon <= TG_BBOX["max_lon"])

def parse_osm_files(file_paths: list) -> pd.DataFrame:
    records = []
    seen_ids = set()

    for path in file_paths:
        if not os.path.exists(path):
            logger.warning(f"File not found: {path}, skipping.")
            continue

        logger.info(f"Parsing OSM infrastructure file: {path}")
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                logger.error(f"Error decoding JSON in {path}: {e}")
                continue

        elements = data.get("elements", [])
        logger.info(f"Loaded {len(elements)} elements from {path}")

        for e in elements:
            e_type = e.get("type", "node")
            e_id = e.get("id")
            uid = f"OSM_{e_type}_{e_id}"
            if uid in seen_ids:
                continue
            seen_ids.add(uid)

            tags = e.get("tags", {})
            name = tags.get("name")
            name_en = tags.get("name:en")
            name_te = tags.get("name:te")
            power_type = tags.get("power", "substation")
            voltage = tags.get("voltage")
            operator = tags.get("operator")
            substation_type = tags.get("substation")
            ref = tags.get("ref")

            # Extract latitude and longitude (node has lat/lon, way/relation has center)
            lat = e.get("lat") or e.get("center", {}).get("lat")
            lon = e.get("lon") or e.get("center", {}).get("lon")

            if lat is None or lon is None:
                continue

            try:
                lat = float(lat)
                lon = float(lon)
            except (ValueError, TypeError):
                continue

            if not is_within_telangana(lat, lon):
                continue

            primary_name = name or name_en or name_te or ref or f"Unnamed {power_type}"
            records.append({
                "candidate_id": uid,
                "candidate_name": primary_name,
                "name_alt": name_en if name_en != name else "",
                "name_te": name_te or "",
                "latitude": round(lat, 7),
                "longitude": round(lon, 7),
                "power_classification": power_type,
                "substation_type": substation_type or "",
                "voltage": str(voltage) if voltage else "",
                "operator": str(operator) if operator else "",
                "source": "OpenStreetMap",
                "source_url": f"https://www.openstreetmap.org/{e_type}/{e_id}",
                "is_named": bool(name or name_en or name_te)
            })

    df = pd.DataFrame(records)
    logger.info(f"Total valid candidates discovered within Telangana: {len(df)}")
    return df

def run_discovery(output_candidates_csv: str):
    osm_files = [
        "data/raw/osm_telangana_substations.json",
        "data/raw/osm_telangana_power_extra.json"
    ]
    df = parse_osm_files(osm_files)
    os.makedirs(os.path.dirname(output_candidates_csv), exist_ok=True)
    df.to_csv(output_candidates_csv, index=False, encoding="utf-8")
    logger.info(f"Candidates saved to {output_candidates_csv} ({len(df)} records)")

    named_count = df["is_named"].sum()
    logger.info(f"Named candidates: {named_count}, Unnamed infrastructure polygons/nodes: {len(df) - named_count}")

if __name__ == "__main__":
    candidates_out = "data/results/geocoding_candidates.csv"
    run_discovery(candidates_out)
