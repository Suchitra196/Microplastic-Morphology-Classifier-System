"""
Convert YOLO-format detection dataset → cropped classification images
=====================================================================
Reads the sivajyothis/microplastic-dataset (YOLOv8 detection format)
and crops each annotated bounding box into a separate 224×224 image,
organized into class subfolders ready for torchvision.ImageFolder.

Output:
  ml-service/data/splits/
      train/Fiber/   train/Film/   train/Fragment/   train/Pellet/
      val/...        test/...

Classes remapped:
  fiber    → Fiber
  film     → Film
  fragment → Fragment
  pallet   → Pellet   (note: Kaggle dataset spells it 'pallet')
"""

import shutil
from pathlib import Path
from collections import Counter

import cv2
import numpy as np

YOLO_ROOT = (
    Path(__file__).resolve().parent.parent
    / "data" / "raw" / "kaggle_yolo"
    / "microplastic_100.v4i.yolov8"
)
SPLITS_DIR = Path(__file__).resolve().parent.parent / "data" / "splits"

CLASS_MAP = {
    0: "Fiber",
    1: "Film",
    2: "Fragment",
    3: "Pellet",
}
SPLIT_MAP = {
    "train": "train",
    "valid": "val",
    "test":  "test",
}
CROP_SIZE   = 224
PAD_FACTOR  = 0.15   # add 15% padding around each bounding box


def yolo_to_pixel(cx, cy, bw, bh, img_w, img_h):
    """Convert YOLO normalised coords to pixel (x1,y1,x2,y2)."""
    x1 = int((cx - bw / 2) * img_w)
    y1 = int((cy - bh / 2) * img_h)
    x2 = int((cx + bw / 2) * img_w)
    y2 = int((cy + bh / 2) * img_h)
    return x1, y1, x2, y2


def crop_with_padding(img, x1, y1, x2, y2, pad=PAD_FACTOR):
    h, w = img.shape[:2]
    bw = x2 - x1
    bh = y2 - y1
    px = int(bw * pad)
    py = int(bh * pad)
    x1p = max(0, x1 - px)
    y1p = max(0, y1 - py)
    x2p = min(w, x2 + px)
    y2p = min(h, y2 + py)
    return img[y1p:y2p, x1p:x2p]


def convert():
    print("\n── YOLO → Crop Conversion ──────────────────────────────────")
    total_crops = Counter()

    # clean old splits
    shutil.rmtree(SPLITS_DIR, ignore_errors=True)
    for split in ["train", "val", "test"]:
        for cls in CLASS_MAP.values():
            (SPLITS_DIR / split / cls).mkdir(parents=True, exist_ok=True)

    for yolo_split, out_split in SPLIT_MAP.items():
        img_dir   = YOLO_ROOT / yolo_split / "images"
        label_dir = YOLO_ROOT / yolo_split / "labels"

        if not img_dir.exists():
            print(f"  ⚠ {yolo_split}/images not found — skipping")
            continue

        split_crops = Counter()
        for label_file in sorted(label_dir.glob("*.txt")):
            # find matching image
            stem = label_file.stem
            img_path = None
            for ext in [".jpg", ".jpeg", ".png"]:
                candidate = img_dir / (stem + ext)
                if candidate.exists():
                    img_path = candidate
                    break
            if img_path is None:
                continue

            img = cv2.imread(str(img_path))
            if img is None:
                continue
            ih, iw = img.shape[:2]

            lines = label_file.read_text().strip().splitlines()
            class_counter = Counter()  # per-image per-class counter

            for line in lines:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                cls_idx = int(parts[0])
                cx, cy, bw, bh = map(float, parts[1:5])
                cls_name = CLASS_MAP.get(cls_idx)
                if cls_name is None:
                    continue

                x1, y1, x2, y2 = yolo_to_pixel(cx, cy, bw, bh, iw, ih)
                crop = crop_with_padding(img, x1, y1, x2, y2)
                if crop.size == 0:
                    continue

                crop_resized = cv2.resize(crop, (CROP_SIZE, CROP_SIZE),
                                          interpolation=cv2.INTER_AREA)

                n = class_counter[cls_name]
                class_counter[cls_name] += 1
                out_name = f"{stem}_{cls_name.lower()}_{n:03d}.jpg"
                out_path = SPLITS_DIR / out_split / cls_name / out_name
                cv2.imwrite(str(out_path), crop_resized, [cv2.IMWRITE_JPEG_QUALITY, 95])
                split_crops[cls_name] += 1
                total_crops[cls_name] += 1

        total = sum(split_crops.values())
        print(f"\n  {out_split.upper()} — {total} crops")
        for cls in CLASS_MAP.values():
            print(f"    {cls:<10}: {split_crops[cls]}")

    print(f"\n  TOTAL crops: {sum(total_crops.values())}")
    for cls in CLASS_MAP.values():
        print(f"    {cls:<10}: {total_crops[cls]}")

    print("\n  ✓ Conversion complete")
    print(f"  Splits saved to: {SPLITS_DIR}\n")


if __name__ == "__main__":
    convert()
