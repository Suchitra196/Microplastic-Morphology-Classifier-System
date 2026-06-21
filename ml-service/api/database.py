"""
Phase 8 — SQLite Data Store for Feedback / Retraining
=======================================================
Stores every /classify result with an optional corrected_label field
for future human feedback.

Schema
------
Table: analyses
  id               INTEGER PRIMARY KEY AUTOINCREMENT
  created_at       TEXT       ISO-8601 timestamp
  image_path       TEXT       path or hash identifying the source image
  integrity_hash   TEXT       SHA-256(image + result) from server.ts

  -- OpenCV features (μm if calibrated, px otherwise) --
  unit             TEXT       "μm" or "px"
  scale_um_per_px  REAL       NULL if no calibration provided
  feret_diameter   REAL
  martin_diameter  REAL
  aspect_ratio     REAL
  area             REAL
  perimeter        REAL
  elongation       REAL
  solidity         REAL
  circularity      REAL

  -- ML classification --
  predicted_class  TEXT       Fiber / Fragment / Film
  confidence       REAL       0–1
  fiber_prob       REAL
  film_prob        REAL
  fragment_prob    REAL
  model_source     TEXT       dataset source used to train the model

  -- ETI --
  eti_score        REAL
  threat_level     TEXT

  -- Human feedback (populated later) --
  corrected_label  TEXT       NULL until a human reviews and corrects

Usage
-----
  from database import AnalysisDB
  db = AnalysisDB()               # opens/creates ml-service/data/analyses.db
  db.insert(record_dict)
  db.get_all()                    # returns list of row dicts
  db.export_csv("out.csv")        # export for retraining
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "analyses.db"


class AnalysisDB:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at       TEXT    NOT NULL,
                    image_path       TEXT,
                    integrity_hash   TEXT,

                    unit             TEXT,
                    scale_um_per_px  REAL,
                    feret_diameter   REAL,
                    martin_diameter  REAL,
                    aspect_ratio     REAL,
                    area             REAL,
                    perimeter        REAL,
                    elongation       REAL,
                    solidity         REAL,
                    circularity      REAL,

                    predicted_class  TEXT,
                    confidence       REAL,
                    fiber_prob       REAL,
                    film_prob        REAL,
                    fragment_prob    REAL,
                    model_source     TEXT,

                    eti_score        REAL,
                    threat_level     TEXT,

                    corrected_label  TEXT DEFAULT NULL
                )
            """)
            conn.commit()

    def insert(self, result: dict) -> int:
        """
        Insert a /classify API response (as returned by the FastAPI service)
        enriched with optional integrity_hash and image_path fields.

        Returns the new row id.
        """
        feat   = result.get("features", {})
        eti    = result.get("eti", {})
        probs  = result.get("class_probabilities", {})

        row = {
            "created_at":      datetime.now(timezone.utc).isoformat(),
            "image_path":      result.get("image_path"),
            "integrity_hash":  result.get("integrity_hash"),

            "unit":            feat.get("unit"),
            "scale_um_per_px": feat.get("scale_um_per_px"),
            "feret_diameter":  feat.get("feret_diameter"),
            "martin_diameter": feat.get("martin_diameter"),
            "aspect_ratio":    feat.get("aspect_ratio"),
            "area":            feat.get("area"),
            "perimeter":       feat.get("perimeter"),
            "elongation":      feat.get("elongation"),
            "solidity":        feat.get("solidity"),
            "circularity":     feat.get("circularity"),

            "predicted_class": result.get("predicted_class"),
            "confidence":      result.get("confidence"),
            "fiber_prob":      probs.get("Fiber"),
            "film_prob":       probs.get("Film"),
            "fragment_prob":   probs.get("Fragment"),
            "model_source":    result.get("model_source"),

            "eti_score":       eti.get("score"),
            "threat_level":    eti.get("threat_level"),

            "corrected_label": result.get("corrected_label"),
        }

        cols   = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        with self._conn() as conn:
            cur = conn.execute(
                f"INSERT INTO analyses ({cols}) VALUES ({placeholders})",
                list(row.values()),
            )
            conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def get_all(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM analyses ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def set_corrected_label(self, row_id: int, label: str):
        """Human feedback: set the corrected morphology class for a row."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE analyses SET corrected_label = ? WHERE id = ?",
                (label, row_id),
            )
            conn.commit()

    def export_csv(self, output_path: str | Path):
        """
        Export all rows where corrected_label is set (or all rows if none are
        labelled yet) as a CSV suitable for re-training.

        Columns: image_path, corrected_label (falls back to predicted_class),
        feret_diameter, martin_diameter, aspect_ratio, area, unit, eti_score
        """
        rows = self.get_all()
        output_path = Path(output_path)

        fieldnames = [
            "id", "created_at", "image_path",
            "predicted_class", "corrected_label", "label_for_training",
            "feret_diameter", "martin_diameter", "aspect_ratio",
            "area", "unit", "confidence", "eti_score", "threat_level",
        ]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                r["label_for_training"] = r["corrected_label"] or r["predicted_class"]
                writer.writerow({k: r.get(k) for k in fieldnames})

        print(f"  Exported {len(rows)} rows → {output_path}")
        return output_path
