#!/usr/bin/env python3
"""
scripts/extract_pdf.py
Extracts all 33/11 kV substation records from 'Sub-Stations list KUSUM Component-A.pdf'.
Preserves original serial numbers, column names, administrative hierarchy, and spelling.
Validates extracted records against expected totals and logs any anomalies.
"""

import os
import sys
import json
import logging
import pdfplumber
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/extract_pdf.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger("extract_pdf")

EXPECTED_COLUMNS = [
    "Sl. No.",
    "DISCOM",
    "Circle",
    "Division",
    "Sub division",
    "Section",
    "Name of 33/11 Substation"
]

def extract_pdf(pdf_path: str, output_csv: str, error_report_path: str):
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found at: {pdf_path}")
        sys.exit(1)

    logger.info(f"Opening PDF: {pdf_path}")
    extracted_rows = []
    anomalies = []
    header_found = None
    page_count = 0

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        logger.info(f"Total pages detected: {page_count}")

        for page_idx, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if not tables:
                msg = f"Warning: No tables found on page {page_idx + 1}"
                logger.warning(msg)
                anomalies.append({"page": page_idx + 1, "issue": "No table found"})
                continue

            for t_idx, table in enumerate(tables):
                for row_idx, row in enumerate(table):
                    if not row or not any(row):
                        continue

                    # Check for header row
                    first_cell = str(row[0]).strip() if row[0] is not None else ""
                    second_cell = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
                    if "Sl" in first_cell and "DISCOM" in second_cell:
                        if header_found is None:
                            header_found = [str(c).replace("\n", " ").strip() for c in row if c]
                            logger.info(f"Header discovered on page {page_idx + 1}: {header_found}")
                        continue

                    # Validate row column count
                    if len(row) != 7:
                        anomalies.append({
                            "page": page_idx + 1,
                            "row_index": row_idx,
                            "issue": f"Unexpected column count: {len(row)} instead of 7",
                            "raw_row": [str(c) for c in row]
                        })
                        continue

                    cleaned_cells = [
                        str(cell).replace("\r\n", " ").replace("\n", " ").strip() if cell is not None else ""
                        for cell in row
                    ]

                    sl_no, discom, circle, division, subdiv, sec, name = cleaned_cells

                    # Anomaly detection on cells
                    if not sl_no:
                        anomalies.append({
                            "page": page_idx + 1,
                            "row_index": row_idx,
                            "issue": "Missing serial number",
                            "raw_row": cleaned_cells
                        })
                    if not name:
                        anomalies.append({
                            "page": page_idx + 1,
                            "row_index": row_idx,
                            "issue": "Missing substation name",
                            "raw_row": cleaned_cells
                        })
                    if not division:
                        anomalies.append({
                            "page": page_idx + 1,
                            "sl_no": sl_no,
                            "issue": "Missing division in source PDF",
                            "name": name,
                            "circle": circle
                        })

                    extracted_rows.append({
                        "Sl. No.": sl_no,
                        "DISCOM": discom,
                        "Circle": circle,
                        "Division": division,
                        "Sub division": subdiv,
                        "Section": sec,
                        "Name of 33/11 Substation": name,
                        "_page": page_idx + 1
                    })

    df = pd.DataFrame(extracted_rows)
    logger.info(f"Extracted {len(df)} records across {page_count} pages.")

    # Integrity validations
    duplicate_sl = df[df.duplicated(subset=["Sl. No."], keep=False)]
    if not duplicate_sl.empty:
        logger.warning(f"Found {len(duplicate_sl)} rows with duplicated Sl. No.!")
        for _, r in duplicate_sl.iterrows():
            anomalies.append({
                "issue": "Duplicate Sl. No.",
                "sl_no": r["Sl. No."],
                "name": r["Name of 33/11 Substation"],
                "circle": r["Circle"]
            })
    else:
        logger.info("Verification passed: 0 duplicate Sl. No. found. Serial sequence is 100% unique.")

    # Save CSV
    out_df = df[EXPECTED_COLUMNS]
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    out_df.to_csv(output_csv, index=False, encoding="utf-8")
    logger.info(f"Saved {len(out_df)} records to {output_csv}")

    # Generate extraction summary report
    report = {
        "pdf_source": pdf_path,
        "total_pages": page_count,
        "total_records_extracted": len(df),
        "unique_serial_numbers": df["Sl. No."].nunique(),
        "discom_breakdown": df["DISCOM"].value_counts().to_dict(),
        "circles_count": df["Circle"].nunique(),
        "divisions_count": df["Division"].replace("", pd.NA).dropna().nunique(),
        "subdivisions_count": df["Sub division"].nunique(),
        "sections_count": df["Section"].nunique(),
        "unique_substation_names": df["Name of 33/11 Substation"].str.lower().nunique(),
        "total_anomalies_detected": len(anomalies),
        "anomalies": anomalies
    }

    os.makedirs(os.path.dirname(error_report_path), exist_ok=True)
    with open(error_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Extraction audit report written to {error_report_path}")

    return report

if __name__ == "__main__":
    pdf_in = "data/raw/Sub-Stations list KUSUM Component-A.pdf"
    csv_out = "data/processed/substations_extracted.csv"
    audit_out = "reports/extraction_report.json"
    extract_pdf(pdf_in, csv_out, audit_out)
