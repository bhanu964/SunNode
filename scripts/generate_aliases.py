#!/usr/bin/env python3
"""
scripts/generate_aliases.py
Intelligently generates name normalizations and alternative aliases for all 33/11 kV substations.
Handles prefixes (33/11 KV), suffixes (SS, Substation, TSIIC), transliteration variants
(palli/pally, guda/gudem, pur/puram, pet/peta, v/w), space/joined permutations,
and administrative context combinations.
Outputs: data/processed/substation_aliases.csv
"""

import os
import re
import sys
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/generate_aliases.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("generate_aliases")

def clean_base_name(raw_name: str) -> str:
    """Removes standard prefixes, suffixes, and noise to produce canonical base name."""
    if not raw_name or not isinstance(raw_name, str):
        return ""

    s = raw_name.strip()

    # Extract parenthetical note if present, e.g., 'RAMAVARAM (Wardhannapet)'
    parenthetical = ""
    match_paren = re.search(r"\((.*?)\)", s)
    if match_paren:
        parenthetical = match_paren.group(1).strip()
        s = re.sub(r"\(.*?\)", "", s).strip()

    # Remove voltage prefixes/suffixes like 33/11 KV, 33/11KV, 33/11, 33KV
    s = re.sub(r"(?i)\b33\s*/\s*11\s*(?:kv|k\.v\.)?\b", "", s)
    s = re.sub(r"(?i)\b33\s*(?:kv|k\.v\.)\b", "", s)
    s = re.sub(r"(?i)\b11\s*(?:kv|k\.v\.)\b", "", s)

    # Remove Substation / SS suffixes/prefixes
    s = re.sub(r"(?i)\b(?:sub\s*station|substation|s/s|s\.s\.|ss)\b", "", s)

    # Clean whitespace and trailing punctuation
    s = re.sub(r"[\-_/\\,.]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s

def generate_transliteration_variants(name: str) -> set:
    """Generates phonetic and transliteration spelling variations common in Telangana."""
    variants = {name}
    lower = name.lower()

    # palli <-> pally <-> valli <-> vally
    if "palli" in lower:
        variants.add(re.sub(r"(?i)palli", "pally", name))
    if "pally" in lower:
        variants.add(re.sub(r"(?i)pally", "palli", name))
    if "valli" in lower:
        variants.add(re.sub(r"(?i)valli", "vally", name))
    if "vally" in lower:
        variants.add(re.sub(r"(?i)vally", "valli", name))

    # pur <-> puram
    if re.search(r"(?i)puram\b", name):
        variants.add(re.sub(r"(?i)puram\b", "pur", name))
    elif re.search(r"(?i)pur\b", name):
        variants.add(re.sub(r"(?i)pur\b", "puram", name))

    # pet <-> peta
    if re.search(r"(?i)peta\b", name):
        variants.add(re.sub(r"(?i)peta\b", "pet", name))
    elif re.search(r"(?i)pet\b", name):
        variants.add(re.sub(r"(?i)pet\b", "peta", name))

    # guda <-> gudem
    if re.search(r"(?i)gudem\b", name):
        variants.add(re.sub(r"(?i)gudem\b", "guda", name))
    elif re.search(r"(?i)guda\b", name):
        variants.add(re.sub(r"(?i)guda\b", "gudem", name))

    # v <-> w at word start or middle
    if "w" in lower:
        variants.add(re.sub(r"(?i)w", "v", name))
    elif "v" in lower:
        variants.add(re.sub(r"(?i)v", "w", name))

    # th <-> t
    if "th" in lower:
        variants.add(re.sub(r"(?i)th", "t", name))

    # Joined word vs Spaced words
    # e.g., "Devuni Yerravalli" -> "Devuniyerravalli"
    if " " in name:
        variants.add(name.replace(" ", ""))

    return variants

def build_substation_aliases(row: pd.Series) -> dict:
    original = str(row["Name of 33/11 Substation"]).strip()
    circle = str(row["Circle"]).strip() if pd.notna(row["Circle"]) else ""
    division = str(row["Division"]).strip() if pd.notna(row["Division"]) else ""
    subdiv = str(row["Sub division"]).strip() if pd.notna(row["Sub division"]) else ""
    section = str(row["Section"]).strip() if pd.notna(row["Section"]) else ""

    base = clean_base_name(original)
    if not base:
        base = original

    # Collect alias set
    alias_set = set()
    alias_set.add(base)
    alias_set.add(base.title())
    alias_set.add(base.upper())
    alias_set.add(f"{base} SS")
    alias_set.add(f"{base} Substation")
    alias_set.add(f"33/11 KV {base}")
    alias_set.add(f"33/11 KV {base} SS")

    # Transliteration variants
    phonetic_set = set()
    for v in generate_transliteration_variants(base):
        phonetic_set.add(v)
        phonetic_set.add(f"{v} SS")
        phonetic_set.add(f"{v} Substation")

    all_aliases = sorted(list(alias_set.union(phonetic_set)))

    # Search queries incorporating administrative hierarchy
    queries = [
        base,
        f"{base} substation",
        f"{base} {section}",
        f"{base} {subdiv}",
        f"{base} {circle}",
        f"{base} Telangana"
    ]
    # Deduplicate queries preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        cleaned_q = re.sub(r"\s+", " ", q).strip()
        if cleaned_q and cleaned_q.lower() not in seen:
            seen.add(cleaned_q.lower())
            unique_queries.append(cleaned_q)

    return {
        "Sl. No.": row["Sl. No."],
        "DISCOM": row["DISCOM"],
        "Circle": circle,
        "Division": division,
        "Sub division": subdiv,
        "Section": section,
        "original_name": original,
        "cleaned_base_name": base,
        "aliases": "; ".join(all_aliases),
        "search_queries": "; ".join(unique_queries),
        "admin_context": f"{section}, {subdiv}, {division}, {circle}, Telangana"
    }

def process_all_aliases(input_csv: str, output_csv: str):
    logger.info(f"Loading extracted substations from {input_csv}")
    df = pd.read_csv(input_csv)
    logger.info(f"Processing {len(df)} records for alias generation...")

    results = []
    for _, row in df.iterrows():
        res = build_substation_aliases(row)
        results.append(res)

    out_df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    out_df.to_csv(output_csv, index=False, encoding="utf-8")
    logger.info(f"Saved {len(out_df)} alias records to {output_csv}")

    # Log sample
    logger.info("Sample record generated:")
    sample = out_df.iloc[0]
    logger.info(f"Sl: {sample['Sl. No.']}, Original: {sample['original_name']}, Cleaned: {sample['cleaned_base_name']}")
    logger.info(f"Aliases count: {len(sample['aliases'].split('; '))}")
    logger.info(f"Queries: {sample['search_queries']}")

if __name__ == "__main__":
    src_csv = "data/processed/substations_extracted.csv"
    dst_csv = "data/processed/substation_aliases.csv"
    process_all_aliases(src_csv, dst_csv)
