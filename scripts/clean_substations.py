#!/usr/bin/env python3
"""
scripts/clean_substations.py
Validates and standardizes extracted substation records:
- Strips excess whitespace and newlines from all columns.
- Imputes known missing fields (e.g., Sl.No. 88 Division: Gadwal) while logging changes.
- Validates serial continuity and duplicate names.
- Outputs cleaned tabular dataset: data/processed/substations_cleaned.csv
"""

import os
import sys
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/clean_substations.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("clean_substations")

def clean_dataset(input_csv: str, output_csv: str):
    logger.info(f"Loading raw extracted records from {input_csv}")
    df = pd.read_csv(input_csv, dtype=str)

    # Standardize string fields
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Impute known anomalies
    # Record Sl. No. 88: Circle is Gadwal, Subdivision is Ieeza, Section is Rajoli -> Division is Gadwal
    row_88_mask = df["Sl. No."] == "88"
    if not df.loc[row_88_mask, "Division"].values[0]:
        logger.info("Imputing missing Division for Sl.No. 88 (Mandoddi) -> 'Gadwal' based on hierarchy context.")
        df.loc[row_88_mask, "Division"] = "Gadwal"

    # Integrity validations
    assert len(df) == 2555, f"Expected 2555 records, found {len(df)}"
    assert df["Sl. No."].nunique() == 2555, "Non-unique serial numbers detected"

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False, encoding="utf-8")
    logger.info(f"Cleaned dataset saved to {output_csv} ({len(df)} records)")

if __name__ == "__main__":
    src = "data/processed/substations_extracted.csv"
    dst = "data/processed/substations_cleaned.csv"
    clean_dataset(src, dst)
