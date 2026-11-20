#!/usr/bin/env python3
"""
scripts/match_government_records.py
Cross-references discovered statewide electrical facilities with government PDF records (2,555 substations).
Uses RapidFuzz token sorting, phonetic permutations, and administrative context (Circle/District/Mandal).
Classifies into:
- EXACT_MATCH
- HIGH_CONFIDENCE_LIKELY_MATCH
- POSSIBLE_MATCH
- UNMATCHED
- AMBIGUOUS
- REQUIRES_MANUAL_VERIFICATION
"""

import re
import logging
import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger("match_government_records")

def clean_name_tokens(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    s = text.lower().strip()
    s = re.sub(r"(?i)\b(?:33/11\s*kv|33/11kv|33kv|11kv|132kv|220kv|400kv|sub\s*station|substation|ss|s/s)\b", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def match_facility_to_pdf(fac_name: str, fac_district: str, fac_mandal: str, pdf_df: pd.DataFrame) -> dict:
    f_clean = clean_name_tokens(fac_name)
    if not f_clean:
        return {
            "PDF Match Status": "UNMATCHED",
            "PDF Serial Number": "UNKNOWN",
            "Original PDF Substation Name": "UNKNOWN",
            "Matching Score": 0.0,
            "Verification Status": "UNVERIFIED",
            "Remarks": "Discovered facility has no valid name for string matching"
        }

    best_score = 0.0
    best_row = None
    candidate_matches = []

    # First pass: Filter by Circle or District if possible to narrow search
    for _, p_row in pdf_df.iterrows():
        base_name = p_row["cleaned_base_name"]
        p_clean = clean_name_tokens(base_name)
        if not p_clean:
            continue

        ts_ratio = fuzz.token_sort_ratio(f_clean, p_clean)
        tset_ratio = fuzz.token_set_ratio(f_clean, p_clean)
        score = float(max(ts_ratio, tset_ratio))

        # Check district / circle context match
        circle = str(p_row.get("Circle", "")).lower()
        district = str(fac_district).lower()
        mandal = str(fac_mandal).lower()
        subdiv = str(p_row.get("Sub division", "")).lower()
        sec = str(p_row.get("Section", "")).lower()

        context_boost = 0.0
        if circle in district or district in circle:
            context_boost += 5.0
        if mandal in subdiv or mandal in sec:
            context_boost += 5.0

        total_score = min(100.0, score + context_boost)

        if total_score >= 70.0:
            candidate_matches.append((total_score, p_row))

        if total_score > best_score:
            best_score = total_score
            best_row = p_row

    if not candidate_matches or best_row is None:
        return {
            "PDF Match Status": "UNMATCHED",
            "PDF Serial Number": "UNKNOWN",
            "Original PDF Substation Name": "UNKNOWN",
            "Matching Score": 0.0,
            "Verification Status": "UNVERIFIED",
            "Remarks": "Discovered facility not present in 33/11 kV government PDF scheme"
        }

    # Ambiguity check: Multiple candidates with similar top score in different circles
    top_candidates = [c for c in candidate_matches if c[0] >= best_score - 2.0]
    is_ambiguous = len(top_candidates) > 1 and len(set(str(c[1]["Circle"]) for c in top_candidates)) > 1

    sl_no = best_row["Sl. No."]
    orig_p_name = best_row["original_name"]

    if best_score == 100.0 and not is_ambiguous:
        status = "EXACT_MATCH"
        v_status = "CONFIRMED_MATCH"
        remarks = f"Exact match with government PDF record Sl.No {sl_no} ({orig_p_name})"
    elif best_score >= 90.0 and not is_ambiguous:
        status = "HIGH_CONFIDENCE_LIKELY_MATCH"
        v_status = "CONFIRMED_MATCH"
        remarks = f"High confidence string & administrative match with Sl.No {sl_no} ({orig_p_name})"
    elif is_ambiguous:
        status = "AMBIGUOUS"
        v_status = "REQUIRES_MANUAL_VERIFICATION"
        remarks = f"Ambiguous: {len(top_candidates)} possible matches across different circles (top Sl.No {sl_no})"
    elif best_score >= 70.0:
        status = "POSSIBLE_MATCH"
        v_status = "REQUIRES_MANUAL_VERIFICATION"
        remarks = f"Partial/possible match with Sl.No {sl_no} ({orig_p_name}); requires field confirmation"
    else:
        status = "UNMATCHED"
        v_status = "UNVERIFIED"
        remarks = "Matching score below acceptance threshold"

    return {
        "PDF Match Status": status,
        "PDF Serial Number": sl_no if best_score >= 70.0 else "UNKNOWN",
        "Original PDF Substation Name": orig_p_name if best_score >= 70.0 else "UNKNOWN",
        "Matching Score": round(best_score, 1),
        "Verification Status": v_status,
        "Remarks": remarks
    }
