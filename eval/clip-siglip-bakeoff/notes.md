# OpenCLIP vs SigLIP bake-off — qualitative spot-check notes

Sat May 9 2026. N=150 Met public-domain works, 5 buckets. See `score.py`
output for the metrics, `spot_check.txt` for the full nearest-neighbor dump.

## Summary

OpenCLIP wins the text→image task overall (h@5 48.7% vs 45.3%) and on all
three failure-mode buckets (near_duplicate +5pp, perspective +6.7pp,
text_heavy +10pp). SigLIP only wins the realistic baseline (+6.7pp).

Image→image looks nearly identical between the two — both cluster the
within-bucket near-duplicates correctly with comparable similarities. The
gap is in the **text encoder** alignment to Met's stylized title language.

## Per-anchor observations (image→image)

### near_duplicate (shabtis)
- Both models: top-5 are all "Worker Shabti of Nauny" with cosine 0.92–0.98.
  Indistinguishable in retrieval quality on this bucket.

### fine_grained (Greek vase fragments)
- Both models: top-5 are all kylix/krater/skyphos fragments. SigLIP slightly
  more willing to mix shape types (e.g. pyxis, hydria) into the top-5 of a
  kylix anchor; OpenCLIP stays more strictly within the same shape. Mild
  signal that OpenCLIP is more shape-discriminating, but neither is wrong.

### text_heavy (manuscripts)
- Both models: top-5 are 100% same-bucket (manuscript leaves / antiphonaries /
  illuminations). On near-duplicate antiphonary leaves (met:466720 etc.) both
  models pull the same series with cosine 0.87–0.97.

### perspective (Piranesi)
- Both models: top-5 are 100% same-bucket. Pull the same Piranesi prints by
  visual style. SigLIP cosine slightly higher absolute values but rankings are
  largely equivalent.

### realistic (Tazza)
- OpenCLIP top-5: tankard, bowl, watch, adoration scene, marble vase (the last
  cross-bucket but thematically vessel-related).
- SigLIP top-5: bowl, tankard, marble vase, watch, hydria — also dominated by
  vessels with cross-bucket pulls.
- Comparable quality; both surface vessel-style neighbors.

## Why the text→image gap goes OpenCLIP's way

Met titles are stylized: "Manuscript Leaf with Initial O, from an Antiphonary",
"Worker Shabti of Nauny", "Terracotta fragment of a column-krater (bowl for
mixing wine and water)". These read more like cataloguer's descriptions than
the natural-image captions SigLIP was trained on.

OpenCLIP's LAION-2B training corpus is messier and broader (alt-text scraped
from the web, including a lot of museum and academic content). That breadth
shows up in the text encoder's tolerance for collection-card phrasing.

SigLIP's sigmoid loss is also tuned for caption-image pairwise scoring rather
than retrieval ranking — and the per-image similarity scale collapses when the
"caption" is more genre/category than description.

## Implication for the production stack

OpenCLIP ViT-L/14 stays. The schema's `image_embeddings.embedding vector(768)`
column is correct as-is — OpenCLIP-Large is 768-dim. **SigLIP-Large is
1024-dim** (the decision-checklist's "size-matched" pre-pick was wrong;
`google/siglip-base-patch16-256` is the 768-dim variant). If a future
re-evaluation with `siglip-base` flipped the result, the column would still
need widening or the smaller-base variant would need its own bake-off.

## Caveats

- Title-only retrieval is the hardest text→image task. A production query
  "Egyptian funerary figure" is closer to natural caption language and would
  likely close the SigLIP gap. The bake-off measured the worst-case for both
  models, deliberately.
- N=150 is too small for tight confidence intervals. The 3.4pp overall gap
  has wide error bars; what's load-bearing is the *per-bucket* finding —
  OpenCLIP wins all three failure-mode buckets, which is the decision we
  actually care about for the resume bullet.
- SAM substrate (Week 4) is the real eval set for resume-bullet bullet 4's
  "[X%]" placeholder — Met substrate today seeds the methodology but doesn't
  ship the headline number.
