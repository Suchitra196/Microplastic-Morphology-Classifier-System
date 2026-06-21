"""
Phase 3 — Test Set Evaluation
==============================
Loads best_model.pt, runs inference on the held-out test split,
and produces:
  - Accuracy, per-class precision / recall / F1
  - Macro-averaged F1
  - Confusion matrix
  - Inference timing (CPU)

All results are saved to ml-service/results/metrics.json.
Nothing is written to documentation — these numbers go into the README
only after you review this output.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import torch
import numpy as np
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

# ── paths ────────────────────────────────────────────────────────────────────
ML_SERVICE  = Path(__file__).resolve().parent.parent
SPLITS_DIR  = ML_SERVICE / "data" / "splits"
MODELS_DIR  = ML_SERVICE / "models"
RESULTS_DIR = ML_SERVICE / "results"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]


def load_model(num_classes: int) -> nn.Module:
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes),
    )
    state = torch.load(MODELS_DIR / "best_model.pt", map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model


def evaluate():
    print("\n══ Phase 3 — Test Set Evaluation ════════════════════════════\n")

    class_names_path = MODELS_DIR / "class_names.json"
    if not class_names_path.exists():
        print("  ✗ class_names.json not found. Run train.py first.")
        return
    class_names = json.loads(class_names_path.read_text())
    num_classes  = len(class_names)
    print(f"  Classes: {class_names}")
    print(f"  Device : {DEVICE}\n")

    tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    test_ds = datasets.ImageFolder(str(SPLITS_DIR / "test"), transform=tf)
    loader  = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=0)
    print(f"  Test samples: {len(test_ds)}\n")

    model = load_model(num_classes)

    all_preds, all_labels, inference_times = [], [], []

    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(DEVICE)
            t0   = time.perf_counter()
            out  = model(imgs)
            dt   = (time.perf_counter() - t0) * 1000  # ms
            inference_times.append(dt / imgs.size(0))  # ms per image

            preds = out.argmax(1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.numpy())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)

    accuracy = accuracy_score(all_labels, all_preds)
    report   = classification_report(
        all_labels, all_preds,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(all_labels, all_preds).tolist()
    avg_inference_ms = float(np.mean(inference_times))

    # ── Print results ─────────────────────────────────────────────────────
    print(f"  Overall Accuracy : {accuracy:.4f}  ({100*accuracy:.1f}%)\n")
    print("  Per-class metrics:")
    print(f"  {'Class':<12} {'Precision':>10} {'Recall':>8} {'F1':>8} {'Support':>8}")
    print("  " + "-" * 48)
    for cls in class_names:
        m = report[cls]
        print(f"  {cls:<12} {m['precision']:>10.4f} {m['recall']:>8.4f} "
              f"{m['f1-score']:>8.4f} {int(m['support']):>8}")
    print("  " + "-" * 48)
    print(f"  {'Macro avg':<12} {report['macro avg']['precision']:>10.4f} "
          f"{report['macro avg']['recall']:>8.4f} "
          f"{report['macro avg']['f1-score']:>8.4f}")

    print(f"\n  Confusion matrix (rows=true, cols=pred):")
    print(f"  {'':12} " + "  ".join(f"{c:>10}" for c in class_names))
    for i, row in enumerate(cm):
        print(f"  {class_names[i]:<12} " + "  ".join(f"{v:>10}" for v in row))

    print(f"\n  Avg inference time: {avg_inference_ms:.1f} ms/image (CPU: {DEVICE})")

    # ── Save metrics ──────────────────────────────────────────────────────
    metrics = {
        "accuracy":          round(accuracy, 4),
        "macro_f1":          round(report["macro avg"]["f1-score"], 4),
        "macro_precision":   round(report["macro avg"]["precision"], 4),
        "macro_recall":      round(report["macro avg"]["recall"], 4),
        "per_class":         {
            cls: {
                "precision": round(report[cls]["precision"], 4),
                "recall":    round(report[cls]["recall"],    4),
                "f1":        round(report[cls]["f1-score"],  4),
                "support":   int(report[cls]["support"]),
            }
            for cls in class_names
        },
        "confusion_matrix":  cm,
        "class_names":       class_names,
        "inference_ms_cpu":  round(avg_inference_ms, 2),
        "test_samples":      len(test_ds),
        "device":            str(DEVICE),
    }
    out_path = RESULTS_DIR / "metrics.json"
    out_path.write_text(json.dumps(metrics, indent=2))
    print(f"\n  Metrics saved → {out_path}")
    print("\n══ Evaluation complete ══════════════════════════════════════\n")


if __name__ == "__main__":
    evaluate()
