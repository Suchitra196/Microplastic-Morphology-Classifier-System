"""
Phase 6 — FastAPI Inference Service
=====================================
POST /classify
  - Accepts: multipart/form-data with 'image' (file) + 'scale_um_per_px' (float, optional)
  - Returns: ClassificationResponse JSON

The service loads the model once at startup (via lifespan) and keeps
it in memory for subsequent requests.

Run with:
  uvicorn ml-service.api.main:app --port 8001 --reload
  (from the repo root)

Or directly:
  python ml-service/api/main.py
"""

from __future__ import annotations

import base64
import json
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from torchvision import models

# ── path setup ────────────────────────────────────────────────────────────
API_DIR     = Path(__file__).resolve().parent
ML_SERVICE  = API_DIR.parent
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(ML_SERVICE / "scripts"))

from eti_scoring import compute_eti, ETIResult        # noqa: E402
from feature_extraction import extract_features       # noqa: E402
from gradcam import GradCAM, overlay_heatmap, TF      # noqa: E402
from database import AnalysisDB                       # noqa: E402

_db = AnalysisDB()

MODELS_DIR = ML_SERVICE / "models"
DEVICE     = torch.device("cpu")

# ── app state ─────────────────────────────────────────────────────────────
class AppState:
    model:       Optional[nn.Module]   = None
    class_names: Optional[list[str]]   = None


state = AppState()


def _load_model():
    cn_path = MODELS_DIR / "class_names.json"
    if not cn_path.exists():
        raise FileNotFoundError(
            "class_names.json not found. Run train.py first."
        )
    state.class_names = json.loads(cn_path.read_text())
    num_classes = len(state.class_names)

    m = models.mobilenet_v2(weights=None)
    in_features = m.classifier[1].in_features
    m.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes),
    )
    weights_path = MODELS_DIR / "best_model.pt"
    if not weights_path.exists():
        raise FileNotFoundError(
            "best_model.pt not found. Run train.py first."
        )
    m.load_state_dict(torch.load(weights_path, map_location=DEVICE))
    m.to(DEVICE)
    m.eval()
    state.model = m


# ── lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    print(f"[startup] Model loaded. Classes: {state.class_names}")
    yield
    # cleanup (nothing needed for CPU inference)


# ── FastAPI app ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Microplastic Classifier ML Service",
    description=(
        "OpenCV feature extraction + MobileNetV2 classification + "
        "Grad-CAM + ETI scoring"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ── response schema ───────────────────────────────────────────────────────
class FeatureResult(BaseModel):
    feret_diameter:     float
    martin_diameter:    float
    aspect_ratio:       float
    area:               float
    perimeter:          float
    elongation:         float
    solidity:           float
    circularity:        float
    unit:               str
    scale_um_per_px:    Optional[float]
    extraction_ok:      bool
    error:              Optional[str] = None


class ETIOutput(BaseModel):
    score:        float
    threat_level: str
    breakdown:    dict
    approximate:  bool


class ClassificationResponse(BaseModel):
    # CV features
    features:           FeatureResult

    # ML classification
    predicted_class:    str
    confidence:         float
    class_probabilities: dict[str, float]

    # Grad-CAM heatmap (base64-encoded PNG)
    gradcam_heatmap_b64: str

    # ETI
    eti:                ETIOutput

    # Metadata
    model_source:       str   # "synthetic_placeholder" or real dataset name
    scale_um_per_px:    Optional[float]


# ── /classify endpoint ────────────────────────────────────────────────────
@app.post("/classify", response_model=ClassificationResponse)
async def classify(
    image:           UploadFile = File(..., description="Microscope image (JPEG/PNG)"),
    scale_um_per_px: Optional[float] = Form(
        default=None,
        description="μm per pixel calibration value. Omit if unknown.",
    ),
):
    if state.model is None or state.class_names is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Save upload to a temp file (OpenCV needs a file path)
    contents = await image.read()
    with tempfile.NamedTemporaryFile(
        suffix=Path(image.filename or "image.jpg").suffix, delete=False
    ) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        # ── 1. Feature extraction ─────────────────────────────────────
        features = extract_features(tmp_path, scale_um_per_px=scale_um_per_px)
        if not features.extraction_ok:
            raise HTTPException(
                status_code=422,
                detail=f"Feature extraction failed: {features.error}",
            )

        # ── 2. CNN classification + Grad-CAM ──────────────────────────
        from PIL import Image as PILImage
        pil_img = PILImage.open(tmp_path).convert("RGB")
        tensor  = TF(pil_img).unsqueeze(0).to(DEVICE)

        target_layer = state.model.features[18][0]
        gcam = GradCAM(state.model, target_layer)
        cam, pred_idx, probs = gcam.generate(tensor)
        gcam.remove_hooks()

        pred_class   = state.class_names[pred_idx]
        confidence   = float(probs[pred_idx])
        class_probs  = {
            state.class_names[i]: round(float(p), 4)
            for i, p in enumerate(probs)
        }

        # ── 3. Grad-CAM heatmap → base64 ─────────────────────────────
        import cv2
        orig_bgr = cv2.resize(cv2.imread(str(tmp_path)), (224, 224))
        heatmap  = overlay_heatmap(orig_bgr, cam, alpha=0.45)
        _, buf   = cv2.imencode(".png", heatmap)
        heatmap_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

        # ── 4. ETI scoring ────────────────────────────────────────────
        eti_result: ETIResult = compute_eti(
            morphology     = pred_class,
            feret_diameter = features.feret_diameter,
            aspect_ratio   = features.aspect_ratio,
            area           = features.area,
            unit           = features.unit,
        )

        # ── 5. Read dataset source for transparency ───────────────────
        manifest_path = ML_SERVICE / "results" / "dataset_manifest.json"
        model_source  = "unknown"
        if manifest_path.exists():
            manifest     = json.loads(manifest_path.read_text())
            model_source = manifest.get("source", "unknown")

    finally:
        tmp_path.unlink(missing_ok=True)

    response_obj = ClassificationResponse(
        features          = FeatureResult(**features.to_dict()),
        predicted_class   = pred_class,
        confidence        = round(confidence, 4),
        class_probabilities = class_probs,
        gradcam_heatmap_b64 = heatmap_b64,
        eti               = ETIOutput(**eti_result.to_dict()),
        model_source      = model_source,
        scale_um_per_px   = scale_um_per_px,
    )

    # Persist to DB (best-effort — don't fail the request if DB errors)
    try:
        _db.insert(response_obj.model_dump())
    except Exception as db_err:
        print(f"[DB] Insert failed (non-fatal): {db_err}")

    return response_obj


# ── health check ──────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status":      "ok",
        "model_loaded": state.model is not None,
        "classes":     state.class_names,
    }


# ── direct run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
