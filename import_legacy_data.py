#!/usr/bin/env python3
import argparse
import csv
import glob
import os
import sqlite3
from datetime import datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import legacy chart CSV files into charting.db.")
    parser.add_argument(
        "--db",
        default="data/charting.db",
        help="Path to destination SQLite database (default: data/charting.db).",
    )
    parser.add_argument(
        "--legacy-dir",
        default="",
        help="Directory containing legacy charts_YYYYMMDD.csv files.",
    )
    return parser.parse_args()


def first_existing_dir(candidates: list[str]) -> str:
    for candidate in candidates:
        expanded = os.path.expanduser(candidate)
        if os.path.isdir(expanded):
            return expanded
    return ""


def normalize_visit_date(timestamp: str, filename: str) -> str:
    ts = (timestamp or "").strip()
    if ts:
        try:
            return datetime.fromisoformat(ts).date().isoformat()
        except ValueError:
            if len(ts) >= 10:
                return ts[:10]

    base = os.path.basename(filename)
    # charts_YYYYMMDD.csv
    if base.startswith("charts_") and len(base) >= 15:
        raw = base[7:15]
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return datetime.now().date().isoformat()


def normalize_created_at(timestamp: str, visit_date: str) -> str:
    ts = (timestamp or "").strip()
    if not ts:
        return f"{visit_date}T00:00:00"
    try:
        return datetime.fromisoformat(ts).isoformat(timespec="seconds")
    except ValueError:
        if len(ts) >= 19:
            return ts[:19]
    return f"{visit_date}T00:00:00"


def row_value(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key, "")
        if value is not None and value.strip():
            return value.strip()
    return ""


def load_existing_keys(conn: sqlite3.Connection) -> set[tuple[str, str, str, str, str, str, str]]:
    existing = set()
    rows = conn.execute(
        """
        SELECT visit_date, subjective, treatment_details, client_feedback, home_care,
               recommended_treatment_plan, created_at
        FROM entries
        """
    ).fetchall()
    for row in rows:
        existing.add(tuple(row))
    return existing


def main() -> int:
    args = parse_args()

    legacy_dir = args.legacy_dir.strip()
    if not legacy_dir:
        legacy_dir = first_existing_dir(
            [
                "data/entry_data",
                "/Applications/Charting_App_2.0/dist/ChartingApp/entry_data",
            ]
        )

    if not legacy_dir:
        print("No legacy directory found. Use --legacy-dir to specify one.")
        return 1

    files = sorted(glob.glob(os.path.join(os.path.expanduser(legacy_dir), "charts_*.csv")))
    if not files:
        print(f"No charts_*.csv files found in: {legacy_dir}")
        return 1

    db_path = os.path.expanduser(args.db)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    inserted = 0
    skipped_existing = 0
    skipped_empty = 0

    with conn:
        existing = load_existing_keys(conn)
        for file_path in files:
            with open(file_path, newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    subjective = row_value(row, ["clinical_impression", "subjective"])
                    treatment_details = row_value(row, ["treatment_details", "treatment"])
                    client_feedback = row_value(row, ["client_feedback", "feedback"])
                    home_care = row_value(row, ["home_care", "homecare", "home_care_plan"])
                    recommended_treatment_plan = row_value(
                        row,
                        ["recommended_treatment_plan", "treatment_plan", "recommendation"],
                    )
                    timestamp = row_value(row, ["timestamp", "created_at", "time"])
                    visit_date = normalize_visit_date(timestamp, file_path)
                    created_at = normalize_created_at(timestamp, visit_date)

                    if not subjective and not treatment_details:
                        skipped_empty += 1
                        continue

                    key = (
                        visit_date,
                        subjective,
                        treatment_details,
                        client_feedback,
                        home_care,
                        recommended_treatment_plan,
                        created_at,
                    )
                    if key in existing:
                        skipped_existing += 1
                        continue

                    conn.execute(
                        """
                        INSERT INTO entries (
                            visit_date,
                            subjective,
                            treatment_details,
                            client_feedback,
                            home_care,
                            recommended_treatment_plan,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        key,
                    )
                    existing.add(key)
                    inserted += 1

    conn.close()

    print(f"Legacy directory: {legacy_dir}")
    print(f"Database: {db_path}")
    print(f"Inserted: {inserted}")
    print(f"Skipped existing: {skipped_existing}")
    print(f"Skipped empty: {skipped_empty}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
