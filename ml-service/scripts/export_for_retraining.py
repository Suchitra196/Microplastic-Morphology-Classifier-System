"""
Phase 8 — Export analysis DB to CSV for retraining
Run: python ml-service/scripts/export_for_retraining.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
from database import AnalysisDB

def main():
    db  = AnalysisDB()
    out = Path(__file__).resolve().parent.parent / "results" / "retraining_export.csv"
    db.export_csv(out)
    rows = db.get_all()
    print(f"  Total rows in DB: {len(rows)}")
    if rows:
        print(f"  Sample row: {rows[0]}")

if __name__ == "__main__":
    main()
