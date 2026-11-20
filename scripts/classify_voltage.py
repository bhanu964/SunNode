#!/usr/bin/env python3
"""
scripts/classify_voltage.py
Classifies electrical infrastructure into standardized categories:
- Transmission substations (765 kV, 400 kV, 220 kV, 132 kV)
- 33/11 kV substations
- Other distribution substations (110 kV, 66 kV, 11 kV)
- Distribution transformers
- Generating stations
- Switching stations
- Unclassified electrical facilities
Extracts Primary Voltage, Secondary Voltage, and Voltage Ratio without guessing capacities.
"""

import re

def parse_voltage_string(raw_v: str) -> tuple[str, str, str, str]:
    """
    Parses voltage string (e.g., '132000', '400000;220000', '33000;11000', '132/33').
    Returns: (standardized_voltage_level, primary_kv, secondary_kv, transformer_ratio)
    """
    if not raw_v or not isinstance(raw_v, str) or str(raw_v).strip().upper() in ["", "NONE", "UNKNOWN", "N/A"]:
        return "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN"

    v_str = str(raw_v).strip()

    # Handle standard semicolon or slash separated values
    # Example: '400000;220000' -> primary 400, secondary 220
    parts = re.split(r"[/;,\s]+", v_str)
    num_parts = []
    for p in parts:
        try:
            val = float(re.sub(r"[^0-9.]", "", p))
            if val > 1000:
                val = val / 1000.0 # Convert Volts to kV (e.g., 400000 -> 400)
            if val > 0:
                num_parts.append(val)
        except (ValueError, TypeError):
            continue

    if not num_parts:
        return v_str, "UNKNOWN", "UNKNOWN", "UNKNOWN"

    num_parts = sorted(num_parts, reverse=True)
    if len(num_parts) == 1:
        p_kv = f"{int(num_parts[0]) if num_parts[0].is_integer() else num_parts[0]} kV"
        return f"{p_kv}", p_kv, "UNKNOWN", "UNKNOWN"
    else:
        p_val = int(num_parts[0]) if num_parts[0].is_integer() else num_parts[0]
        s_val = int(num_parts[1]) if num_parts[1].is_integer() else num_parts[1]
        p_kv = f"{p_val} kV"
        s_kv = f"{s_val} kV"
        ratio = f"{p_val}/{s_val} kV"
        return ratio, p_kv, s_kv, ratio

def classify_facility(power_type: str, substation_type: str, voltage_str: str, name: str) -> tuple[str, str]:
    """
    Determines infrastructure category and detailed substation type.
    """
    power_type = str(power_type).lower().strip()
    substation_type = str(substation_type).lower().strip()
    name_lower = str(name).lower().strip()
    std_v, p_kv, s_kv, ratio = parse_voltage_string(voltage_str)

    # 1. Transformers (Distinct from substations)
    if power_type == "transformer" or "transformer" in name_lower and "substation" not in name_lower:
        return "DISTRIBUTION_TRANSFORMER", "Distribution Transformer"

    # 2. Generating Stations / Power Plants
    if power_type in ["generator", "plant"] or "power plant" in name_lower or "generating" in name_lower:
        return "GENERATING_STATION", "Power Generating Station"

    # 3. Switching Stations / Switchgear
    if power_type in ["switchgear", "compensator"] or substation_type in ["transition", "switching"] or "switching station" in name_lower:
        return "SWITCHING_STATION", "Switching / Transition Station"

    # 4. Substations Classification based on Voltage and Substation Type
    p_num = 0.0
    if p_kv != "UNKNOWN":
        try:
            p_num = float(re.sub(r"[^0-9.]", "", p_kv))
        except ValueError:
            p_num = 0.0

    # High-Voltage Transmission Substations (>= 132 kV)
    if p_num >= 132 or substation_type == "transmission" or any(kv in name_lower for kv in ["765", "400", "220", "132"]):
        if p_num >= 400:
            return "TRANSMISSION_SUBSTATION", "Extra High Voltage (EHV) Transmission Substation (>=400 kV)"
        else:
            return "TRANSMISSION_SUBSTATION", "High Voltage (HV) Transmission Substation (132-220 kV)"

    # 33/11 kV Substations
    if ratio == "33/11 kV" or p_num == 33 or "33/11" in name_lower or "33/11kv" in name_lower:
        return "33_11KV_SUBSTATION", "33/11 kV Primary Distribution Substation"

    # Other Distribution Substations (110 kV, 66 kV, 11 kV)
    if p_num in [110, 66, 11] or substation_type in ["distribution", "minor_distribution"]:
        return "OTHER_DISTRIBUTION_SUBSTATION", f"Distribution Substation ({p_kv if p_kv != 'UNKNOWN' else 'Secondary Distribution'})"

    # Unclassified
    if std_v != "UNKNOWN":
        return "OTHER_DISTRIBUTION_SUBSTATION", f"Electrical Substation ({std_v})"
    return "UNCLASSIFIED_ELECTRICAL_FACILITY", "Unclassified Electrical Facility"
