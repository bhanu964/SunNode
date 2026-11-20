#!/usr/bin/env python3
"""
scripts/administrative_matching.py
Performs accurate Point-in-Polygon spatial joins for all facility coordinates against:
- Official 33 Telangana Districts (telangana_33_districts.geojson)
- Official Mandals / Subdistricts (telangana_subdistricts_current.geojson)
Avoids assumptions based on names and ensures spatial ground truth.
"""

import os
import logging
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

logger = logging.getLogger("administrative_matching")

def perform_administrative_join(gdf_points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    districts_file = "data/boundaries/telangana_33_districts.geojson"
    mandals_file = "data/boundaries/telangana_subdistricts_current.geojson"
    state_file = "data/boundaries/telangana_boundary.geojson"

    gdf_dist = gpd.read_file(districts_file)[["dtname", "geometry"]]
    gdf_mandals = gpd.read_file(mandals_file)[["sdtname", "geometry"]]
    gdf_state = gpd.read_file(state_file)
    state_geom = gdf_state.geometry.iloc[0]

    # Ensure CRS is EPSG:4326
    if gdf_points.crs != "EPSG:4326":
        gdf_points = gdf_points.to_crs("EPSG:4326")

    # Check state containment
    is_in_state = gdf_points.geometry.apply(lambda g: state_geom.contains(g) or state_geom.touches(g))
    gdf_points["within_telangana"] = is_in_state

    # Join District
    joined_dist = gpd.sjoin(gdf_points, gdf_dist, how="left", predicate="within")
    joined_dist["District"] = joined_dist["dtname"].fillna("UNKNOWN")
    joined_dist = joined_dist.drop(columns=["index_right", "dtname"], errors="ignore")

    # Join Mandal
    joined_all = gpd.sjoin(joined_dist, gdf_mandals, how="left", predicate="within")
    joined_all["Mandal"] = joined_all["sdtname"].fillna("UNKNOWN")
    joined_all = joined_all.drop(columns=["index_right", "sdtname"], errors="ignore")

    return joined_all
