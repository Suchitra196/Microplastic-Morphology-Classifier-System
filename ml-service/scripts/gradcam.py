"""
Phase 4 — Grad-CAM Explainability
===================================
Implements Grad-CAM (Selvaraju et al., 2017) targeting the LAST
convolutional layer of MobileNetV2: `model.features[18][0]`
(the final pointwise conv before global average pooling).

Why that layer?
  MobileNetV2 ends with features[0..18]. features[18] is the last
  inverted-residual / conv block. The conv at index [0] inside it
  is the last spatial conv — its activation maps retain spatial
  resolution before global pooling collapses everything to a vector.

How Grad-CAM works (in plain English):
  1. Run a forward pass; record the activation maps A at the target layer.
  2. Run a backward pass for the predicted class score.
  3. Compute the gradient of the class score w.r.t. each activation map.
  4. Weight each map by its global-average gradient (importance weight α).
  5. ReLU(weighted sum) → positive activations only → upscale to image size
     → overlay as a heatmap.

Output:
  - ml-service/results/gradcam_examples/<class>_<filename>_gradcam.png
    (original image side-by-side with heatmap overlay)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# ── paths ─────────────────────────────────────────────────────────────────
ML_SERVICE   = Path(__file__).resolve().parent.parent
MODELS_DIR   = ML_SERVICE / "models"
RESULTS_DIR  = ML_SERVICE / "results"
GRADCAM_DIR  = RESULTS_DIR / "gradcam_examples"
GRADCAM_DIR.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cpu")   # Grad-CAM must run on CPU for hook stability

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

TF = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


# ── model loader ──────────────────────────────────────────────────────────
def load_model(class_names: list[str]) -> nn.Module:
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, len(class_names)),
    )
    state = torch.load(MODELS_DIR / "best_model.pt", map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model


# ── Grad-CAM hook class ───────────────────────────────────────────────────
class GradCAM:
    """Wraps a model and registers hooks to capture activations + gradients."""

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model         = model
        self.activations   : Optional[torch.Tensor] = None
        self.gradients     : Optional[torch.Tensor] = None

        self._fwd_hook = target_layer.register_forward_hook(self._save_activation)
        # Use full backward hook to avoid FutureWarning in PyTorch 2.x
        self._bwd_hook = target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, input, output):
        self.activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def remove_hooks(self):
        self._fwd_hook.remove()
        self._bwd_hook.remove()

    def generate(
        self,
        input_tensor: torch.Tensor,   # [1, 3, H, W]
        class_idx: Optional[int] = None,
    ) -> tuple[np.ndarray, int, np.ndarray]:
        """
        Returns
        -------
        cam        : np.ndarray [H, W] float32, values in [0, 1]
        pred_class : int
        probs      : np.ndarray [num_classes] float32
        """
        self.model.zero_grad()
        logits = self.model(input_tensor)                  # forward
        probs  = torch.softmax(logits, dim=1).squeeze().detach().cpu().numpy()
        pred_class = int(logits.argmax(1).item())

        target = class_idx if class_idx is not None else pred_class
        score  = logits[0, target]
        score.backward()                                   # backward

        # α = global-average of gradients over spatial dims
        grads = self.gradients           # [1, C, H, W]
        acts  = self.activations         # [1, C, H, W]
        alpha = grads.mean(dim=(2, 3), keepdim=True)       # [1, C, 1, 1]

        cam = (alpha * acts).sum(dim=1).squeeze()          # [H, W]
        cam = torch.relu(cam).numpy()

        # Normalise to [0, 1]
        if cam.max() > 0:
            cam = cam / cam.max()

        return cam, pred_class, probs


# ── overlay helper ────────────────────────────────────────────────────────
def overlay_heatmap(
    original_bgr: np.ndarray,
    cam: np.ndarray,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Resize cam to original image size, apply jet colormap,
    blend with original. Returns BGR uint8.
    """
    h, w = original_bgr.shape[:2]
    cam_resized = cv2.resize(cam, (w, h), interpolation=cv2.INTER_LINEAR)
    cam_uint8   = np.uint8(255 * cam_resized)
    heatmap     = cv2.applyColorMap(cam_uint8, cv2.COLORMAP_JET)
    overlay     = cv2.addWeighted(original_bgr, 1 - alpha, heatmap, alpha, 0)
    return overlay


