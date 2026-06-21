"""
Phase 2 — OpenCV Feature Extraction Module
===========================================
Computes real morphological measurements from a microscope image using
OpenCV contour detection. No LLM involvement — all measurements are
derived from actual pixel geometry.

Measurements returned (all in μm if scale_um_per_px is provided,
otherwise in pixels):
  - feret_diameter    : longest dimension of the minimum-area bounding box
  - martin_diameter   : width of the contour measured at its midpoint
                        (perpendicular to the major axis)
  - aspect_ratio      : feret_diameter / martin_diameter
  - area              : contour area (from cv2.contourArea)
  - perimeter         : contour perimeter (from cv2.arcLength)
  - elongation        : 1 - (minor_axis / major_axis) of fitted ellipse
                        (0 = circle, →1 = very elongated)
  - solidity          : contour_area / convex_hull_area  (1 = convex particle)
  - circularity       : 4π·area / perimeter²  (1 = perfect circle)

scale_um_per_px : float
    μm per pixel.  If None, measurements are returned in pixels.
    Typical benchtop microscope at 10× objective: ~1–2 μm/px.
    At 40× objective: ~0.25 μm/px.
    Pass None when the calibration value is unknown.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


# ── data class ──────────────────────────────────────────────────────────────
@dataclass
class ParticleFeatures:
    # measurement values
    feret_diameter: float       # longest dimension (μm or px)
    martin_diameter: float      # midpoint width (μm or px)
    aspect_ratio: float         # feret / martin
    area: float                 # μm² or px²
    perimeter: float            # μm or px
    elongation: float           # 0–1
    solidity: float             # 0–1
    circularity: float          # 0–1

    # metadata
    unit: str                   # "μm" or "px"
    scale_um_per_px: Optional[float]
    contour_point_count: int
    image_path: str
    extraction_ok: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def pretty(self) -> str:
        lines = [
            f"  Image       : {Path(self.image_path).name}",
            f"  Unit        : {self.unit}",
            f"  Scale       : {self.scale_um_per_px} μm/px" if self.scale_um_per_px
                             else "  Scale       : not provided (values in pixels)",
            f"  Feret diam. : {self.feret_diameter:.2f} {self.unit}",
            f"  Martin diam.: {self.martin_diameter:.2f} {self.unit}",
            f"  Aspect ratio: {self.aspect_ratio:.3f}",
            f"  Area        : {self.area:.2f} {self.unit}²",
            f"  Perimeter   : {self.perimeter:.2f} {self.unit}",
            f"  Elongation  : {self.elongation:.3f}  (0=circle → 1=very elongated)",
            f"  Solidity    : {self.solidity:.3f}  (1=convex)",
            f"  Circularity : {self.circularity:.3f}  (1=perfect circle)",
        ]
        if not self.extraction_ok:
            lines.append(f"  ⚠ Error     : {self.error}")
        return "\n".join(lines)


# ── preprocessing ────────────────────────────────────────────────────────────
def _preprocess(img_bgr: np.ndarray) -> np.ndarray:
    """
    Convert to grayscale → CLAHE contrast enhancement →
    Gaussian blur → Otsu threshold → morphological closing.
    Returns a binary mask (255 = particle).
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # CLAHE to handle uneven illumination (common in microscopy)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Blur to reduce noise before thresholding
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

    # Otsu's method — automatic threshold; works well for bimodal histograms
    # (bright background, dark particle) typical of bright-field microscopy.
    # invert so particles are white
    _, binary = cv2.threshold(
        blurred, 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    # Morphological closing to fill small holes inside the particle
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    return closed


def _martin_diameter(contour: np.ndarray, major_angle_deg: float) -> float:
    """
    Martin's diameter: the chord length that bisects the contour area,
    drawn perpendicular to the major axis at the centroid.

    Implementation:
      1. Rotate the contour so the major axis aligns with the x-axis.
      2. Find the y-range of the rotated contour.
      3. Measure the chord at y = midpoint (the Martin line).
    """
    M = cv2.moments(contour)
    if M["m00"] == 0:
        return 0.0

    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]

    # Rotate contour so major axis → horizontal
    angle_rad = np.deg2rad(major_angle_deg)
    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    pts = contour.reshape(-1, 2).astype(float)
    pts[:, 0] -= cx
    pts[:, 1] -= cy
    rot = np.column_stack([
        pts[:, 0] * cos_a + pts[:, 1] * sin_a,
        -pts[:, 0] * sin_a + pts[:, 1] * cos_a,
    ])

    y_vals = rot[:, 1]
    y_mid = (y_vals.min() + y_vals.max()) / 2.0

    # Find x-coordinates of contour points near the midline (within ±tolerance)
    tol = max(1.0, (y_vals.max() - y_vals.min()) * 0.05)
    near_mid = rot[np.abs(rot[:, 1] - y_mid) < tol, 0]

    if len(near_mid) < 2:
        return 0.0

    return float(near_mid.max() - near_mid.min())


