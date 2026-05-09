"""Compute image + text embeddings under OpenCLIP and SigLIP for the bake-off.

Throwaway. Loads sample.json, runs both models against each work's image and
title (just the title — most diagnostic per the locked scope choice), saves
four arrays to embeddings.npz. Uses MPS if available, else CPU.

Outputs (all unit-normalized):
    embeddings.npz {
        openclip_image: (N, 768),
        openclip_text:  (N, 768),
        siglip_image:   (N, 768),
        siglip_text:    (N, 768),
        order: (N,) source_object_id, str
    }

Sanity check: prints diagonal cosine for both models — the title-image pair
on the same row should sit well above 0 (random baseline). If both models
score near 0 we have a preprocessing or tokenizer mismatch, not a bake-off.

Usage:
    python -m eval.clip-siglip-bakeoff.embed
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

import open_clip
from transformers import AutoModel, AutoProcessor

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "sample.json"
OUT = ROOT / "embeddings.npz"

OPENCLIP_NAME = "ViT-L-14"
OPENCLIP_PRETRAINED = "laion2b_s32b_b82k"
SIGLIP_ID = "google/siglip-large-patch16-256"


def pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def normalize(x: torch.Tensor) -> torch.Tensor:
    return x / x.norm(dim=-1, keepdim=True).clamp_min(1e-12)


def unwrap(x):
    # transformers 5.x: get_image_features / get_text_features may return a
    # BaseModelOutputWithPooling instead of a bare tensor for some models.
    if isinstance(x, torch.Tensor):
        return x
    if getattr(x, "pooler_output", None) is not None:
        return x.pooler_output
    if getattr(x, "last_hidden_state", None) is not None:
        return x.last_hidden_state.mean(dim=1)
    raise TypeError(f"cannot unwrap {type(x)} to tensor")


def load_images(sample: list[dict]) -> list[Image.Image]:
    return [Image.open(ROOT / r["image_path"]).convert("RGB") for r in sample]


def embed_openclip(
    images: list[Image.Image], texts: list[str], device: torch.device
) -> tuple[np.ndarray, np.ndarray]:
    print(f"  Loading OpenCLIP {OPENCLIP_NAME} / {OPENCLIP_PRETRAINED} …")
    t0 = time.time()
    model, _, preprocess = open_clip.create_model_and_transforms(
        OPENCLIP_NAME, pretrained=OPENCLIP_PRETRAINED
    )
    tokenizer = open_clip.get_tokenizer(OPENCLIP_NAME)
    model = model.to(device).eval()
    print(f"  Loaded in {time.time() - t0:.1f}s")

    img_batch = torch.stack([preprocess(im) for im in images]).to(device)
    tok = tokenizer(texts).to(device)

    with torch.no_grad():
        img_emb = normalize(model.encode_image(img_batch))
        txt_emb = normalize(model.encode_text(tok))

    return img_emb.cpu().float().numpy(), txt_emb.cpu().float().numpy()


def embed_siglip(
    images: list[Image.Image], texts: list[str], device: torch.device
) -> tuple[np.ndarray, np.ndarray]:
    print(f"  Loading SigLIP {SIGLIP_ID} …")
    t0 = time.time()
    processor = AutoProcessor.from_pretrained(SIGLIP_ID)
    model = AutoModel.from_pretrained(SIGLIP_ID).to(device).eval()
    print(f"  Loaded in {time.time() - t0:.1f}s")

    img_inputs = processor(images=images, return_tensors="pt").to(device)
    # SigLIP's tokenizer truncates to 64 tokens — long Met titles get cut.
    txt_inputs = processor(
        text=texts, return_tensors="pt", padding="max_length", truncation=True
    ).to(device)

    with torch.no_grad():
        img_emb = normalize(unwrap(model.get_image_features(**img_inputs)))
        txt_emb = normalize(unwrap(model.get_text_features(**txt_inputs)))

    return img_emb.cpu().float().numpy(), txt_emb.cpu().float().numpy()


def diag_cosine(img: np.ndarray, txt: np.ndarray) -> float:
    return float(np.mean(np.sum(img * txt, axis=1)))


def main() -> int:
    if not SAMPLE.exists():
        print(f"ERROR: {SAMPLE} not found. Run fetch_images.py first.", file=sys.stderr)
        return 2

    sample = json.loads(SAMPLE.read_text())
    print(f"Loaded {len(sample)} works from sample.json\n")

    device = pick_device()
    print(f"Device: {device}\n")

    images = load_images(sample)
    titles = [r["title"] for r in sample]
    order = np.array([r["source_object_id"] for r in sample])

    t0 = time.time()
    oc_img, oc_txt = embed_openclip(images, titles, device)
    print(f"  OpenCLIP done in {time.time() - t0:.1f}s "
          f"(img {oc_img.shape}, txt {oc_txt.shape})\n")

    t0 = time.time()
    sg_img, sg_txt = embed_siglip(images, titles, device)
    print(f"  SigLIP done in {time.time() - t0:.1f}s "
          f"(img {sg_img.shape}, txt {sg_txt.shape})\n")

    np.savez(
        OUT,
        openclip_image=oc_img,
        openclip_text=oc_txt,
        siglip_image=sg_img,
        siglip_text=sg_txt,
        order=order,
    )

    print("=== Sanity diagonal cosine (mean across N) ===")
    print(f"  OpenCLIP: {diag_cosine(oc_img, oc_txt):.4f}")
    print(f"  SigLIP:   {diag_cosine(sg_img, sg_txt):.4f}")
    print(f"\nWrote → {OUT.relative_to(ROOT.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
