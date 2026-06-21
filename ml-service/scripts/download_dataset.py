"""
Phase 1 — Dataset Download & Organization Script
=================================================
Sources (in priority order):
  1. Kaggle: "zhongbinbin/microplastic-dataset-for-computer-vision"
             (requires ~/.kaggle/kaggle.json)
  2. Mendeley Data: doi:10.48349/ASU/ZCEM6W
             (ASU microplastics image collection — public, no auth)
  3. GitHub mirror: ymzhu19eee/dataset_microplastics
             (holography-based, fiber/fragment/pellet classes)

If none of the above are accessible (no Kaggle token, network issues),
the script falls back to building a *clearly-labelled synthetic dataset*
of procedurally-generated placeholder images per class so that all
downstream scripts (train, evaluate, gradcam) can run end-to-end.

The synthetic fallback is NOT used for any real accuracy metrics.
When the real dataset is available, re-run this script to replace it.

Output layout (torchvision ImageFolder-compatible):
  ml-service/data/splits/
      train/Fiber/     train/Fragment/     train/Film/
      val/Fiber/       val/Fragment/       val/Film/
      test/Fiber/      test/Fragment/      test/Film/

Random seed: 42 (fixed for reproducibility).
Split ratio: 70 / 15 / 15.
"""

import os
import sys
import json
import shutil
import random
import hashlib
import zipfile
import tarfile
import argparse
import requests
from pathlib import Path
from collections import Counter

# ── paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
ML_SERVICE   = SCRIPT_DIR.parent
DATA_DIR     = ML_SERVICE / "data"
RAW_DIR      = DATA_DIR / "raw"
SPLITS_DIR   = DATA_DIR / "splits"
RESULTS_DIR  = ML_SERVICE / "results"

CLASSES      = ["Fiber", "Fragment", "Film"]
SPLITS       = {"train": 0.70, "val": 0.15, "test": 0.15}
SEED         = 42
IMG_EXTS     = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# ── helpers ─────────────────────────────────────────────────────────────────
def ensure_dirs():
    for split in SPLITS:
        for cls in CLASSES:
            (SPLITS_DIR / split / cls).mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMG_EXTS


def split_and_copy(class_images: dict[str, list[Path]]):
    """
    Given {class_name: [image_paths]}, shuffle each class with a fixed seed,
    split 70/15/15, copy to SPLITS_DIR, and return per-split counts.
    """
    rng = random.Random(SEED)
    counts: dict[str, Counter] = {s: Counter() for s in SPLITS}

    for cls, images in class_images.items():
        rng.shuffle(images)
        n = len(images)
        n_train = round(n * SPLITS["train"])
        n_val   = round(n * SPLITS["val"])
        # remaining goes to test (avoids rounding drift)
        buckets = {
            "train": images[:n_train],
            "val":   images[n_train : n_train + n_val],
            "test":  images[n_train + n_val :],
        }
        for split, subset in buckets.items():
            dest_dir = SPLITS_DIR / split / cls
            dest_dir.mkdir(parents=True, exist_ok=True)
            for src in subset:
                dst = dest_dir / src.name
                # avoid name collisions
                if dst.exists():
                    stem  = src.stem
                    h     = hashlib.md5(str(src).encode()).hexdigest()[:6]
                    dst   = dest_dir / f"{stem}_{h}{src.suffix}"
                shutil.copy2(src, dst)
                counts[split][cls] += 1

    return counts


def print_distribution(counts: dict[str, Counter]):
    print("\n── Dataset split distribution ──────────────────────────────")
    total_all = 0
    for split in ["train", "val", "test"]:
        c = counts[split]
        total = sum(c.values())
        total_all += total
        print(f"\n  {split.upper()} ({total} images)")
        for cls in CLASSES:
            pct = 100 * c[cls] / total if total else 0
            bar = "█" * int(pct / 2)
            print(f"    {cls:<12} {c[cls]:>5}  {pct:5.1f}%  {bar}")
    print(f"\n  TOTAL: {total_all} images across all splits")
    print("────────────────────────────────────────────────────────────\n")
    # flag class imbalance (>2× ratio between classes in train)
    train_c = counts["train"]
    mx, mn = max(train_c.values()), min(train_c.values())
    if mn > 0 and mx / mn > 2.0:
        print(f"  ⚠  Class imbalance detected (max/min ratio = {mx/mn:.1f}×).")
        print("     Consider weighted loss or oversampling during training.\n")
    return total_all


def save_manifest(counts: dict[str, Counter], source: str):
    manifest = {
        "source": source,
        "seed": SEED,
        "splits": {s: dict(c) for s, c in counts.items()},
    }
    out = RESULTS_DIR / "dataset_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"  Manifest saved → {out}\n")


# ── source 1: Kaggle ────────────────────────────────────────────────────────
KAGGLE_DATASETS = [
    "zhongbinbin/microplastic-dataset-for-computer-vision",  # primary
    "suchitra196/microplastic-morphology-dataset",           # fallback
]
KAGGLE_EXE = Path(os.path.expanduser("~")) / "AppData/Roaming/Python/Python310/Scripts/kaggle.exe"


