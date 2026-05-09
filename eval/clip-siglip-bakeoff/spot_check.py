"""Image→image nearest-neighbor dump for the qualitative spot-check.

Throwaway. Picks one anchor per bucket (plus a few extras), prints the top-5
nearest images per model along with title + bucket, so we can eyeball where
each model surfaces semantically-aligned vs. compositional matches.

Usage:
    python -m eval.clip-siglip-bakeoff.spot_check
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "sample.json"
EMB = ROOT / "embeddings.npz"

ANCHOR_INDICES = (0, 5, 40, 50, 70, 80, 100, 110, 120, 135)


def main() -> int:
    sample = json.loads(SAMPLE.read_text())
    data = np.load(EMB, allow_pickle=True)

    for m in ("openclip", "siglip"):
        img = data[f"{m}_image"]
        sims = img @ img.T
        np.fill_diagonal(sims, -1)  # exclude self
        for ai in ANCHOR_INDICES:
            anchor = sample[ai]
            top5 = np.argsort(-sims[ai])[:5]
            title = (anchor["title"] or "")[:55]
            print(f"\n[{m.upper()}] anchor met:{anchor['source_object_id']:>7} ({anchor['bucket']}) "
                  f"{title}")
            for rank, j in enumerate(top5, 1):
                neigh = sample[j]
                ntitle = (neigh["title"] or "")[:55]
                same_bucket = "✓" if neigh["bucket"] == anchor["bucket"] else " "
                print(f"  {rank}. [{same_bucket}] sim={sims[ai, j]:.3f}  met:{neigh['source_object_id']:>7} "
                      f"({neigh['bucket']:14}) {ntitle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
