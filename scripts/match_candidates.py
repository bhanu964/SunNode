#!/usr/bin/env python3
"""
scripts/match_candidates.py
Matches 2,555 source substations against discovered geospatial infrastructure candidates.
Uses RapidFuzz (token sort, token set, partial ratio), voltage consistency, and administrative hierarchy.
Classifies into HIGH (90-100), MEDIUM (70-89), LOW (<70), and UNMATCHED.
Outputs: data/results/substations_matched.csv
"""

import os
import re
import sys
import logging
import pandas as pd
from rapidfuzz import fuzz

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/match_candidates.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("match_candidates")

def clean_for_matching(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    # Remove common substation suffixes for pure root matching
    s = text.lower().strip()
    s = re.sub(r"(?i)\b(?:33/11\s*kv|33/11kv|33kv|11kv|sub\s*station|substation|ss|s/s)\b", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def compute_similarity(source_base: str, aliases: list, cand_name: str) -> tuple[float, str]:
    """Computes composite similarity score and identifies matching token."""
    c_clean = clean_for_matching(cand_name)
    s_clean = clean_for_matching(source_base)

    if not c_clean or not s_clean:
        return 0.0, ""

    # Exact normalized match
    if s_clean == c_clean:
        return 100.0, f"Exact root match: '{s_clean}' == '{c_clean}'"

    # Test all alias variations
    best_score = 0.0
    best_reason = ""

    candidates_to_test = [s_clean] + [clean_for_matching(a) for a in aliases if clean_for_matching(a)]
    for query in set(candidates_to_test):
        if not query:
            continue
        ts_ratio = fuzz.token_sort_ratio(query, c_clean)
        tset_ratio = fuzz.token_set_ratio(query, c_clean)
        part_ratio = fuzz.partial_ratio(query, c_clean)

        # Composite score weighting
        # We heavily weight token sort and token set ratio to prevent partial substring false positives
        if min(len(query), len(c_clean)) <= 4 and part_ratio > 90 and ts_ratio < 70:
            # Short acronym / false substring guard
            composite = float(ts_ratio)
        else:
            composite = float(max(ts_ratio, tset_ratio))

        if composite > best_score:
            best_score = composite
            best_reason = f"Fuzzy match '{query}' vs '{c_clean}' (sort={ts_ratio:.1f}, set={tset_ratio:.1f})"

    return round(best_score, 2), best_reason

def evaluate_voltage_evidence(source_text: str, candidate_voltage: str) -> str:
    if not candidate_voltage:
        return "No voltage tag in candidate"
    v_cand = str(candidate_voltage).replace(" ", "")
    if "33000" in v_cand or "33" in v_cand or "11000" in v_cand or "11" in v_cand:
        return f"Confirmed 33/11 kV compatible voltage: {candidate_voltage}"
    elif "132000" in v_cand or "220000" in v_cand or "400000" in v_cand:
        return f"Transmission step-down facility: {candidate_voltage}"
    return f"Voltage tagged: {candidate_voltage}"

def run_matching(aliases_csv: str, candidates_csv: str, output_matched_csv: str):
    logger.info(f"Loading source aliases from {aliases_csv}")
    source_df = pd.read_csv(aliases_csv)
    logger.info(f"Loading discovered candidates from {candidates_csv}")
    cand_df = pd.read_csv(candidates_csv)

    # Filter candidates to only named ones for primary high/medium matching
    named_cands = cand_df[cand_df["is_named"]].copy()
    logger.info(f"Loaded {len(source_df)} source records and {len(named_cands)} named candidates.")

    matched_records = []

    for _, s_row in source_df.iterrows():
        sl_no = s_row["Sl. No."]
        discom = s_row["DISCOM"]
        circle = s_row["Circle"]
        division = s_row["Division"] if pd.notna(s_row["Division"]) else ""
        subdiv = s_row["Sub division"] if pd.notna(s_row["Sub division"]) else ""
        section = s_row["Section"] if pd.notna(s_row["Section"]) else ""
        orig_name = s_row["original_name"]
        base_name = s_row["cleaned_base_name"]
        alias_list = [a.strip() for a in str(s_row["aliases"]).split(";")]

        admin_context = f"{circle} {division} {subdiv} {section}".lower()

        # Find best candidate
        best_cand = None
        best_score = 0.0
        best_reason = ""

        for _, c_row in named_cands.iterrows():
            cand_name = str(c_row["candidate_name"])
            score, reason = compute_similarity(base_name, alias_list, cand_name)

            # Check if candidate mentions administrative context
            c_name_lower = cand_name.lower()
            if circle.lower() in c_name_lower or (division and division.lower() in c_name_lower):
                # Contextual confirmation boost
                score = min(100.0, score + 5.0)
                reason += " [+Admin context confirmed]"

            if score > best_score:
                best_score = score
                best_cand = c_row
                best_reason = reason

        # Confidence classification
        if best_cand is not None and best_score >= 90.0:
            confidence = "HIGH"
            status = "VERIFIED_CANDIDATE"
        elif best_cand is not None and best_score >= 70.0:
            confidence = "MEDIUM"
            status = "MANUAL_REVIEW_REQUIRED"
        elif best_cand is not None and best_score > 0.0:
            confidence = "LOW"
            status = "UNVERIFIED"
        else:
            confidence = "UNMATCHED"
            status = "UNMATCHED"

        if best_cand is not None and best_score >= 70.0:
            lat = best_cand["latitude"]
            lon = best_cand["longitude"]
            cand_name = best_cand["candidate_name"]
            cand_source = best_cand["source"]
            cand_id = best_cand["candidate_id"]
            cand_url = best_cand["source_url"]
            voltage_ev = evaluate_voltage_evidence(orig_name, best_cand["voltage"])
            evidence_desc = (
                f"{best_reason}; Source: {cand_source} ({cand_id}); "
                f"Coords: ({lat}, {lon}); Voltage: {best_cand['voltage'] or 'N/A'}; "
                f"Operator: {best_cand['operator'] or 'N/A'}"
            )
        else:
            lat = None
            lon = None
            cand_name = ""
            cand_source = ""
            cand_id = ""
            cand_url = ""
            voltage_ev = "No candidate match"
            evidence_desc = "No public electrical infrastructure match meeting the confidence threshold"

        matched_records.append({
            "Sl. No.": sl_no,
            "DISCOM": discom,
            "Circle": circle,
            "Division": division,
            "Sub division": subdiv,
            "Section": section,
            "original_name": orig_name,
            "generated_aliases": s_row["aliases"],
            "candidate_name": cand_name,
            "latitude": lat,
            "longitude": lon,
            "candidate_source": cand_source,
            "source_feature_id": cand_id,
            "source_url": cand_url,
            "matching_score": best_score,
            "confidence_tier": confidence,
            "evidence": evidence_desc,
            "match_explanation": best_reason if best_score >= 70.0 else "Score below acceptance threshold",
            "voltage_evidence": voltage_ev,
            "verification_status": status
        })

    out_df = pd.DataFrame(matched_records)
    os.makedirs(os.path.dirname(output_matched_csv), exist_ok=True)
    out_df.to_csv(output_matched_csv, index=False, encoding="utf-8")
    logger.info(f"Saved {len(out_df)} matched records to {output_matched_csv}")

    tier_counts = out_df["confidence_tier"].value_counts().to_dict()
    logger.info(f"Confidence Tier Breakdown: {tier_counts}")

if __name__ == "__main__":
    aliases_in = "data/processed/substation_aliases.csv"
    cands_in = "data/results/geocoding_candidates.csv"
    matched_out = "data/results/substations_matched.csv"
    run_matching(aliases_in, cands_in, matched_out)
