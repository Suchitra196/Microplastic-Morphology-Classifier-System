"""
Phase 5 — Ecological Threat Index (ETI) Scoring
================================================
Pure function: no I/O, no ML, no side effects.

INPUT
-----
  morphology    : str  — "Fiber", "Fragment", or "Film"
  feret_diameter: float — longest dimension in μm (or pixels if no scale)
  aspect_ratio  : float — feret / martin diameter
  area          : float — particle area in μm² (or px²)

OUTPUT
------
  ETIResult dataclass with:
    score       : float  0–100
    threat_level: str    "Low" | "Moderate" | "High" | "Critical"
    breakdown   : dict   component scores for transparency

WEIGHTING LOGIC (heuristic — not literature-derived)
-----------------------------------------------------
The ETI is a weighted sum of four sub-scores, each normalised to [0, 1]:

  1. Morphology score  (weight 0.35)
     Fiber     → 1.0   (highest: entanglement + penetration risk)
     Fragment  → 0.65  (moderate: ingestion + leaching)
     Film      → 0.45  (lower: less likely to penetrate tissue)

  2. Size score  (weight 0.30)
     Smaller particles are more dangerous (can cross biological barriers).
     Score = max(0, 1 - feret_diameter / SIZE_REFERENCE_UM)
     SIZE_REFERENCE_UM = 500 μm  (above this, penetration risk drops sharply)
     If feret_diameter is in pixels (scale unknown), a generic SIZE_REFERENCE_PX
     of 200 px is used and the result is flagged as approximate.

  3. Elongation score  (weight 0.25)
     Highly elongated particles (fibers, film sheets) are harder for organisms
     to excrete and more likely to cause physical damage.
     Score = min(1.0, max(0, aspect_ratio - 1) / ELONGATION_REFERENCE)
     ELONGATION_REFERENCE = 10 (aspect ratio ≥ 10 → full score)

  4. Area score  (weight 0.10)
     Larger surface area → more potential for adsorbed chemical release.
     Score = min(1.0, area / AREA_REFERENCE_UM2)
     AREA_REFERENCE_UM2 = 50000 μm²  (≈ 224×224 px at 1 μm/px)

These weights and reference values are deliberately documented as a
HEURISTIC PROTOTYPE. They were chosen to reproduce the qualitative risk
ordering seen in the microplastics literature (fiber > fragment > film,
smaller > larger) but have not been calibrated against any empirical
toxicity or bioaccumulation study.

Threat level thresholds:
  [0, 25)   → Low
  [25, 50)  → Moderate
  [50, 75)  → High
  [75, 100] → Critical
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

# ── constants ─────────────────────────────────────────────────────────────
WEIGHTS = {
    "morphology":  0.35,
    "size":        0.30,
    "elongation":  0.25,
    "area":        0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

MORPHOLOGY_SCORES = {
    "Fiber":    1.00,
    "Fragment": 0.65,
    "Film":     0.45,
}

SIZE_REFERENCE_UM  = 500.0    # μm
SIZE_REFERENCE_PX  = 200.0    # px (fallback when no scale calibration)
ELONGATION_REFERENCE = 10.0   # aspect ratio at which elongation score = 1.0
AREA_REFERENCE_UM2 = 50_000.0 # μm²
AREA_REFERENCE_PX2 = 10_000.0 # px² fallback

THRESHOLDS = [
    (75.0,  "Critical"),
    (50.0,  "High"),
    (25.0,  "Moderate"),
    (0.0,   "Low"),
]


# ── result type ───────────────────────────────────────────────────────────
@dataclass
class ETIResult:
    score:        float   # 0–100, rounded to 2 dp
    threat_level: str     # Low / Moderate / High / Critical
    breakdown: dict       # sub-scores and weights (for UI display)
    approximate:  bool    # True if no μm scale provided (pixel fallback used)

    def to_dict(self) -> dict:
        return asdict(self)

    def pretty(self) -> str:
        lines = [
            f"  ETI Score    : {self.score:.1f} / 100",
            f"  Threat Level : {self.threat_level}",
            f"  Approximate  : {self.approximate}",
            "  Breakdown:",
        ]
        for k, v in self.breakdown.items():
            lines.append(f"    {k:<18}: {v}")
        return "\n".join(lines)


# ── scoring function ───────────────────────────────────────────────────────
def compute_eti(
    morphology:     str,
    feret_diameter: float,
    aspect_ratio:   float,
    area:           float,
    unit:           str = "μm",   # "μm" or "px"
) -> ETIResult:
    """
    Compute the Ecological Threat Index.

    Parameters
    ----------
    morphology     : "Fiber", "Fragment", or "Film" (case-sensitive)
    feret_diameter : longest particle dimension (μm if unit=="μm", else px)
    aspect_ratio   : feret_diameter / martin_diameter
    area           : particle area (μm² or px²)
    unit           : "μm" (calibrated) or "px" (no scale provided)

    Returns
    -------
    ETIResult
    """
    # Normalise morphology string to title case for robustness
    morphology = morphology.strip().title()
    if morphology not in MORPHOLOGY_SCORES:
        raise ValueError(
            f"Unknown morphology '{morphology}'. "
            f"Expected one of: {list(MORPHOLOGY_SCORES.keys())}"
        )

    approximate = (unit != "μm")
    size_ref    = SIZE_REFERENCE_PX  if approximate else SIZE_REFERENCE_UM
    area_ref    = AREA_REFERENCE_PX2 if approximate else AREA_REFERENCE_UM2

    # 1. Morphology sub-score
    s_morphology = MORPHOLOGY_SCORES[morphology]

    # 2. Size sub-score (smaller → higher score)
    s_size = max(0.0, 1.0 - feret_diameter / size_ref)

    # 3. Elongation sub-score
    s_elongation = min(1.0, max(0.0, aspect_ratio - 1.0) / ELONGATION_REFERENCE)

    # 4. Area sub-score
    s_area = min(1.0, area / area_ref)

    # Weighted sum → scale to 0–100
    raw = (
        WEIGHTS["morphology"]  * s_morphology +
        WEIGHTS["size"]        * s_size       +
        WEIGHTS["elongation"]  * s_elongation +
        WEIGHTS["area"]        * s_area
    )
    score = round(min(100.0, max(0.0, raw * 100.0)), 2)

    # Threat level
    threat_level = "Low"
    for threshold, label in THRESHOLDS:
        if score >= threshold:
            threat_level = label
            break

    breakdown = {
        "morphology_score":   round(s_morphology,  4),
        "size_score":         round(s_size,         4),
        "elongation_score":   round(s_elongation,   4),
        "area_score":         round(s_area,         4),
        "weight_morphology":  WEIGHTS["morphology"],
        "weight_size":        WEIGHTS["size"],
        "weight_elongation":  WEIGHTS["elongation"],
        "weight_area":        WEIGHTS["area"],
    }

    return ETIResult(
        score=score,
        threat_level=threat_level,
        breakdown=breakdown,
        approximate=approximate,
    )
