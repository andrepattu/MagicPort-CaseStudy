"""
Explore the vessel case study dataset: columns, stats, duplicates, invalid IMO/MMSI.
Run from repo root: python scripts/explore_dataset.py
"""
import os
import sys

import pandas as pd

# Allow importing from repo root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.imo_validation import is_valid_imo

CSV_PATH = os.path.join(REPO_ROOT, "case_study_dataset_202509152039.csv")


def load_data():
    df = pd.read_csv(CSV_PATH)
    # Normalize column names (duplicate 'draught' exists; second one is voyage draught)
    df.columns = [c.strip() for c in df.columns]
    return df


def main():
    df = load_data()
    n = len(df)

    print("=" * 60)
    print("DATASET EXPLORATION")
    print("=" * 60)
    print(f"Rows: {n}, Columns: {len(df.columns)}")
    print()

    # Column groups (by interpretation)
    static = [
        "imo", "mmsi", "name", "aisClass", "callsign", "length", "width",
        "vessel_type", "flag", "deadweight", "grossTonnage", "builtYear",
        "netTonnage", "hullTypeCode", "shipBuilder", "hullNumber", "launchYear",
    ]
    position = [
        "last_position_latitude", "last_position_longitude",
        "last_position_speed", "last_position_course", "last_position_heading",
        "last_position_updateTimestamp", "last_position_accuracy",
    ]
    voyage = [
        "destination", "eta", "matchedPort_name", "matchedPort_unlocode",
        "matchedPort_latitude", "matchedPort_longitude",
    ]
    meta = ["InsertDate", "UpdateDate", "staticData_updateTimestamp"]

    print("Column interpretation (summary):")
    print("  Static/registry: imo, mmsi, name, vessel_type, flag, dimensions, tonnages, builtYear, ...")
    print("  AIS/position:    last_position_*, last_position_updateTimestamp")
    print("  Voyage:          destination, eta, matchedPort_*")
    print("  Meta:            InsertDate, UpdateDate")
    print()

    # IMO validation: single-value checksum via is_valid_imo
    def check_imo(v):
        if pd.isna(v) or (isinstance(v, float) and (v != v or int(v) != v)):
            return False
        try:
            return is_valid_imo(int(float(v)))
        except (ValueError, TypeError):
            return False
    valid_imo_mask = df["imo"].apply(check_imo)
    invalid_imo_series = df.loc[~valid_imo_mask, "imo"].dropna()
    try:
        invalid_imos = invalid_imo_series.astype(int).unique().tolist()
    except (ValueError, TypeError):
        invalid_imos = invalid_imo_series.unique().tolist()
    zero_imo = (df["imo"].fillna(-1).astype(int) == 0).sum()
    placeholder_imo = df["imo"].astype(str).str.match(r"^(0|1000000|2097152|2097216|3395388|8000000|1234560|1111110|32768|707800112|231636981|134548308|123456789|345314265)$").fillna(False).sum()

    print("IMO ANALYSIS")
    print("-" * 40)
    print(f"  Non-null IMO count:     {df['imo'].count()}")
    print(f"  Valid checksum (7-digit): {valid_imo_mask.sum()}")
    print(f"  Invalid/placeholder IMO count: {len(invalid_imos)} distinct values")
    print(f"  IMO = 0 count:          {zero_imo}")
    print(f"  Common placeholder IMOs: 1000000, 0, 2097152, 2097216, 3395388, 8000000, ...")
    print()

    # MMSI: should be 9 digits
    mmsi = df["mmsi"].dropna().astype(int)
    mmsi_valid_len = mmsi.astype(str).str.len() == 9
    print("MMSI ANALYSIS")
    print("-" * 40)
    print(f"  Non-null MMSI:          {mmsi.count()}")
    print(f"  MMSI 9-digit:           {mmsi_valid_len.sum()}")
    print(f"  Duplicate MMSI (multiple rows): {df['mmsi'].duplicated(keep=False).sum()} rows")
    print()

    # Same IMO -> multiple MMSIs (expected: vessel re-flagging / MMSI change)
    imo_mmsi = df[["imo", "mmsi"]].drop_duplicates()
    imo_counts = imo_mmsi.groupby("imo")["mmsi"].nunique()
    multi_mmsi_imos = imo_counts[imo_counts > 1]
    print("IMO -> MULTIPLE MMSIs (identity / flag change)")
    print("-" * 40)
    print(f"  IMOs with more than one MMSI: {len(multi_mmsi_imos)}")
    if len(multi_mmsi_imos) > 0:
        sample = multi_mmsi_imos.head(5)
        for imo in sample.index:
            mmsis = imo_mmsi[imo_mmsi["imo"] == imo]["mmsi"].tolist()
            print(f"    IMO {imo}: MMSIs {mmsis}")
    print()

    # Same MMSI -> multiple IMOs (conflict)
    mmsi_imo_counts = imo_mmsi.groupby("mmsi")["imo"].nunique()
    multi_imo_mmsis = mmsi_imo_counts[mmsi_imo_counts > 1]
    print("MMSI -> MULTIPLE IMOs (conflict)")
    print("-" * 40)
    print(f"  MMSIs with more than one IMO: {len(multi_imo_mmsis)}")
    if len(multi_imo_mmsis) > 0:
        for mmsi_val in multi_imo_mmsis.head(3).index:
            imos_for_mmsi = imo_mmsi[imo_mmsi["mmsi"] == mmsi_val]["imo"].tolist()
            print(f"    MMSI {mmsi_val}: IMOs {imos_for_mmsi}")
    print()

    # Duplicate (imo, mmsi) with different attributes
    dup_keys = df.duplicated(subset=["imo", "mmsi"], keep=False)
    print("DUPLICATE (IMO, MMSI) PAIRS")
    print("-" * 40)
    print(f"  Rows with duplicate (imo, mmsi): {dup_keys.sum()}")
    print()

    # Missing key fields
    print("MISSING KEY FIELDS")
    print("-" * 40)
    for col in ["imo", "mmsi", "name", "vessel_type", "flag"]:
        missing = df[col].isna().sum()
        empty = (df[col].astype(str).str.strip() == "").sum()
        print(f"  {col}: null={missing}, empty={empty}")
    print()

    # Vessel type and flag value counts
    print("VESSEL_TYPE (sample)")
    print("-" * 40)
    print(df["vessel_type"].value_counts().head(15).to_string())
    print()
    print("FLAG (sample)")
    print("-" * 40)
    print(df["flag"].value_counts().head(15).to_string())
    print()
    print("Done.")


if __name__ == "__main__":
    main()
