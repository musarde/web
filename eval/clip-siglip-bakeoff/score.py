"""Score text→image retrieval for OpenCLIP vs SigLIP.

Throwaway. Reads embeddings.npz + sample.json, ranks each title against all
150 image embeddings (per model, independently), and prints overall +
per-bucket hit@1/5/10. Sanity floor: hit@1 must be substantially > 1/N.

Usage:
    python -m eval.clip-siglip-bakeoff.score
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "sample.json"
EMB = ROOT / "embeddings.npz"

K_VALUES = (1, 5, 10)
MODELS = ("openclip", "siglip")


def hit_at_k(sims: np.ndarray, k: int) -> np.ndarray:
    """For an N×N similarity matrix (text rows × image cols, with the gold
    target on the diagonal), return per-row 1.0 if the diagonal is in the
    top-k by similarity, else 0.0.
    """
    n = sims.shape[0]
    diag = np.diag(sims)[:, None]
    rank = (sims > diag).sum(axis=1)
    return (rank < k).astype(np.float32)


def fmt_pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


def main() -> int:
    if not EMB.exists() or not SAMPLE.exists():
        print("ERROR: embeddings.npz or sample.json missing. Run embed.py first.", file=sys.stderr)
        return 2

    sample = json.loads(SAMPLE.read_text())
    data = np.load(EMB, allow_pickle=True)
    n = len(sample)
    buckets = np.array([r["bucket"] for r in sample])
    titles = [r["title"] for r in sample]
    print(f"N = {n}; random baseline hit@1 = {1 / n:.3%}\n")

    # Per-model: hit@k matrix, shape (N, len(K_VALUES))
    per_model = {}
    for m in MODELS:
        img = data[f"{m}_image"]
        txt = data[f"{m}_text"]
        # cosine — both arrays already normalized in embed.py
        sims = txt @ img.T
        per_row = np.stack([hit_at_k(sims, k) for k in K_VALUES], axis=1)
        per_model[m] = per_row

    print("=" * 72)
    print(f"{'Bucket':<18} {'N':>4}  " + "  ".join(
        f"{m:>8}-h@{k}" for m in MODELS for k in K_VALUES
    ))
    print("-" * 72)

    overall_n = n
    overall_line = f"{'OVERALL':<18} {overall_n:>4}  "
    for m in MODELS:
        for ki in range(len(K_VALUES)):
            overall_line += f"  {fmt_pct(per_model[m][:, ki].mean())}  "
    print(overall_line)
    print()

    for bucket in sorted(set(buckets)):
        mask = buckets == bucket
        nb = int(mask.sum())
        line = f"{bucket:<18} {nb:>4}  "
        for m in MODELS:
            for ki in range(len(K_VALUES)):
                line += f"  {fmt_pct(per_model[m][mask, ki].mean())}  "
        print(line)
    print("=" * 72)

    # Per-bucket summary deltas (SigLIP - OpenCLIP, hit@5)
    print(f"\nPer-bucket hit@5 delta (SigLIP - OpenCLIP, positive = SigLIP wins):")
    for bucket in sorted(set(buckets)):
        mask = buckets == bucket
        oc = per_model["openclip"][mask, K_VALUES.index(5)].mean()
        sg = per_model["siglip"][mask, K_VALUES.index(5)].mean()
        delta = sg - oc
        marker = "  SigLIP" if delta > 0.02 else "  OpenCLIP" if delta < -0.02 else "  ~tie"
        print(f"  {bucket:<18}  {fmt_pct(oc)} → {fmt_pct(sg)}   Δ={delta * 100:+5.1f}pp{marker}")

    # Per-row hit lists for the qualitative pass
    print("\nMisses-where-the-other-hit (top-5):")
    oc5 = per_model["openclip"][:, K_VALUES.index(5)]
    sg5 = per_model["siglip"][:, K_VALUES.index(5)]
    only_sg = np.where((sg5 == 1) & (oc5 == 0))[0]
    only_oc = np.where((oc5 == 1) & (sg5 == 0))[0]
    print(f"  SigLIP-only top-5 hits ({len(only_sg)}): {[sample[i]['source_object_id'] for i in only_sg[:8]]}")
    print(f"  OpenCLIP-only top-5 hits ({len(only_oc)}): {[sample[i]['source_object_id'] for i in only_oc[:8]]}")

    # Sanity floor
    overall_h1 = {m: per_model[m][:, 0].mean() for m in MODELS}
    floor = 5 / n  # 5x random baseline
    if all(v < floor for v in overall_h1.values()):
        print(f"\n⚠️  Both models hit@1 below {floor:.1%} — likely preprocessing/tokenizer issue, not a real bake-off.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
