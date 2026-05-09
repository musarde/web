"""Stratified Met sampler for the OpenCLIP vs SigLIP bake-off (Sat May 9).

Throwaway. Oversamples ~200 candidates from the live `objects` table into
buckets that stress-test known CLIP failure modes the Met substrate actually
contains. Image URLs are not in raw_metadata (Met CSV doesn't carry them) —
the fetcher (fetch_images.py) probes Met REST per-object and finalizes the
manifest.

Buckets (target sizes; oversampled vs final 150):
  near_duplicate  40  Egyptian shabtis (nearly-identical funerary figures)
  fine_grained    35  Greek vases by shape (amphora/krater/kylix/hydria/lekythos)
  text_heavy      30  Manuscripts and Illuminations + Calligraphy
  perspective     30  Piranesi prints (architectural perspective)
  realistic       65  Stratified random across other public-domain works

Determinism: setseed(0.42) + ORDER BY random().

Usage:
    python -m eval.clip-siglip-bakeoff.sample
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT = REPO_ROOT / "eval" / "clip-siglip-bakeoff" / "candidates.json"
SEED = 0.42

BUCKETS = {
    "near_duplicate": (
        40,
        """
        SELECT id, source_object_id, title, classification, department,
               raw_metadata->>'Artist Display Name' AS artist
        FROM objects
        WHERE source = 'met'
          AND is_public_domain = TRUE
          AND department = 'Egyptian Art'
          AND object_name ILIKE '%shabti%'
          AND title IS NOT NULL
        ORDER BY random()
        LIMIT %s
        """,
    ),
    "fine_grained": (
        35,
        """
        SELECT id, source_object_id, title, classification, department,
               raw_metadata->>'Artist Display Name' AS artist
        FROM objects
        WHERE source = 'met'
          AND is_public_domain = TRUE
          AND department = 'Greek and Roman Art'
          AND classification = 'Vases'
          AND object_name ILIKE ANY(ARRAY[
              '%amphora%', '%krater%', '%kylix%', '%hydria%',
              '%lekythos%', '%oinochoe%', '%pyxis%', '%skyphos%'
          ])
          AND title IS NOT NULL
        ORDER BY random()
        LIMIT %s
        """,
    ),
    "text_heavy": (
        30,
        """
        SELECT id, source_object_id, title, classification, department,
               raw_metadata->>'Artist Display Name' AS artist
        FROM objects
        WHERE source = 'met'
          AND is_public_domain = TRUE
          AND classification IN ('Manuscripts and Illuminations', 'Calligraphy')
          AND title IS NOT NULL
        ORDER BY random()
        LIMIT %s
        """,
    ),
    "perspective": (
        30,
        """
        SELECT id, source_object_id, title, classification, department,
               raw_metadata->>'Artist Display Name' AS artist
        FROM objects
        WHERE source = 'met'
          AND is_public_domain = TRUE
          AND raw_metadata->>'Artist Display Name' ILIKE '%Piranesi%'
          AND title IS NOT NULL
        ORDER BY random()
        LIMIT %s
        """,
    ),
}

# Department mix for the realistic substrate. Excludes departments that already
# contributed via targeted bucket queries (Egyptian Art, Greek and Roman Art,
# Drawings and Prints — the Piranesi/manuscripts/calligraphy home).
REALISTIC_QUERY = """
SELECT id, source_object_id, title, classification, department,
       raw_metadata->>'Artist Display Name' AS artist
FROM objects
WHERE source = 'met'
  AND is_public_domain = TRUE
  AND department IN (
      'European Sculpture and Decorative Arts',
      'Asian Art',
      'Islamic Art',
      'The American Wing',
      'Costume Institute',
      'Arms and Armor',
      'Medieval Art',
      'Photographs',
      'Arts of Africa, Oceania, and the Americas',
      'Ancient Near Eastern Art',
      'European Paintings',
      'Musical Instruments'
  )
  AND title IS NOT NULL
  AND id != ALL(%s)
ORDER BY random()
LIMIT %s
"""
REALISTIC_TARGET = 65


def fetch_bucket(cur: psycopg.Cursor, name: str, sql: str, target: int) -> list[dict]:
    # LIMIT is inlined as int (not a parameter) so % in ILIKE patterns is taken
    # literally — psycopg's parameter parser otherwise collides with '%shabti%'.
    cur.execute(sql.replace("LIMIT %s", f"LIMIT {int(target)}"))
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["bucket"] = name
    return rows


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set.", file=sys.stderr)
        return 2

    candidates: list[dict] = []
    with psycopg.connect(db_url) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT setseed(%s)", (SEED,))

        for name, (target, sql) in BUCKETS.items():
            rows = fetch_bucket(cur, name, sql, target)
            print(f"  {name:16} {len(rows):>3} (target {target})")
            candidates.extend(rows)

        excluded_ids = [r["id"] for r in candidates]
        realistic_sql = REALISTIC_QUERY.replace("LIMIT %s", f"LIMIT {int(REALISTIC_TARGET)}")
        cur.execute(realistic_sql, (excluded_ids,))
        realistic = [dict(r) for r in cur.fetchall()]
        for r in realistic:
            r["bucket"] = "realistic"
        print(f"  {'realistic':16} {len(realistic):>3} (target {REALISTIC_TARGET})")
        candidates.extend(realistic)

    # Assert no duplicates and stable shape.
    ids = [r["id"] for r in candidates]
    assert len(ids) == len(set(ids)), "duplicate object_ids across buckets"

    OUT.write_text(json.dumps(candidates, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"\nWrote {len(candidates)} candidates → {OUT.relative_to(REPO_ROOT)}")
    print(f"Bucket totals: {dict((b, sum(1 for r in candidates if r['bucket'] == b)) for b in {*[c['bucket'] for c in candidates]})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