# ── main inference + save function ───────────────────────────────────────
def run_gradcam(
    image_path: str | Path,
    class_names: list[str],
    model: nn.Module,
    save: bool = True,
) -> dict:
    """
    Run Grad-CAM on a single image.

    Returns dict with keys:
      predicted_class, confidence, class_probabilities, cam_saved_to
    """
    image_path = Path(image_path)
    pil_img    = Image.open(image_path).convert("RGB")
    tensor     = TF(pil_img).unsqueeze(0).to(DEVICE)

    # Target layer: last spatial conv in MobileNetV2
    # features[18] is a Sequential([Conv2d, BatchNorm2d, ReLU6])
    target_layer = model.features[18][0]

    gcam    = GradCAM(model, target_layer)
    cam, pred_idx, probs = gcam.generate(tensor)
    gcam.remove_hooks()

    pred_class  = class_names[pred_idx]
    confidence  = float(probs[pred_idx])
    class_probs = {class_names[i]: round(float(p), 4) for i, p in enumerate(probs)}

    result = {
        "image":             str(image_path),
        "predicted_class":   pred_class,
        "confidence":        round(confidence, 4),
        "class_probabilities": class_probs,
        "cam_saved_to":      None,
    }

    if save:
        # Load original at 224×224 for side-by-side panel
        orig_bgr = cv2.resize(
            cv2.imread(str(image_path)),
            (224, 224)
        )
        overlay  = overlay_heatmap(orig_bgr, cam)

        # Side-by-side: original | heatmap overlay
        divider  = np.full((224, 4, 3), 200, dtype=np.uint8)
        panel    = np.hstack([orig_bgr, divider, overlay])

        # Label bar
        label = f"Pred: {pred_class}  ({100*confidence:.1f}%)"
        cv2.putText(panel, label, (8, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.putText(panel, label, (8, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)

        out_name = f"{image_path.parent.name}_{image_path.stem}_gradcam.png"
        out_path = GRADCAM_DIR / out_name
        cv2.imwrite(str(out_path), panel)
        result["cam_saved_to"] = str(out_path)

    return result


# ── CLI ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="Generate Grad-CAM heatmaps")
    parser.add_argument("images", nargs="*",
                        help="Image paths (default: 1 image per class from test split)")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    cn_path = MODELS_DIR / "class_names.json"
    if not cn_path.exists():
        print("class_names.json not found. Run train.py first."); sys.exit(1)
    class_names = json.loads(cn_path.read_text())
    model = load_model(class_names)

    if not args.images:
        test_dir = ML_SERVICE / "data" / "splits" / "test"
        image_paths = []
        for cls in class_names:
            imgs = sorted((test_dir / cls).glob("*.png"))
            if imgs:
                image_paths.append(imgs[0])  # one per class
    else:
        image_paths = [Path(p) for p in args.images]

    print(f"\n── Grad-CAM on {len(image_paths)} images ──")
    for p in image_paths:
        r = run_gradcam(p, class_names, model, save=not args.no_save)
        print(f"\n  {p.parent.name}/{p.name}")
        print(f"    Predicted : {r['predicted_class']}  ({100*r['confidence']:.1f}%)")
        print(f"    All probs : {r['class_probabilities']}")
        if r["cam_saved_to"]:
            print(f"    Saved     : {r['cam_saved_to']}")

    print(f"\n  ✓ Heatmaps saved to {GRADCAM_DIR}\n")
