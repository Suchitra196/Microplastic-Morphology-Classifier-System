"""
Phase 6 — FastAPI integration test
Spins up the app with TestClient (no real server needed) and
verifies the /classify endpoint shape and /health endpoint.
Run with: python -m pytest ml-service/tests/test_api.py -v
"""

import sys
import base64
from pathlib import Path
import pytest

# Allow importing ml-service.api.*
ML_SERVICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE / "api"))
sys.path.insert(0, str(ML_SERVICE / "scripts"))

from fastapi.testclient import TestClient
from main import app   # imports the FastAPI app

# TestClient used as a context manager so the lifespan fires
# (loads the model at startup, same as a real server would)
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# ── pick a real test image ────────────────────────────────────────────────
TEST_IMAGES = {
    cls: sorted((ML_SERVICE / "data" / "splits" / "test" / cls).glob("*.png"))[0]
    for cls in ["Fiber", "Film", "Fragment"]
    if sorted((ML_SERVICE / "data" / "splits" / "test" / cls).glob("*.png"))
}


@pytest.mark.parametrize("cls", list(TEST_IMAGES.keys()))
def test_classify_response_shape(client, cls):
    """POST /classify returns the expected JSON structure."""
    img_path = TEST_IMAGES[cls]
    with open(img_path, "rb") as f:
        resp = client.post(
            "/classify",
            files={"image": (img_path.name, f, "image/png")},
            data={"scale_um_per_px": "1.5"},
        )
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"

    data = resp.json()

    # ── top-level keys ────────────────────────────────────────────────
    required_keys = {
        "features", "predicted_class", "confidence",
        "class_probabilities", "gradcam_heatmap_b64",
        "eti", "model_source", "scale_um_per_px",
    }
    assert required_keys.issubset(data.keys()), (
        f"Missing keys: {required_keys - set(data.keys())}"
    )

    # ── predicted_class is one of the known classes ───────────────────
    assert data["predicted_class"] in ("Fiber", "Film", "Fragment")

    # ── confidence is a float in [0, 1] ──────────────────────────────
    assert 0.0 <= data["confidence"] <= 1.0

    # ── class_probabilities has 3 classes and sums to ~1 ─────────────
    probs = data["class_probabilities"]
    assert len(probs) == 3
    assert abs(sum(probs.values()) - 1.0) < 0.01

    # ── gradcam_heatmap_b64 is a non-empty base64 string ─────────────
    raw = base64.b64decode(data["gradcam_heatmap_b64"])
    assert len(raw) > 100, "Heatmap PNG is suspiciously small"

    # ── features sub-object ───────────────────────────────────────────
    feat = data["features"]
    assert feat["extraction_ok"] is True
    assert feat["feret_diameter"] > 0
    assert feat["martin_diameter"] > 0
    assert feat["unit"] == "μm"

    # ── ETI sub-object ────────────────────────────────────────────────
    eti = data["eti"]
    assert 0.0 <= eti["score"] <= 100.0
    assert eti["threat_level"] in ("Low", "Moderate", "High", "Critical")
    assert isinstance(eti["breakdown"], dict)


def test_classify_without_scale(client):
    """Omitting scale_um_per_px should still succeed with unit='px'."""
    cls = list(TEST_IMAGES.keys())[0]
    img_path = TEST_IMAGES[cls]
    with open(img_path, "rb") as f:
        resp = client.post(
            "/classify",
            files={"image": (img_path.name, f, "image/png")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["features"]["unit"] == "px"
    assert data["eti"]["approximate"] is True


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert len(data["classes"]) == 3


def test_classify_no_image_returns_422(client):
    resp = client.post("/classify")
    assert resp.status_code == 422   # FastAPI validation error
