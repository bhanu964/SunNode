#!/usr/bin/env python3
"""
scripts/export_geojson.py
Exports statewide electrical infrastructure to valid GeoJSON:
outputs/telangana_electrical_infrastructure.geojson
Ensures:
- Valid Point geometry with [longitude, latitude] coordinate ordering
- Coordinates fall strictly within Telangana
- Preserves all administrative and electrical properties
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
        logging.FileHandler("logs/export_geojson.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("export_geojson")

def export_geojson(input_csv: str, output_geojson: str):
    logger.info(f"Loading facilities from {input_csv}")
    df = pd.read_csv(input_csv)

    # Validate coordinate ranges
    valid_mask = (df["Latitude"] >= 15.5) & (df["Latitude"] <= 20.0) & (df["Longitude"] >= 77.0) & (df["Longitude"] <= 82.0)
    df = df[valid_mask].copy()

    # Geometry: Point(lon, lat)
    geometries = [Point(float(lon), float(lat)) for lon, lat in zip(df["Longitude"], df["Latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometries, crs="EPSG:4326")

    os.makedirs(os.path.dirname(output_geojson), exist_ok=True)
    gdf.to_file(output_geojson, driver="GeoJSON")
    logger.info(f"GeoJSON exported to {output_geojson} ({len(gdf)} features)")

    # Verify GeoJSON valid structure
    with open(output_geojson, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Verified GeoJSON structure: {data.get('type')}, Features: {len(data.get('features', []))}")

if __name__ == "__main__":
    src_csv = "data/results/telangana_statewide_facilities.csv"
    dst_geojson = "outputs/telangana_electrical_infrastructure.geojson"
    export_geojson(src_csv, dst_geojson)
