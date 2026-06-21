"""
Phase 5 — ETI unit tests
Covers all four threat levels, edge cases, and validation errors.
Run with:  python -m pytest ml-service/tests/test_eti.py -v
"""

import sys
from pathlib import Path
import pytest

# Allow importing from ml-service/api without installing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
from eti_scoring import compute_eti, ETIResult


# ── helper ────────────────────────────────────────────────────────────────
def eti(morphology, feret, aspect, area, unit="μm"):
    return compute_eti(morphology, feret, aspect, area, unit)


# ══════════════════════════════════════════════════════════════════════════
# 1. Threat level coverage — at least one example per level
# ══════════════════════════════════════════════════════════════════════════

class TestThreatLevels:

    def test_critical_small_high_aspect_fiber(self):
        """
        Tiny (5 μm) fiber with very high aspect ratio → Critical.
        Small size + fiber morphology + elongation drive score above 75.
        """
        result = eti("Fiber", feret=5.0, aspect=25.0, area=20.0)
        assert result.threat_level == "Critical", (
            f"Expected Critical, got {result.threat_level} (score={result.score})"
        )
        assert result.score >= 75.0

    def test_high_medium_fiber(self):
        """
        Medium-sized (150 μm) fiber with moderate aspect ratio → High.
        Feret=150 μm reduces the size sub-score enough to push below Critical.
        """
        result = eti("Fiber", feret=150.0, aspect=5.0, area=600.0)
        assert result.threat_level == "High", (
            f"Expected High, got {result.threat_level} (score={result.score})"
        )
        assert 50.0 <= result.score < 75.0

    def test_moderate_large_fragment(self):
        """
        Large (300 μm) fragment, low elongation → Moderate.
        """
        result = eti("Fragment", feret=300.0, aspect=1.5, area=8000.0)
        assert result.threat_level == "Moderate", (
            f"Expected Moderate, got {result.threat_level} (score={result.score})"
        )
        assert 25.0 <= result.score < 50.0

    def test_low_large_film(self):
        """
        Very large (450 μm) film particle, near-circular → Low.
        """
        result = eti("Film", feret=450.0, aspect=1.2, area=500.0)
        assert result.threat_level == "Low", (
            f"Expected Low, got {result.threat_level} (score={result.score})"
        )
        assert result.score < 25.0


# ══════════════════════════════════════════════════════════════════════════
# 2. Morphology ordering: Fiber > Fragment > Film at equal size/shape
# ══════════════════════════════════════════════════════════════════════════

class TestMorphologyOrdering:

    def test_fiber_beats_fragment(self):
        kwargs = dict(feret=100.0, aspect=3.0, area=1000.0)
        assert eti("Fiber", **kwargs).score > eti("Fragment", **kwargs).score

    def test_fragment_beats_film(self):
        kwargs = dict(feret=100.0, aspect=3.0, area=1000.0)
        assert eti("Fragment", **kwargs).score > eti("Film", **kwargs).score


# ══════════════════════════════════════════════════════════════════════════
# 3. Size ordering: smaller particle → higher risk at equal morphology
# ══════════════════════════════════════════════════════════════════════════

class TestSizeOrdering:

    def test_small_particle_higher_risk(self):
        kwargs = dict(morphology="Fragment", aspect=2.0, area=500.0)
        small  = eti(**kwargs, feret=10.0)
        large  = eti(**kwargs, feret=400.0)
        assert small.score > large.score

    def test_very_large_particle_near_zero_size_score(self):
        result = eti("Fragment", feret=600.0, aspect=1.5, area=5000.0)
        # size score should be 0 (feret >= SIZE_REFERENCE_UM)
        assert result.breakdown["size_score"] == 0.0


# ══════════════════════════════════════════════════════════════════════════
# 4. Score bounds
# ══════════════════════════════════════════════════════════════════════════

class TestScoreBounds:

    def test_score_never_below_zero(self):
        result = eti("Film", feret=9999.0, aspect=1.0, area=0.0)
        assert result.score >= 0.0

    def test_score_never_above_100(self):
        # Pathological: feret=0, aspect=1000, area=1e9
        result = eti("Fiber", feret=0.001, aspect=1000.0, area=1e9)
        assert result.score <= 100.0

    def test_score_is_float(self):
        result = eti("Fragment", feret=50.0, aspect=2.0, area=1000.0)
        assert isinstance(result.score, float)


# ══════════════════════════════════════════════════════════════════════════
# 5. Pixel mode (no scale calibration)
# ══════════════════════════════════════════════════════════════════════════

class TestPixelMode:

    def test_pixel_mode_sets_approximate_flag(self):
        result = eti("Fiber", feret=50.0, aspect=4.0, area=200.0, unit="px")
        assert result.approximate is True

    def test_um_mode_clears_approximate_flag(self):
        result = eti("Fiber", feret=50.0, aspect=4.0, area=200.0, unit="μm")
        assert result.approximate is False

    def test_pixel_and_um_differ_in_score(self):
        """
        Same raw numbers but different units → different reference values
        → different scores.
        """
        r_um = eti("Fragment", feret=100.0, aspect=2.0, area=3000.0, unit="μm")
        r_px = eti("Fragment", feret=100.0, aspect=2.0, area=3000.0, unit="px")
        # pixel reference is smaller → size score saturates at 0 sooner
        assert r_um.score != r_px.score


# ══════════════════════════════════════════════════════════════════════════
# 6. Validation: unknown morphology raises ValueError
# ══════════════════════════════════════════════════════════════════════════

class TestValidation:

    def test_unknown_morphology_raises(self):
        with pytest.raises(ValueError, match="Unknown morphology"):
            eti("Sphere", feret=50.0, aspect=2.0, area=1000.0)

    def test_morphology_case_insensitive(self):
        # Should not raise — normalized to title case internally
        result = eti("fiber", feret=50.0, aspect=4.0, area=500.0)
        assert result.threat_level in {"Low", "Moderate", "High", "Critical"}


# ══════════════════════════════════════════════════════════════════════════
# 7. Breakdown dict has required keys
# ══════════════════════════════════════════════════════════════════════════

class TestBreakdown:

    REQUIRED_KEYS = {
        "morphology_score", "size_score", "elongation_score", "area_score",
        "weight_morphology", "weight_size", "weight_elongation", "weight_area",
    }

    def test_breakdown_has_all_keys(self):
        result = eti("Film", feret=100.0, aspect=5.0, area=2000.0)
        assert self.REQUIRED_KEYS.issubset(result.breakdown.keys())

    def test_weights_sum_to_one(self):
        result = eti("Fragment", feret=80.0, aspect=2.0, area=1000.0)
        total = (
            result.breakdown["weight_morphology"] +
            result.breakdown["weight_size"]       +
            result.breakdown["weight_elongation"] +
            result.breakdown["weight_area"]
        )
        assert abs(total - 1.0) < 1e-9
