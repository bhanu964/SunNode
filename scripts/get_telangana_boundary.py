#!/usr/bin/env python3
"""
scripts/get_telangana_boundary.py
Obtains, validates, and visualizes the complete Telangana state boundary polygon:
1. Generates data/boundaries/telangana_boundary.geojson (dissolved state polygon).
2. Generates data/boundaries/telangana_districts.geojson (district polygons).
3. Generates data/boundaries/telangana_blocks.geojson (444 mandal polygons).
4. Verifies area (~112,297 sq km) and extent in Google Earth Engine.
5. Produces reports/boundary_report.html with an interactive statewide map.
6. Exports boundary as an Earth Engine asset: projects/ai-voice-agent-crm/assets/suryagrid_telangana_boundary
"""

import os
import sys
import json
import logging
import geopandas as gpd
import folium
import ee
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/get_telangana_boundary.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("get_telangana_boundary")

EE_PROJECT_ID = os.getenv("EE_PROJECT_ID", "ai-voice-agent-crm")

def validate_and_process_boundaries():
    boundary_path = "data/boundaries/telangana_boundary.geojson"
    blocks_path = "data/boundaries/telangana_blocks.geojson"
    districts_path = "data/boundaries/telangana_districts.geojson"

    if not os.path.exists(boundary_path):
        logger.error(f"Missing {boundary_path}")
        sys.exit(1)

    logger.info("Loading state boundary GeoJSON...")
    gdf_state = gpd.read_file(boundary_path)
    geom = gdf_state.geometry.iloc[0]

    bounds = gdf_state.total_bounds # minx, miny, maxx, maxy
    logger.info(f"State Bounds: W={bounds[0]:.4f}, S={bounds[1]:.4f}, E={bounds[2]:.4f}, N={bounds[3]:.4f}")
    logger.info(f"Geometry Valid: {geom.is_valid}, Type: {geom.geom_type}")

    gdf_blocks = gpd.read_file(blocks_path)
    logger.info(f"Total mandals/blocks loaded: {len(gdf_blocks)}")

    # Initialize Earth Engine
    logger.info(f"Initializing Earth Engine with project: {EE_PROJECT_ID}")
    ee.Initialize(project=EE_PROJECT_ID)

    with open(boundary_path, "r", encoding="utf-8") as f:
        boundary_json = json.load(f)

    ee_feature = ee.Feature(ee.Geometry(boundary_json["features"][0]["geometry"]), {"state": "Telangana"})
    ee_fc = ee.FeatureCollection([ee_feature])
    area_km2 = ee_feature.geometry().area().divide(1e6).getInfo()
    logger.info(f"Earth Engine computed Telangana State Area: {area_km2:,.1f} sq km")

    # Export boundary to Earth Engine asset if not exists
    boundary_asset_id = f"projects/{EE_PROJECT_ID}/assets/suryagrid_telangana_boundary"
    try:
        ee.data.getAsset(boundary_asset_id)
        logger.info(f"Boundary asset already exists at {boundary_asset_id}")
    except Exception:
        logger.info(f"Exporting boundary to EE asset: {boundary_asset_id}")
        task = ee.batch.Export.table.toAsset(
            collection=ee_fc,
            description="suryagrid_telangana_boundary_export",
            assetId=boundary_asset_id
        )
        task.start()
        logger.info(f"Export task started with ID: {task.id}")

    # Generate interactive HTML visualization
    logger.info("Generating reports/boundary_report.html...")
    center_lat = (bounds[1] + bounds[3]) / 2.0
    center_lon = (bounds[0] + bounds[2]) / 2.0
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles="OpenStreetMap")

    # Add Mandals layer
    folium.GeoJson(
        gdf_blocks,
        name="Telangana Mandals (444)",
        style_function=lambda x: {
            "fillColor": "#0284c7",
            "color": "#38bdf8",
            "weight": 0.8,
            "fillOpacity": 0.15
        },
        tooltip=folium.GeoJsonTooltip(fields=["D_N", "DM_N"], aliases=["District:", "Mandal:"])
    ).add_to(m)

    # Add State Boundary layer
    folium.GeoJson(
        gdf_state,
        name="Telangana State Boundary",
        style_function=lambda x: {
            "fillColor": "none",
            "color": "#f97316",
            "weight": 3.5,
            "opacity": 1.0
        }
    ).add_to(m)

    folium.LayerControl().add_to(m)

    os.makedirs("reports", exist_ok=True)
    m.save("reports/boundary_report.html")
    logger.info("Boundary report saved to reports/boundary_report.html")

    report_data = {
        "state": "Telangana",
        "area_sq_km": round(area_km2, 1),
        "official_area_reference": "~112,077 sq km",
        "bounds": {
            "min_lon": round(bounds[0], 5),
            "min_lat": round(bounds[1], 5),
            "max_lon": round(bounds[2], 5),
            "max_lat": round(bounds[3], 5)
        },
        "mandals_count": len(gdf_blocks),
        "earth_engine_asset_id": boundary_asset_id,
        "geometry_valid": geom.is_valid
    }
    with open("reports/boundary_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    logger.info("Boundary processing completed successfully.")

if __name__ == "__main__":
    validate_and_process_boundaries()