# ── main extraction function ─────────────────────────────────────────────────
def extract_features(
    image_path: str | Path,
    scale_um_per_px: Optional[float] = None,
) -> ParticleFeatures:
    """
    Extract morphological features for the most prominent particle in the image.

    Parameters
    ----------
    image_path : path to the image file
    scale_um_per_px : calibration value (μm per pixel).
                      If None, results are in pixels.

    Returns
    -------
    ParticleFeatures dataclass
    """
    image_path = str(image_path)
    _err = lambda msg: ParticleFeatures(
        feret_diameter=0, martin_diameter=0, aspect_ratio=0,
        area=0, perimeter=0, elongation=0, solidity=0, circularity=0,
        unit="px", scale_um_per_px=scale_um_per_px,
        contour_point_count=0, image_path=image_path,
        extraction_ok=False, error=msg,
    )

    img = cv2.imread(image_path)
    if img is None:
        return _err(f"Could not read image: {image_path}")

    mask = _preprocess(img)

    # Find external contours only
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    if not contours:
        return _err("No contours found after thresholding")

    # Pick the largest contour by area — the most prominent particle
    contour = max(contours, key=cv2.contourArea)
    area_px = cv2.contourArea(contour)

    if area_px < 50:  # too small — likely noise
        return _err(f"Largest contour too small (area={area_px:.0f} px²) — likely noise")

    perimeter_px = cv2.arcLength(contour, closed=True)

    # ── Feret diameter via minimum-area bounding box ──────────────────────
    # cv2.minAreaRect returns (center, (w,h), angle)
    rect = cv2.minAreaRect(contour)
    box_w, box_h = rect[1]
    feret_px  = float(max(box_w, box_h))   # longest dimension
    minor_px  = float(min(box_w, box_h))   # shortest dimension
    major_angle = float(rect[2])            # degrees from horizontal

    # ── Martin's diameter ─────────────────────────────────────────────────
    martin_px = _martin_diameter(contour, major_angle)
    # fallback: use minor axis of bounding box if chord method fails
    if martin_px <= 0:
        martin_px = minor_px

    # ── Aspect ratio ──────────────────────────────────────────────────────
    aspect_ratio = feret_px / martin_px if martin_px > 0 else float("inf")

    # ── Elongation from fitted ellipse ────────────────────────────────────
    if len(contour) >= 5:
        ellipse = cv2.fitEllipse(contour)
        ell_w, ell_h = ellipse[1]
        major_ax = max(ell_w, ell_h)
        minor_ax = min(ell_w, ell_h)
        elongation = 1.0 - (minor_ax / major_ax) if major_ax > 0 else 0.0
    else:
        elongation = 1.0 - (minor_px / feret_px) if feret_px > 0 else 0.0

    # ── Solidity ──────────────────────────────────────────────────────────
    hull     = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity  = area_px / hull_area if hull_area > 0 else 0.0

    # ── Circularity ───────────────────────────────────────────────────────
    circularity = (
        (4 * np.pi * area_px) / (perimeter_px ** 2)
        if perimeter_px > 0 else 0.0
    )
    circularity = min(circularity, 1.0)  # clamp — numerical noise can push >1

    # ── Apply scale ───────────────────────────────────────────────────────
    s   = scale_um_per_px if scale_um_per_px is not None else 1.0
    unit = "μm" if scale_um_per_px is not None else "px"

    return ParticleFeatures(
        feret_diameter    = round(feret_px   * s,       4),
        martin_diameter   = round(martin_px  * s,       4),
        aspect_ratio      = round(aspect_ratio,         4),
        area              = round(area_px    * (s ** 2), 4),
        perimeter         = round(perimeter_px * s,     4),
        elongation        = round(elongation,            4),
        solidity          = round(solidity,              4),
        circularity       = round(circularity,           4),
        unit              = unit,
        scale_um_per_px   = scale_um_per_px,
        contour_point_count = len(contour),
        image_path        = image_path,
        extraction_ok     = True,
    )


# ── CLI / test runner ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run feature extraction on one or more images"
    )
    parser.add_argument("images", nargs="*",
                        help="Image paths (default: sample images from splits/train)")
    parser.add_argument("--scale", type=float, default=None,
                        help="μm per pixel calibration (default: report in pixels)")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()

    # default: grab 2 images per class from splits/train
    if not args.images:
        splits_dir = (
            Path(__file__).resolve().parent.parent / "data" / "splits" / "train"
        )
        sample_paths = []
        for cls in ["Fiber", "Fragment", "Film"]:
            cls_dir = splits_dir / cls
            imgs = sorted(cls_dir.glob("*.png"))[:2]
            sample_paths.extend(imgs)
        if not sample_paths:
            print("No images found. Run download_dataset.py first.")
            sys.exit(1)
        image_paths = [str(p) for p in sample_paths]
    else:
        image_paths = args.images

    print(f"\n── Feature Extraction Test ({'%.2f μm/px' % args.scale if args.scale else 'pixel units'}) ──")
    results = []
    for path in image_paths:
        feat = extract_features(path, scale_um_per_px=args.scale)
        results.append(feat.to_dict())
        if args.json:
            print(json.dumps(feat.to_dict(), indent=2))
        else:
            cls_name = Path(path).parent.name
            print(f"\n[{cls_name}]")
            print(feat.pretty())

    if not args.json:
        print(f"\n  Processed {len(results)} images.")
        ok  = sum(1 for r in results if r["extraction_ok"])
        err = len(results) - ok
        print(f"  ✓ Successful: {ok}   ✗ Failed: {err}")
