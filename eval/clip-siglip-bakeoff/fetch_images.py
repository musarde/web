"""Fetch primaryImageSmall for each candidate via Met REST.

Throwaway. Reads candidates.json (oversampled ~200), probes
https://collectionapi.metmuseum.org/public/collection/v1/objects/{id}
for primaryImageSmall, downloads to images/{source_object_id}.jpg,
and writes the successful subset to sample.json. Aims for ~150 final.

Usage:
    python -m eval.clip-siglip-bakeoff.fetch_images
"""

from __future__ import annotations

import json
import ssl
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def encode_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            quote(parts.path, safe="/"),
            quote(parts.query, safe="=&"),
            quote(parts.fragment),
        )
    )

ROOT = Path(__file__).resolve().parent
IMAGES = ROOT / "images"
CANDIDATES = ROOT / "candidates.json"
SAMPLE = ROOT / "sample.json"

API = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{}"
UA = "Musarde-clip-siglip-bakeoff/1.0 (eval; non-production)"
DELAY_S = 0.5
TIMEOUT_S = 15
TARGET_FINAL = 150
RATE_LIMIT_BACKOFF_S = (30, 60, 120)  # retries on 403


def http_get(url: str) -> bytes:
    req = Request(encode_url(url), headers={"User-Agent": UA})
    with urlopen(req, timeout=TIMEOUT_S, context=SSL_CTX) as r:
        return r.read()


def fetch_meta(source_object_id: str) -> dict | None:
    url = API.format(source_object_id)
    backoffs = (0, *RATE_LIMIT_BACKOFF_S)
    for attempt, wait in enumerate(backoffs):
        if wait:
            print(f"    META RETRY met:{source_object_id} after {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
        try:
            body = http_get(url)
            return json.loads(body.decode("utf-8"))
        except HTTPError as e:
            if e.code == 403 and attempt < len(backoffs) - 1:
                continue
            print(f"    META FAIL met:{source_object_id} {e}")
            return None
        except (URLError, json.JSONDecodeError, UnicodeError) as e:
            print(f"    META FAIL met:{source_object_id} {e}")
            return None
    return None


def fetch_image(url: str, dest: Path) -> bool:
    try:
        body = http_get(url)
    except (HTTPError, URLError, UnicodeError) as e:
        print(f"    IMG  FAIL {url} {e}")
        return False
    if not body:
        print(f"    IMG  EMPTY {url}")
        return False
    dest.write_bytes(body)
    return True


def main() -> int:
    if not CANDIDATES.exists():
        print(f"ERROR: {CANDIDATES} not found. Run sample.py first.", file=sys.stderr)
        return 2

    IMAGES.mkdir(exist_ok=True)
    candidates = json.loads(CANDIDATES.read_text())

    # Resume: load existing sample.json so completed entries skip the meta call.
    existing: dict[str, dict] = {}
    if SAMPLE.exists():
        try:
            existing = {r["source_object_id"]: r for r in json.loads(SAMPLE.read_text())}
        except (json.JSONDecodeError, KeyError, TypeError):
            existing = {}
    print(f"Probing {len(candidates)} candidates → primaryImageSmall  ({len(existing)} resumed)\n")

    final: list[dict] = []
    no_meta = no_image_url = image_dl_fail = 0

    for i, c in enumerate(candidates, 1):
        sid = c["source_object_id"]
        dest = IMAGES / f"{sid}.jpg"

        if sid in existing and dest.exists():
            final.append(existing[sid])
            continue

        meta = fetch_meta(sid)
        if meta is None:
            no_meta += 1
            continue

        url = meta.get("primaryImageSmall") or ""
        if not url:
            print(f"  [{i:>3}/{len(candidates)}] met:{sid:>7} no primaryImageSmall")
            no_image_url += 1
            continue

        if not dest.exists():
            ok = fetch_image(url, dest)
            if not ok:
                image_dl_fail += 1
                continue

        c["image_url"] = url
        c["image_path"] = str(dest.relative_to(ROOT))
        c["primary_image"] = meta.get("primaryImage") or ""
        c["object_url"] = meta.get("objectURL") or ""
        final.append(c)

        # Persist after each successful new fetch so a crash doesn't lose progress.
        SAMPLE.write_text(json.dumps(final, indent=2, ensure_ascii=False, default=str) + "\n")

        if i % 20 == 0:
            print(f"  [{i:>3}/{len(candidates)}] kept={len(final)}  no_url={no_image_url}  dl_fail={image_dl_fail}  no_meta={no_meta}")

        time.sleep(DELAY_S)

    # Trim to TARGET_FINAL deterministically — keep order from candidates.json
    # (which is already bucket-grouped, so per-bucket counts shrink proportionally).
    if len(final) > TARGET_FINAL:
        final = final[:TARGET_FINAL]

    SAMPLE.write_text(json.dumps(final, indent=2, ensure_ascii=False, default=str) + "\n")

    print()
    print("=== Fetch summary ===")
    print(f"  Candidates probed:   {len(candidates)}")
    print(f"  Meta fetch fail:     {no_meta}")
    print(f"  No primaryImageSmall:{no_image_url}")
    print(f"  Image DL fail:       {image_dl_fail}")
    print(f"  Final sample:        {len(final)}")
    print()
    bucket_counts: dict[str, int] = {}
    for r in final:
        bucket_counts[r["bucket"]] = bucket_counts.get(r["bucket"], 0) + 1
    for b, n in sorted(bucket_counts.items()):
        print(f"    {b:16} {n}")
    print(f"\nWrote → {SAMPLE.relative_to(ROOT.parent.parent)}")

    drop_pct = 100.0 * (len(candidates) - len(final)) / len(candidates)
    if drop_pct > 30 and len(final) < 120:
        print(f"\n⚠️  {drop_pct:.0f}% drop, N={len(final)} below 120 — consider re-sampling.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
