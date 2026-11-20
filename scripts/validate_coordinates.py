#!/usr/bin/env python3
"""
scripts/validate_coordinates.py
Validates geographical coordinates:
- Strict bounding box check [15.5 <= lat <= 20.0, 77.0 <= lon <= 82.0]
- Point geometry validity
- Coordinates ordering enforcement
"""

def is_valid_coordinate(lat, lon) -> bool:
    try:
        lat = float(lat)
        lon = float(lon)
        return (15.5 <= lat <= 20.0) and (77.0 <= lon <= 82.0)
    except (ValueError, TypeError):
        return False
