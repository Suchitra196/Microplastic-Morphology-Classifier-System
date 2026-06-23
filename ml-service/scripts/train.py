"""
Phase 3 — Transfer Learning Classifier
=======================================
Backbone: MobileNetV2 (pretrained on ImageNet)

Why MobileNetV2 over ResNet18?
  - Comparable accuracy on small image datasets at this scale
  - ~3.4M parameters vs ResNet18's 11.7M → faster to fine-tune on CPU
  - Depthwise separable convolutions → efficient for later edge deployment
  - torchvision.models provides a clean `features` / `classifier` split
    that makes it straightforward to target Grad-CAM at the last conv block

Training strategy:
  1. Freeze all feature layers, train only the new classifier head for
     WARMUP_EPOCHS (fast convergence, avoids destroying pretrained features).
  2. Unfreeze the last two InvertedResidual blocks + classifier for
     FINETUNE_EPOCHS (allows domain adaptation).
  3. Cosine annealing LR schedule across the fine-tune phase.
  4. Class-weighted CrossEntropyLoss (handles imbalance automatically).
  5. Best model (by val accuracy) is saved to models/best_model.pt.

Outputs:
  - ml-service/models/best_model.pt    (state_dict)
  - ml-service/models/class_names.json
  - ml-service/results/training_log.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, models, transforms

# ── paths ────────────────────────────────────────────────────────────────────
ML_SERVICE  = Path(__file__).resolve().parent.parent
SPLITS_DIR  = ML_SERVICE / "data" / "splits"
MODELS_DIR  = ML_SERVICE / "models"
RESULTS_DIR = ML_SERVICE / "results"
MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# ── hyperparameters ──────────────────────────────────────────────────────────
IMG_SIZE       = 224
BATCH_SIZE     = 32
WARMUP_EPOCHS  = 8    # head-only training
FINETUNE_EPOCHS = 30  # partial unfreeze
LR_WARMUP      = 1e-3
LR_FINETUNE    = 3e-4
WEIGHT_DECAY   = 1e-4
SEED           = 42
NUM_WORKERS    = 0    # set to 0 for Windows (avoids multiprocessing issues)

torch.manual_seed(SEED)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ── data transforms ──────────────────────────────────────────────────────────
# ImageNet normalization stats (MobileNetV2 was trained on these)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

train_tf = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(30),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

val_tf = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


def build_loaders():
    train_ds = datasets.ImageFolder(str(SPLITS_DIR / "train"), transform=train_tf)
    val_ds   = datasets.ImageFolder(str(SPLITS_DIR / "val"),   transform=val_tf)

    # Weighted sampler so every batch is balanced regardless of class sizes
    class_counts = [0] * len(train_ds.classes)
    for _, label in train_ds.samples:
        class_counts[label] += 1
    weights = [1.0 / class_counts[label] for _, label in train_ds.samples]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE,
                              sampler=sampler, num_workers=NUM_WORKERS)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE,
                              shuffle=False, num_workers=NUM_WORKERS)
    return train_loader, val_loader, train_ds.classes


def build_model(num_classes: int) -> nn.Module:
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)

    # Replace the classifier head
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes),
    )
    return model.to(DEVICE)


def freeze_features(model: nn.Module):
    for param in model.features.parameters():
        param.requires_grad = False


def unfreeze_last_blocks(model: nn.Module, n_blocks: int = 3):
    """Unfreeze the last n_blocks InvertedResidual layers + classifier."""
    feature_layers = list(model.features.children())
    for layer in feature_layers[-n_blocks:]:
        for param in layer.parameters():
            param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True


def run_epoch(model, loader, criterion, optimizer=None, phase="train"):
    is_train = (phase == "train")
    model.train() if is_train else model.eval()

    total_loss, correct, total = 0.0, 0, 0
    with torch.set_grad_enabled(is_train):
        for imgs, labels in loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            outputs = model(imgs)
            loss = criterion(outputs, labels)

            if is_train and optimizer:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * imgs.size(0)
            correct    += (outputs.argmax(1) == labels).sum().item()
            total      += imgs.size(0)

    return total_loss / total, correct / total


def train():
    print(f"\n══ Phase 3 — Training (device={DEVICE}) ═════════════════════\n")
    train_loader, val_loader, class_names = build_loaders()
    num_classes = len(class_names)
    print(f"  Classes : {class_names}")
    print(f"  Train   : {len(train_loader.dataset)} samples")
    print(f"  Val     : {len(val_loader.dataset)} samples\n")

    model     = build_model(num_classes)
    criterion = nn.CrossEntropyLoss()

    # ── Phase A: warm-up (frozen features, head only) ────────────────────
    print(f"  ── Warm-up ({WARMUP_EPOCHS} epochs, head only) ──")
    freeze_features(model)
    optimizer_warmup = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR_WARMUP, weight_decay=WEIGHT_DECAY
    )

    log = []
    best_val_acc = 0.0
    best_epoch   = 0

    for epoch in range(1, WARMUP_EPOCHS + 1):
        t0 = time.time()
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer_warmup, "train")
        vl_loss, vl_acc = run_epoch(model, val_loader,   criterion, None,             "val")
        elapsed = time.time() - t0
        entry = {
            "epoch": epoch, "phase": "warmup",
            "train_loss": round(tr_loss, 4), "train_acc": round(tr_acc, 4),
            "val_loss":   round(vl_loss, 4), "val_acc":   round(vl_acc, 4),
        }
        log.append(entry)
        print(f"  Epoch {epoch:2d}/{WARMUP_EPOCHS}  "
              f"train_loss={tr_loss:.4f}  train_acc={tr_acc:.4f}  "
              f"val_loss={vl_loss:.4f}  val_acc={vl_acc:.4f}  "
              f"({elapsed:.1f}s)")

        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            best_epoch   = epoch
            torch.save(model.state_dict(), MODELS_DIR / "best_model.pt")

    # ── Phase B: fine-tune (unfreeze last 3 blocks) ───────────────────────
    print(f"\n  ── Fine-tune ({FINETUNE_EPOCHS} epochs, last 3 blocks unfrozen) ──")
    unfreeze_last_blocks(model, n_blocks=3)
    optimizer_ft = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR_FINETUNE, weight_decay=WEIGHT_DECAY
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer_ft, T_max=FINETUNE_EPOCHS, eta_min=1e-6
    )

    for epoch in range(1, FINETUNE_EPOCHS + 1):
        t0 = time.time()
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer_ft, "train")
        vl_loss, vl_acc = run_epoch(model, val_loader,   criterion, None,         "val")
        scheduler.step()
        elapsed = time.time() - t0
        entry = {
            "epoch": WARMUP_EPOCHS + epoch, "phase": "finetune",
            "train_loss": round(tr_loss, 4), "train_acc": round(tr_acc, 4),
            "val_loss":   round(vl_loss, 4), "val_acc":   round(vl_acc, 4),
        }
        log.append(entry)
        print(f"  Epoch {WARMUP_EPOCHS+epoch:2d}/{WARMUP_EPOCHS+FINETUNE_EPOCHS}  "
              f"train_loss={tr_loss:.4f}  train_acc={tr_acc:.4f}  "
              f"val_loss={vl_loss:.4f}  val_acc={vl_acc:.4f}  "
              f"({elapsed:.1f}s)")

        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            best_epoch   = WARMUP_EPOCHS + epoch
            torch.save(model.state_dict(), MODELS_DIR / "best_model.pt")

    # ── Save artefacts ────────────────────────────────────────────────────
    (MODELS_DIR / "class_names.json").write_text(
        json.dumps(class_names, indent=2)
    )
    (RESULTS_DIR / "training_log.json").write_text(
        json.dumps({"best_epoch": best_epoch,
                    "best_val_acc": round(best_val_acc, 4),
                    "log": log}, indent=2)
    )

    print(f"\n  Best val accuracy: {best_val_acc:.4f}  (epoch {best_epoch})")
    print(f"  Model saved → {MODELS_DIR / 'best_model.pt'}")
    print(f"  Log   saved → {RESULTS_DIR / 'training_log.json'}")
    print("\n══ Training complete — run evaluate.py for test-set metrics ═\n")


if __name__ == "__main__":
    train()
