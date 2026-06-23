# Microplastic Morphology Classifier — System Design

## Table of Contents
1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Component Breakdown](#3-component-breakdown)
4. [Data Flow](#4-data-flow)
5. [ML Pipeline](#5-ml-pipeline)
6. [Frontend Pages](#6-frontend-pages)
7. [API Reference](#7-api-reference)
8. [Database Schema](#8-database-schema)
9. [Security & Integrity](#9-security--integrity)
10. [Running the Application](#10-running-the-application)
11. [Project Structure](#11-project-structure)

---

## 1. Overview

MicroClassify is an end-to-end environmental intelligence platform for detecting, classifying, and risk-scoring microplastic particles from microscope images.

### What it does
- Accepts a microscope image upload
- Runs **real OpenCV contour detection** to measure particle geometry (Feret diameter, Martin's diameter, aspect ratio, solidity, circularity)
- Classifies the particle morphology into **Fiber / Film / Fragment / Pellet** using a fine-tuned **MobileNetV2 CNN**
- Generates a **Grad-CAM heatmap** showing which part of the image drove the classification
- Computes an **Ecological Threat Index (ETI)** score (0–100) based on morphology, size, elongation, and surface area
- Calls **Gemini AI** to generate a plain-language stakeholder report from the structured results
- Stores every result in a **SQLite database** with an optional human-correction field for retraining
- Logs a **SHA-256 integrity hash** (image bytes + result JSON) to an append-only file

### What it does NOT do (honest limitations)
- The model was trained on synthetic placeholder data until a real Kaggle dataset download completes. Accuracy numbers on synthetic data are not meaningful. Re-run `train.py` + `evaluate.py` after downloading real data.
- The ETI scoring formula is a heuristic prototype, not a literature-calibrated risk model.
- The SHA-256 hash is tamper-evident local logging, not blockchain.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                            │
│   React SPA  (Landing → Upload → Results → Dashboard)  │
└───────────────────────┬─────────────────────────────────┘
                        │  HTTP  POST /api/analyze
                        ▼
┌─────────────────────────────────────────────────────────┐
│            Express Server  (server.ts)  :3000           │
│                                                         │
│  1. Receives multipart image upload                     │
│  2. Proxies to FastAPI ML service                       │
│  3. Calls Gemini for stakeholder report                 │
│  4. Computes SHA-256 hash → appends to hash_log.jsonl   │
│  5. Returns combined JSON to browser                    │
└───────────────────────┬─────────────────────────────────┘
                        │  HTTP  POST /classify
                        ▼
┌─────────────────────────────────────────────────────────┐
│          FastAPI ML Service  (ml-service/api)  :8001    │
│                                                         │
│  Step 1 ── OpenCV feature extraction                    │
│             Feret diameter, Martin's diameter,          │
│             aspect ratio, area, perimeter,              │
│             elongation, solidity, circularity           │
│                                                         │
│  Step 2 ── MobileNetV2 CNN classification               │
│             → Fiber / Film / Fragment / Pellet          │
│             → confidence scores per class               │
│                                                         │
│  Step 3 ── Grad-CAM heatmap (base64 PNG)                │
│             Target layer: model.features[18][0]         │
│                                                         │
│  Step 4 ── ETI scoring (pure function)                  │
│             Score 0–100, threat level label             │
│                                                         │
│  Step 5 ── Persist to SQLite (analyses.db)              │
│                                                         │
│  Returns structured JSON                                │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  analyses.db    │  SQLite — every result stored
              │  hash_log.jsonl │  append-only SHA-256 log
              └─────────────────┘
```

---

## 3. Component Breakdown

### 3.1 Express Server (`server.ts`)
| Responsibility | Detail |
|---|---|
| Static file serving | Serves the built React SPA in production via `express.static` |
| Dev proxy | Vite dev middleware in development mode |
| Image ingestion | `multer` — accepts multipart image, stores in memory buffer |
| ML proxy | `fetch` → FastAPI `/classify` with image + scale param |
| Gemini reporting | Calls `gemini-2.0-flash` with structured ML result → plain English report |
| Integrity logging | `crypto.createHash('sha256')` over image bytes + result JSON → `hash_log.jsonl` |

### 3.2 FastAPI ML Service (`ml-service/api/main.py`)
| Module | File | Purpose |
|---|---|---|
| Feature extraction | `scripts/feature_extraction.py` | OpenCV contour → particle geometry |
| CNN classifier | Model loaded from `models/best_model.pt` | MobileNetV2 inference |
| Grad-CAM | `scripts/gradcam.py` | Visual explanation heatmap |
| ETI scoring | `api/eti_scoring.py` | Risk index calculation |
| Database | `api/database.py` | SQLite persistence |

### 3.3 React Frontend (`src/`)
| Page | Route | Purpose |
|---|---|---|
| `LandingPage` | `/` | Hero, metrics, how-it-works, Three.js particle animation |
| `UploadPage` | `/upload` | Drag-and-drop image upload, scale calibration, analysis trigger |
| `AnalysisPage` | `/results` | Image viewer, Grad-CAM toggle, classification, measurements, ETI gauge, Gemini report |
| `DashboardPage` | `/dashboard` | Analysis history, ETI trend chart, alerts panel, sample table |

---

## 4. Data Flow

```
User drops image
      │
      ▼
UploadPage.tsx
  POST /api/analyze  (multipart: image + scale_um_per_px)
      │
      ▼
server.ts
  → saves image to memory buffer
  → POST http://localhost:8001/classify  (multipart)
      │
      ▼
FastAPI /classify
  1. OpenCV: preprocess → CLAHE → Gaussian blur → Otsu threshold
             → find contours → largest contour → measurements
  2. MobileNetV2: forward pass → softmax probabilities
  3. Grad-CAM: backward pass on predicted class → weighted activation map → PNG
  4. ETI: compute_eti(morphology, feret, aspect_ratio, area, unit)
  5. SQLite: INSERT into analyses table
  ← returns ClassificationResponse JSON
      │
      ▼
server.ts
  → calls Gemini API with structured result (no image, no heatmap)
  → Gemini returns plain-language paragraph
  → SHA-256 = hash(image_bytes + result_json)
  → appends {hash, timestamp, class, eti_score} to hash_log.jsonl
  ← returns combined JSON to browser
      │
      ▼
AnalysisPage.tsx
  renders: image | heatmap toggle | classification | measurements | ETI gauge | Gemini report
```

---

## 5. ML Pipeline

### 5.1 Dataset
- **Source**: `sivajyothis/microplastic-dataset` (Kaggle, CC BY 4.0)
- **Format**: YOLOv8 detection labels → converted to cropped classification images
- **Classes**: Fiber, Film, Fragment, Pellet
- **Size**: 4,136 real particle crops (balanced ~25% each)
- **Splits**: Pre-split by Kaggle (train 315 imgs / val 37 imgs / test 9 imgs of full scenes → 3585 / 453 / 98 crops)
- **Converter script**: `ml-service/scripts/convert_yolo_to_crops.py`

### 5.2 Model
- **Backbone**: MobileNetV2 pretrained on ImageNet
- **Why MobileNetV2**: ~3.4M params (vs ResNet18's 11.7M), fast on CPU, separable convolutions suitable for edge deployment
- **Head**: `Dropout(0.3) → Linear(1280, 4)`
- **Training strategy**:
  - Phase A (warm-up, 8 epochs): freeze backbone, train head only, LR=1e-3
  - Phase B (fine-tune, 30 epochs): unfreeze last 3 InvertedResidual blocks, AdamW LR=3e-4, cosine annealing
- **Augmentation**: random flip, rotation ±30°, color jitter
- **Saved to**: `ml-service/models/best_model.pt`

### 5.3 Feature Extraction (OpenCV)
All measurements are computed from real pixel geometry via `cv2.findContours`:

| Metric | Method |
|---|---|
| Feret diameter | Longest side of `cv2.minAreaRect` bounding box |
| Martin's diameter | Chord at the midpoint perpendicular to major axis |
| Aspect ratio | Feret / Martin |
| Area | `cv2.contourArea` |
| Perimeter | `cv2.arcLength` |
| Elongation | `1 - (minor_axis / major_axis)` from fitted ellipse |
| Solidity | contour area / convex hull area |
| Circularity | `4π × area / perimeter²` |

### 5.4 ETI Scoring Formula
```
ETI = 100 × (
  0.35 × morphology_score    # Fiber=1.0, Fragment=0.65, Film=0.45, Pellet=0.55
+ 0.30 × size_score          # max(0, 1 - feret / 500μm)
+ 0.25 × elongation_score    # min(1, (aspect_ratio - 1) / 10)
+ 0.10 × area_score          # min(1, area / 50000μm²)
)

Threat levels: [0,25) Low | [25,50) Moderate | [50,75) High | [75,100] Critical
```
> ⚠ Heuristic weighting — not calibrated against toxicology literature.

### 5.5 Grad-CAM
- Target layer: `model.features[18][0]` (last spatial conv before global average pooling)
- Hook captures forward activations and backward gradients
- Importance weights = global average of gradients over spatial dims
- CAM = ReLU(weighted sum of activation maps) → upscaled to image size → jet colormap overlay

---

## 6. Frontend Pages

### Landing Page
- Three.js particle animation (fiber/fragment/film 3D meshes floating with mouse parallax)
- Hero with primary/secondary CTAs
- Metrics strip (total samples, accuracy, morphology classes)
- "How it works" 4-step cascade cards
- Glassmorphism design system (Stitch "Luminous Analytics" tokens)

### Upload Page
- Drag-and-drop or browse file input (TIFF/JPEG/PNG)
- Scale calibration input (μm/px) with stepper
- Sample site ID and procedural notes fields
- Animated processing overlay with phase-by-phase status text and progress bar
- Real API call to `POST /api/analyze`

### Analysis Results Page
- Side-by-side original image + Grad-CAM heatmap toggle
- Classification card: morphology class, confidence, probability bars per class
- Geometric measurements table (Feret, Martin's, aspect ratio, area, perimeter)
- ETI gauge (SVG arc, color-coded by threat level)
- Gemini stakeholder report (Markdown rendered)
- SHA-256 integrity hash footer

### Dashboard Page
- 4 stat cards: total samples, average ETI, high/critical count, most common morphology
- ETI trend area chart (Recharts, 30-day window)
- Filter bar: date range, threat level, morphology
- Sortable sample table with status badges
- Recent alerts panel (right sidebar)

---

## 7. API Reference

### Express (port 3000)

#### `POST /api/analyze`
**Input**: `multipart/form-data`
| Field | Type | Required | Description |
|---|---|---|---|
| `image` | File | Yes | JPEG/PNG/TIFF microscope image |
| `scale_um_per_px` | number | No | μm per pixel calibration |

**Response**:
```json
{
  "features": {
    "feret_diameter": 95.2,
    "martin_diameter": 7.1,
    "aspect_ratio": 13.4,
    "area": 612.0,
    "perimeter": 201.3,
    "elongation": 0.95,
    "solidity": 0.87,
    "circularity": 0.19,
    "unit": "μm",
    "scale_um_per_px": 1.5,
    "extraction_ok": true
  },
  "predicted_class": "Fiber",
  "confidence": 0.912,
  "class_probabilities": { "Fiber": 0.912, "Film": 0.055, "Fragment": 0.023, "Pellet": 0.01 },
  "gradcam_heatmap_b64": "<base64 PNG>",
  "eti": {
    "score": 78.4,
    "threat_level": "Critical",
    "breakdown": { ... },
    "approximate": false
  },
  "stakeholderReport": "The analyzed sample exhibits...",
  "integrityHash": "sha256hex...",
  "hashNote": "SHA-256(image bytes + result JSON). Stored in ml-service/hash_log.jsonl.",
  "timestamp": "2024-10-24T10:30:00.000Z",
  "imageUrl": "data:image/jpeg;base64,...",
  "model_source": "kaggle_yolo"
}
```

#### `GET /api/health`
Returns status of Express server and ML service reachability.

### FastAPI (port 8001)

#### `POST /classify`
Same as above minus `stakeholderReport`, `integrityHash`, `imageUrl`.

#### `GET /health`
```json
{ "status": "ok", "model_loaded": true, "classes": ["Fiber","Film","Fragment","Pellet"] }
```

---

## 8. Database Schema

**File**: `ml-service/data/analyses.db` (SQLite)

```sql
CREATE TABLE analyses (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at       TEXT,         -- ISO-8601 UTC
  image_path       TEXT,         -- filename or temp path
  integrity_hash   TEXT,         -- SHA-256

  -- OpenCV features --
  unit             TEXT,         -- "μm" or "px"
  scale_um_per_px  REAL,
  feret_diameter   REAL,
  martin_diameter  REAL,
  aspect_ratio     REAL,
  area             REAL,
  perimeter        REAL,
  elongation       REAL,
  solidity         REAL,
  circularity      REAL,

  -- Classification --
  predicted_class  TEXT,         -- Fiber/Film/Fragment/Pellet
  confidence       REAL,
  fiber_prob       REAL,
  film_prob        REAL,
  fragment_prob    REAL,
  model_source     TEXT,

  -- ETI --
  eti_score        REAL,
  threat_level     TEXT,

  -- Human feedback (for retraining) --
  corrected_label  TEXT          -- NULL until reviewed
);
```

Export for retraining:
```bash
python ml-service/scripts/export_for_retraining.py
# → ml-service/results/retraining_export.csv
```

---

## 9. Security & Integrity

| Mechanism | Implementation |
|---|---|
| Image integrity | SHA-256 over raw image bytes + result JSON. Stored in `ml-service/hash_log.jsonl` (append-only). Returned in API response as `integrityHash`. |
| No secrets in frontend | Gemini API key stays server-side in `.env` only, never exposed to browser |
| Input validation | FastAPI `UploadFile` + Pydantic response models enforce schema |
| CORS | Express CORS middleware — restrict origins in production |

---

## 10. Running the Application

### Prerequisites
- **Node.js** ≥ 18
- **Python** 3.10+
- **npm** packages installed (`node_modules/` present)
- **Python packages** installed (`pip install -r ml-service/requirements.txt`)
- A `.env` file with your Gemini API key (see `.env.example`)

### Step 1 — Set your Gemini API key
Open `.env` and replace the placeholder:
```
GEMINI_API_KEY="your_actual_gemini_api_key_here"
```
Get a free key at: https://aistudio.google.com/app/apikey

### Step 2 — Start the Python ML service
Open **Terminal 1**:
```bash
cd "c:\Users\DELL\OneDrive\New folder\Microplastic Classifier"
python -m uvicorn ml-service.api.main:app --port 8001 --reload
```
You should see:
```
[startup] Model loaded. Classes: ['Fiber', 'Film', 'Fragment', 'Pellet']
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 3 — Start the Express + Vite dev server
Open **Terminal 2**:
```bash
cd "c:\Users\DELL\OneDrive\New folder\Microplastic Classifier"
npm run dev
```
You should see:
```
Server running on http://localhost:3000
ML service URL → http://localhost:8001
```

### Step 4 — Open the app
Navigate to: **http://localhost:3000**

---

### Quick health check
```bash
# Check Express is up
curl http://localhost:3000/api/health

# Check ML service is up
curl http://localhost:8001/health
```

---

### Run all tests
```bash
# ETI unit tests (18 tests) + API integration tests (6 tests)
python -m pytest ml-service/tests/ -v

# TypeScript type check
node node_modules/typescript/bin/tsc --noEmit
```

---

### Rebuild the model on real data (when Kaggle token is ready)
```bash
# 1. Download + crop dataset
python ml-service/scripts/download_dataset.py --clean-splits
python ml-service/scripts/convert_yolo_to_crops.py

# 2. Train
python ml-service/scripts/train.py

# 3. Evaluate on test set (these are the REAL accuracy numbers)
python ml-service/scripts/evaluate.py
# → results saved to ml-service/results/metrics.json
```

---

## 11. Project Structure

```
Microplastic Classifier/
│
├── server.ts                    ← Express server (API gateway + Gemini)
├── index.html                   ← SPA shell
├── package.json
├── vite.config.ts
├── tsconfig.json
├── .env                         ← GEMINI_API_KEY (not committed)
├── .env.example
│
├── src/                         ← React frontend
│   ├── main.tsx
│   ├── App.tsx                  ← Router / page state
│   ├── index.css                ← Stitch design tokens + glass-panel
│   ├── components/
│   │   ├── Navbar.tsx
│   │   └── ETIGauge.tsx
│   └── pages/
│       ├── LandingPage.tsx      ← Hero + Three.js + How it works
│       ├── UploadPage.tsx       ← Upload form + processing overlay
│       ├── AnalysisPage.tsx     ← Results + Grad-CAM + ETI
│       └── DashboardPage.tsx    ← History + charts + alerts
│
└── ml-service/
    ├── requirements.txt
    ├── hash_log.jsonl           ← Append-only SHA-256 log
    │
    ├── scripts/
    │   ├── download_dataset.py      ← Phase 1: Kaggle/ASU/synthetic
    │   ├── convert_yolo_to_crops.py ← YOLO bbox → classification crops
    │   ├── feature_extraction.py    ← Phase 2: OpenCV measurements
    │   ├── train.py                 ← Phase 3: MobileNetV2 training
    │   ├── evaluate.py              ← Phase 3: test-set metrics
    │   ├── gradcam.py               ← Phase 4: Grad-CAM heatmaps
    │   └── export_for_retraining.py ← Phase 8: CSV export
    │
    ├── api/
    │   ├── main.py              ← FastAPI /classify endpoint
    │   ├── eti_scoring.py       ← Phase 5: ETI pure function
    │   └── database.py          ← Phase 8: SQLite schema + queries
    │
    ├── models/
    │   ├── best_model.pt        ← Trained weights (not in git)
    │   └── class_names.json     ← ["Fiber","Film","Fragment","Pellet"]
    │
    ├── data/
    │   ├── splits/              ← train/val/test image folders (not in git)
    │   └── raw/                 ← downloaded datasets (not in git)
    │
    ├── results/
    │   ├── metrics.json         ← Real test-set accuracy (after evaluate.py)
    │   ├── training_log.json    ← Per-epoch loss/accuracy
    │   ├── dataset_manifest.json
    │   └── gradcam_examples/    ← Sample heatmap PNGs
    │
    └── tests/
        ├── test_eti.py          ← 18 ETI unit tests
        └── test_api.py          ← 6 FastAPI integration tests
```
