# ml-service/data

This directory is not committed to git (see `.gitignore`).

## To populate it, run:

```bash
# Option A — synthetic placeholder (no auth required, for pipeline testing)
python ml-service/scripts/download_dataset.py --source synthetic

# Option B — auto (tries Kaggle → ASU Dataverse → synthetic fallback)
python ml-service/scripts/download_dataset.py

# Option C — Kaggle (requires ~/.kaggle/kaggle.json)
python ml-service/scripts/download_dataset.py --source kaggle
```

## Recommended real datasets

| Dataset | Source | Classes | Notes |
|---------|--------|---------|-------|
| Microplastic Dataset for Computer Vision | [Kaggle: zhongbinbin](https://www.kaggle.com/datasets/zhongbinbin/microplastic-dataset-for-computer-vision) | Fiber, Fragment, Film, Pellet | Primary target |
| TACO (plastic subtypes) | [Kaggle: kneroma](https://www.kaggle.com/datasets/kneroma/tacobag) | Multiple plastic classes | Broader dataset |

## Current status

Run `download_dataset.py` and check `ml-service/results/dataset_manifest.json`
for the source and split counts used in this run.