def try_kaggle() -> dict[str, list[Path]] | None:
    import subprocess
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print("  Kaggle token not found (~/.kaggle/kaggle.json). Skipping Kaggle.")
        return None

    exe = str(KAGGLE_EXE) if KAGGLE_EXE.exists() else "kaggle"

    for dataset_slug in KAGGLE_DATASETS:
        dest = RAW_DIR / "kaggle"
        dest.mkdir(exist_ok=True)
        print(f"  Trying Kaggle dataset: {dataset_slug} …")
        result = subprocess.run(
            [exe, "datasets", "download", "-d", dataset_slug,
             "--unzip", "-p", str(dest)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ✗ Kaggle download failed: {result.stderr.strip()}")
            continue

        # auto-detect class folders
        class_images = detect_class_folders(dest)
        if class_images:
            print(f"  ✓ Kaggle dataset downloaded and detected classes: "
                  f"{list(class_images.keys())}")
            return class_images

    return None


def detect_class_folders(root: Path) -> dict[str, list[Path]]:
    """
    Walk root looking for folder names that fuzzy-match our class names.
    Returns dict only when ≥2 classes are found.
    """
    CLASS_ALIASES = {
        "Fiber":    ["fiber", "fibre", "filament", "line"],
        "Fragment": ["fragment", "frag", "pellet", "sphere", "bead"],
        "Film":     ["film", "sheet", "foam", "flake"],
    }
    result: dict[str, list[Path]] = {}
    for folder in sorted(root.rglob("*")):
        if not folder.is_dir():
            continue
        name_lower = folder.name.lower()
        for cls, aliases in CLASS_ALIASES.items():
            if any(alias in name_lower for alias in aliases):
                imgs = [p for p in folder.iterdir() if is_image(p)]
                if imgs:
                    if cls not in result:
                        result[cls] = []
                    result[cls].extend(imgs)
    return result


# ── source 2: ASU Dataverse ─────────────────────────────────────────────────
ASU_API = (
    "https://dataverse.asu.edu/api/access/dataset/"
    ":persistentId/?persistentId=doi:10.48349/ASU/ZCEM6W"
)


def try_asu_dataverse() -> dict[str, list[Path]] | None:
    dest = RAW_DIR / "asu"
    dest.mkdir(exist_ok=True)
    zip_path = dest / "asu_microplastics.zip"

    if not zip_path.exists():
        print("  Trying ASU Dataverse download …")
        try:
            r = requests.get(ASU_API, stream=True, timeout=60)
            if r.status_code != 200:
                print(f"  ✗ ASU returned HTTP {r.status_code}. Skipping.")
                return None
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("  ✓ ASU zip downloaded.")
        except Exception as e:
            print(f"  ✗ ASU download failed: {e}")
            return None
    else:
        print("  ✓ ASU zip already present, skipping download.")

    # unzip
    extract_dir = dest / "extracted"
    extract_dir.mkdir(exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
    except Exception as e:
        print(f"  ✗ Failed to unzip ASU archive: {e}")
        return None

    class_images = detect_class_folders(extract_dir)
    if class_images:
        print(f"  ✓ ASU classes detected: {list(class_images.keys())}")
        return class_images
    print("  ✗ Could not auto-detect class folders in ASU archive.")
    return None


# ── source 3: synthetic fallback ────────────────────────────────────────────
def make_synthetic_dataset(n_per_class: int = 120) -> dict[str, list[Path]]:
    """
    Generate clearly-labelled synthetic grayscale images using numpy/cv2.
    Each image contains a shape representative of the class:
      Fiber    → thin elongated blob
      Fragment → irregular polygon
      Film     → thin flat rectangle
    Images are 224×224 uint8 PNGs.

    ⚠ These are NOT real microscope images. They are placeholder images
    so the full pipeline can be exercised before the real dataset is
    available. Any metrics produced from this data are meaningless and
    will be clearly marked as such.
    """
    import numpy as np
    import cv2  # type: ignore

    print(f"\n  ⚠ Using SYNTHETIC PLACEHOLDER dataset ({n_per_class} images/class).")
    print("    These are NOT real microscope images.")
    print("    Metrics from this data are for pipeline validation only.\n")

    synth_dir = RAW_DIR / "synthetic"
    rng = np.random.default_rng(SEED)
    class_images: dict[str, list[Path]] = {c: [] for c in CLASSES}

    def noisy_bg(rng, size=224):
        bg = rng.integers(200, 240, (size, size), dtype=np.uint8)
        noise = rng.integers(-15, 15, (size, size))
        return np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    for i in range(n_per_class):
        # ── Fiber ──
        img = cv2.cvtColor(noisy_bg(rng), cv2.COLOR_GRAY2BGR)
        cx, cy = 112, 112
        angle  = rng.integers(0, 180)
        length = rng.integers(80, 160)
        width  = rng.integers(3, 8)
        dx = int(length / 2 * np.cos(np.deg2rad(angle)))
        dy = int(length / 2 * np.sin(np.deg2rad(angle)))
        cv2.line(img, (cx - dx, cy - dy), (cx + dx, cy + dy),
                 color=(40, 40, 80), thickness=width)
        # add slight gaussian blur to simulate microscope focus
        img = cv2.GaussianBlur(img, (3, 3), 0.8)
        path = synth_dir / "Fiber" / f"fiber_{i:04d}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), img)
        class_images["Fiber"].append(path)

        # ── Fragment ──
        img = cv2.cvtColor(noisy_bg(rng), cv2.COLOR_GRAY2BGR)
        n_pts = rng.integers(5, 9)
        angles_r = sorted(rng.uniform(0, 2 * np.pi, n_pts))
        radii    = rng.uniform(25, 70, n_pts)
        pts = np.array([
            [int(112 + r * np.cos(a)), int(112 + r * np.sin(a))]
            for r, a in zip(radii, angles_r)
        ], dtype=np.int32)
        cv2.fillPoly(img, [pts], color=(60, 80, 120))
        img = cv2.GaussianBlur(img, (3, 3), 0.8)
        path = synth_dir / "Fragment" / f"fragment_{i:04d}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), img)
        class_images["Fragment"].append(path)

        # ── Film ── (thin, flat, semi-transparent rectangle)
        img = cv2.cvtColor(noisy_bg(rng), cv2.COLOR_GRAY2BGR)
        fw  = int(rng.integers(80, 140))
        fh  = int(rng.integers(10, 30))    # flat / thin
        x0  = (224 - fw) // 2
        y0  = (224 - fh) // 2
        # draw dark semi-transparent rectangle directly onto image
        overlay = img.copy()
        cv2.rectangle(overlay, (x0, y0), (x0 + fw, y0 + fh), (50, 70, 30), -1)
        img = cv2.addWeighted(overlay, 0.75, img, 0.25, 0)
        # rotate the whole image slightly
        angle = float(rng.integers(0, 45))
        M     = cv2.getRotationMatrix2D((112.0, 112.0), angle, 1.0)
        img   = cv2.warpAffine(img, M, (224, 224),
                               borderMode=cv2.BORDER_REFLECT)
        img   = cv2.GaussianBlur(img, (3, 3), 0.8)
        path  = synth_dir / "Film" / f"film_{i:04d}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), img)
        class_images["Film"].append(path)

    total = sum(len(v) for v in class_images.values())
    print(f"  ✓ Synthetic dataset generated: {total} images "
          f"({n_per_class} per class)")
    return class_images


# ── main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Download and split microplastics dataset")
    parser.add_argument("--source", choices=["kaggle", "asu", "synthetic", "auto"],
                        default="auto",
                        help="Force a specific source (default: auto, tries kaggle→asu→synthetic)")
    parser.add_argument("--n-synthetic", type=int, default=120,
                        help="Images per class for synthetic fallback (default: 120)")
    parser.add_argument("--clean-splits", action="store_true",
                        help="Delete existing splits before re-running")
    args = parser.parse_args()

    ensure_dirs()

    if args.clean_splits:
        print("  Cleaning existing splits …")
        shutil.rmtree(SPLITS_DIR, ignore_errors=True)
        ensure_dirs()

    print("\n══ Phase 1 — Dataset Download & Split ══════════════════════\n")

    source_used = "unknown"
    class_images: dict[str, list[Path]] | None = None

    if args.source in ("kaggle", "auto"):
        class_images = try_kaggle()
        if class_images:
            source_used = "kaggle"

    if class_images is None and args.source in ("asu", "auto"):
        class_images = try_asu_dataverse()
        if class_images:
            source_used = "asu_dataverse"

    if class_images is None and args.source in ("synthetic", "auto"):
        class_images = make_synthetic_dataset(args.n_synthetic)
        source_used = "synthetic_placeholder"

    if class_images is None:
        print("  ✗ All dataset sources failed. Exiting.")
        sys.exit(1)

    # ensure all three classes present
    missing = [c for c in CLASSES if c not in class_images or not class_images[c]]
    if missing:
        print(f"  ✗ Missing classes after download: {missing}")
        print("    Cannot proceed — check dataset structure.")
        sys.exit(1)

    print(f"\n  Source selected: {source_used}")
    for cls in CLASSES:
        print(f"    {cls}: {len(class_images[cls])} images found")

    print("\n  Splitting (70/15/15) with seed=42 …")
    counts = split_and_copy(class_images)

    print_distribution(counts)
    save_manifest(counts, source=source_used)

    print("══ Phase 1 complete ════════════════════════════════════════\n")
    print("  Next step: run Phase 2 feature extraction on sample images")
    print("  in ml-service/data/splits/train/\n")


if __name__ == "__main__":
    main()
