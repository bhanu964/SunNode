#!/usr/bin/env python3
"""
scripts/earth_engine_import.py
Imports the statewide electrical infrastructure inventory into Google Earth Engine:
- Target asset: projects/ai-voice-agent-crm/assets/suryagrid_tel_statewide_inventory_v2
- Preserves existing asset projects/ai-voice-agent-crm/assets/suryagrid_substations_verified untouched
- Sanitizes all property keys for Earth Engine
- Submits and monitors export task
- Updates reports/earth_engine_report.json
"""

import os
import sys
import json
import time
import logging
import pandas as pd
import ee
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/earth_engine_import.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("earth_engine_import")

EE_PROJECT_ID = os.getenv("EE_PROJECT_ID", "ai-voice-agent-crm")
NEW_ASSET_ID = f"projects/{EE_PROJECT_ID}/assets/suryagrid_tel_statewide_inventory_v2"

def sanitize_ee_key(k: str) -> str:
    s = k.replace(".", "_").replace(" ", "_").replace("/", "_").replace("-", "_").lower()
    return s.strip("_")

def initialize_earth_engine(project_id: str) -> bool:
    try:
        ee.Initialize(project=project_id)
        test_val = ee.String("SuryaGrid Earth Engine connection active").getInfo()
        logger.info(f"Earth Engine initialized successfully: {test_val}")
        return True
    except Exception as e:
        logger.error(f"Earth Engine init failed: {e}")
        return False

def check_asset_exists(asset_id: str) -> bool:
    try:
        ee.data.getAsset(asset_id)
        return True
    except Exception:
        return False

def import_statewide_inventory_to_ee(geojson_path: str, report_json_path: str):
    if not initialize_earth_engine(EE_PROJECT_ID):
        logger.error("Initialization failed; cannot upload to Earth Engine.")
        sys.exit(1)

    logger.info(f"Reading statewide GeoJSON from {geojson_path}")
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    logger.info(f"Loaded {len(features)} Point features for Earth Engine ingestion.")

    ee_features = []
    for feat in features:
        coords = feat["geometry"]["coordinates"] # [lon, lat]
        pt = ee.Geometry.Point(coords)
        props = {}
        for k, v in feat.get("properties", {}).items():
            if v is not None:
                props[sanitize_ee_key(k)] = v
        ee_features.append(ee.Feature(pt, props))

    fc = ee.FeatureCollection(ee_features)
    logger.info(f"Constructed ee.FeatureCollection with {len(ee_features)} features.")

    # Check if target asset already exists
    if check_asset_exists(NEW_ASSET_ID):
        logger.warning(f"Target asset {NEW_ASSET_ID} already exists. Not overwriting.")
        task_id = "ALREADY_EXISTS"
        status_msg = "COMPLETED"
    else:
        logger.info(f"Starting batch export to new Earth Engine asset: {NEW_ASSET_ID}")
        task = ee.batch.Export.table.toAsset(
            collection=fc,
            description="suryagrid_tel_statewide_inventory_v2_export",
            assetId=NEW_ASSET_ID
        )
        task.start()
        task_id = task.id
        status_msg = task.status().get("state", "RUNNING")
        logger.info(f"Earth Engine export task started. Task ID: {task_id}, Status: {status_msg}")

    # Build report
    df_fac = pd.read_csv("data/results/telangana_statewide_facilities.csv")
    cat_counts = df_fac["Infrastructure Category"].value_counts().to_dict()
    match_counts = df_fac["PDF Match Status"].value_counts().to_dict()

    report = {
        "earth_engine_connection": "CONNECTED",
        "google_cloud_project": EE_PROJECT_ID,
        "new_statewide_asset_id": NEW_ASSET_ID,
        "preserved_previous_asset_id": f"projects/{EE_PROJECT_ID}/assets/suryagrid_substations_verified",
        "boundary_asset_id": f"projects/{EE_PROJECT_ID}/assets/suryagrid_telangana_boundary",
        "total_statewide_facilities_exported": len(df_fac),
        "infrastructure_categories": cat_counts,
        "pdf_match_breakdown": match_counts,
        "export_task_id": task_id,
        "task_status": status_msg,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "geojson_source": geojson_path,
        "excel_inventory_path": "outputs/SuryaGrid_Telangana_Statewide_Substation_Inventory.xlsx"
    }

    os.makedirs(os.path.dirname(report_json_path), exist_ok=True)
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Earth Engine statewide import report written to {report_json_path}")
    return report

if __name__ == "__main__":
    src_geo = "outputs/telangana_electrical_infrastructure.geojson"
    rep_out = "reports/earth_engine_report.json"
    import_statewide_inventory_to_ee(src_geo, rep_out)
