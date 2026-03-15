"""
Vessel identity resolution and conflict detection.
- When do two records refer to the same vessel?
- Detect invalid/conflicting records.
- Track vessel changes over time (name, flag, MMSI).
"""
import os
import sys
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.imo_validation import is_valid_imo

CSV_PATH = os.path.join(REPO_ROOT, "case_study_dataset_202509152039.csv")


def load_data():
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.strip() for c in df.columns]
    return df


def same_vessel(rec1: dict, rec2: dict) -> bool:
    """
    Heuristic: two records refer to the same vessel if:
    - Same valid IMO (strong), or
    - Same MMSI and consistent identity (name/callsign/type) and no IMO conflict.
    """
    imo1, imo2 = rec1.get("imo"), rec2.get("imo")
    mmsi1, mmsi2 = rec1.get("mmsi"), rec2.get("mmsi")

    # Strong: same valid IMO
    if imo1 is not None and imo2 is not None and imo1 == imo2:
        try:
            if is_valid_imo(int(imo1)):
                return True
        except (ValueError, TypeError):
            pass

    # Same MMSI: only if IMOs don't conflict
    if mmsi1 is not None and mmsi2 is not None and mmsi1 == mmsi2:
        if imo1 is not None and imo2 is not None and imo1 != imo2:
            return False  # conflict
        return True

    return False


def flag_invalid_records(df: pd.DataFrame) -> pd.DataFrame:
    """Add columns: invalid_imo, imo_mmsi_conflict, duplicate_key."""
    df = df.copy()
    def check_imo(v):
        if pd.isna(v):
            return False
        try:
            return is_valid_imo(int(float(v)))
        except (ValueError, TypeError):
            return False
    df["invalid_imo"] = ~df["imo"].apply(check_imo)

    # IMO–MMSI conflict: same MMSI, different (valid) IMOs
    mmsi_imos = df.groupby("mmsi")["imo"].apply(
        lambda s: set(int(x) for x in s.dropna().astype(int).unique())
    ).to_dict()

    def conflict(row):
        mmsi, imo = row["mmsi"], row["imo"]
        if pd.isna(mmsi) or pd.isna(imo):
            return False
        try:
            imo_int = int(imo)
        except (ValueError, TypeError):
            return False
        imos_for_mmsi = mmsi_imos.get(mmsi, set())
        if len(imos_for_mmsi) <= 1:
            return False
        return is_valid_imo(imo_int)
    df["imo_mmsi_conflict"] = df.apply(conflict, axis=1)

    df["duplicate_key"] = df.duplicated(subset=["imo", "mmsi"], keep=False)
    return df


def vessel_timeline(df: pd.DataFrame, imo: int) -> list[dict]:
    """Return records for a given IMO ordered by time (UpdateDate / staticData_updateTimestamp)."""
    try:
        subset = df[df["imo"].notna() & (df["imo"].astype(int) == imo)].copy()
    except (ValueError, TypeError):
        return []
    if subset.empty:
        return []
    ts_col = "UpdateDate" if "UpdateDate" in subset.columns else "staticData_updateTimestamp"
    subset[ts_col] = pd.to_datetime(subset[ts_col], errors="coerce")
    subset = subset.dropna(subset=[ts_col]).sort_values(ts_col)
    return subset[["imo", "mmsi", "name", "flag", "vessel_type", ts_col]].to_dict("records")


def main():
    df = load_data()
    df = flag_invalid_records(df)

    print("=" * 60)
    print("VESSEL IDENTITY & CONFLICT DETECTION")
    print("=" * 60)

    print("\n1) Invalid IMO count:", df["invalid_imo"].sum())
    print("2) IMO–MMSI conflict count:", df["imo_mmsi_conflict"].sum())
    print("3) Duplicate (imo, mmsi) rows:", df["duplicate_key"].sum())

    # Example: one valid IMO with multiple MMSIs (same vessel over time)
    imo_mmsi = df[["imo", "mmsi"]].drop_duplicates()
    valid_imos = imo_mmsi[imo_mmsi["imo"].apply(lambda x: is_valid_imo(x) if pd.notna(x) else False)]
    multi = valid_imos.groupby("imo")["mmsi"].nunique()
    example_imo = multi[multi > 1].index[0] if (multi > 1).any() else None
    if example_imo is not None:
        print("\n4) Example vessel (IMO) with multiple MMSIs over time:")
        timeline = vessel_timeline(df, int(example_imo))
        for r in timeline[:5]:
            print("   ", r)

    # Same-vessel check examples
    print("\n5) same_vessel() examples:")
    r_invalid = df.iloc[0].to_dict()
    r_invalid2 = df[df["imo"] == r_invalid["imo"]].iloc[-1].to_dict() if (df["imo"] == r_invalid["imo"]).sum() > 1 else r_invalid
    print("   Example A (invalid IMO – placeholder):")
    print("      r1: imo={}, mmsi={}, name={}".format(r_invalid.get("imo"), r_invalid.get("mmsi"), r_invalid.get("name")))
    print("      r2: imo={}, mmsi={}, name={}".format(r_invalid2.get("imo"), r_invalid2.get("mmsi"), r_invalid2.get("name")))
    print("      same_vessel(r1, r2):", same_vessel(r_invalid, r_invalid2))
    valid_imo_df = df[~df["invalid_imo"]]
    if len(valid_imo_df) >= 2:
        same_imo = valid_imo_df["imo"].value_counts()
        multi = same_imo[same_imo >= 2].index
        if len(multi) > 0:
            imo_val = int(multi[0])
            rows = valid_imo_df[valid_imo_df["imo"] == imo_val]
            r_a, r_b = rows.iloc[0].to_dict(), rows.iloc[-1].to_dict()
            print("   Example B (valid IMO – same vessel):")
            print("      r_a: imo={}, mmsi={}, name={}".format(r_a.get("imo"), r_a.get("mmsi"), r_a.get("name")))
            print("      r_b: imo={}, mmsi={}, name={}".format(r_b.get("imo"), r_b.get("mmsi"), r_b.get("name")))
            print("      same_vessel(r_a, r_b):", same_vessel(r_a, r_b))
    print("Done.")


if __name__ == "__main__":
    main()
