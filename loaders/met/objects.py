"""Met CSV → `objects` table loader.

Reads MetObjects.csv, normalizes per Week 1 schema decisions
(9999 end-date sentinel → NULL, dirty AccessionYear coerced to NULL,
embedded newlines handled via the csv module, UTF-8 BOM stripped via
utf-8-sig), and idempotent-upserts on the natural key
(source='met', source_object_id) using `INSERT ... ON CONFLICT DO UPDATE`.

Usage:
    python -m loaders.met.objects --csv data/raw/MetObjects.csv
    python -m loaders.met.objects --csv data/raw/MetObjects.csv --limit 5000
    python -m loaders.met.objects --csv data/raw/MetObjects.csv --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from tqdm import tqdm

from loaders.met.csv_util import coerce_year, iter_csv_rows

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SOURCE = "met"

PROMOTED_MET_FIELDS = frozenset(
    {
        "Object ID",
        "Title",
        "Object Name",
        "Object Number",
        "Object Date",
        "Object Begin Date",
        "Object End Date",
        "Department",
        "Classification",
        "Medium",
        "Is Public Domain",
        "Is Highlight",
    }
)

# Idempotent upsert on the natural key (source, source_object_id).
# `ingested_at` deliberately not in the SET clause — immutable after first
# insert per decision 5 (freshness pattern). `last_seen_at` bumped on every
# update. RETURNING (xmax = 0) distinguishes inserts from updates without an
# extra round-trip: xmax = 0 on a fresh insert, set to txid on an update.
UPSERT_SQL = """
INSERT INTO objects (
    source, source_object_id, title, object_name, object_number,
    date_string, date_start_year, date_end_year,
    department, classification, medium,
    aat_type_uris, is_public_domain, is_highlight, is_on_view,
    iiif_manifest_url, raw_metadata, source_updated_at
) VALUES (
    %(source)s, %(source_object_id)s, %(title)s, %(object_name)s, %(object_number)s,
    %(date_string)s, %(date_start_year)s, %(date_end_year)s,
    %(department)s, %(classification)s, %(medium)s,
    %(aat_type_uris)s, %(is_public_domain)s, %(is_highlight)s, %(is_on_view)s,
    %(iiif_manifest_url)s, %(raw_metadata)s, %(source_updated_at)s
)
ON CONFLICT (source, source_object_id) DO UPDATE SET
    title             = EXCLUDED.title,
    object_name       = EXCLUDED.object_name,
    object_number     = EXCLUDED.object_number,
    date_string       = EXCLUDED.date_string,
    date_start_year   = EXCLUDED.date_start_year,
    date_end_year     = EXCLUDED.date_end_year,
    department        = EXCLUDED.department,
    classification    = EXCLUDED.classification,
    medium            = EXCLUDED.medium,
    aat_type_uris     = EXCLUDED.aat_type_uris,
    is_public_domain  = EXCLUDED.is_public_domain,
    is_highlight      = EXCLUDED.is_highlight,
    is_on_view        = EXCLUDED.is_on_view,
    iiif_manifest_url = EXCLUDED.iiif_manifest_url,
    raw_metadata      = EXCLUDED.raw_metadata,
    source_updated_at = EXCLUDED.source_updated_at,
    last_seen_at      = NOW()
RETURNING (xmax = 0) AS inserted
"""


@dataclass
class LoaderStats:
    rows_read: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    dirty_year_coercions: int = 0
    end_date_9999_normalized: int = 0
    parse_errors: list[tuple[int, str]] = field(default_factory=list)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the Met objects loader."""
    parser = argparse.ArgumentParser(
        description="Load Met CSV rows into the `objects` table (idempotent upsert).",
    )
    parser.add_argument(
        "--csv",
        required=True,
        type=Path,
        help="Path to MetObjects.csv (e.g. data/raw/MetObjects.csv).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after processing N rows. Omit to process the full file.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Rows per upsert batch (default: 500).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and tally without writing to the database.",
    )
    return parser.parse_args(argv)


def coerce_bool(raw: str) -> bool:
    """Parse Met's 'True'/'False' string column into a Python bool."""
    return raw == "True"


def map_row_to_object(row: dict[str, str], stats: LoaderStats) -> dict[str, Any]:
    """Map a raw Met CSV row to the column→value dict for the `objects` table."""
    # row is one item yielded by iter_csv_rows
    # e.g. row['Object ID'] = '436535', row['Title'] = 'Wheat Field with Cypresses', ...
    result: dict[str, Any] = {}

    # Natural key + source identity (NOT NULL; required for upsert).
    result["source"] = SOURCE
    result["source_object_id"] = row["Object ID"]

    # Promoted text columns; empty strings normalized to NULL.
    result["title"] = row["Title"] or None
    result["object_name"] = row["Object Name"] or None
    result["object_number"] = row["Object Number"] or None
    result["date_string"] = row["Object Date"] or None
    result["department"] = row["Department"] or None
    result["classification"] = row["Classification"] or None
    result["medium"] = row["Medium"] or None

    # Year columns; 9999 end-date sentinel and dirty values tracked separately.
    raw_end = row["Object End Date"]
    if raw_end == "9999":
        stats.end_date_9999_normalized += 1
    date_start_year, dirty_start = coerce_year(row["Object Begin Date"])
    date_end_year, dirty_end = coerce_year(raw_end)
    if dirty_start:
        stats.dirty_year_coercions += 1
    if dirty_end:
        stats.dirty_year_coercions += 1

    result["date_start_year"] = date_start_year
    result["date_end_year"] = date_end_year

    # Booleans (Met emits 'True'/'False' strings; coerce_bool handles both columns).
    result["is_public_domain"] = coerce_bool(row["Is Public Domain"])
    result["is_highlight"] = coerce_bool(row["Is Highlight"])

    # Schema columns Met's CSV doesn't populate. Explicit None/[] for upsert uniformity.
    result["is_on_view"] = None
    result["iiif_manifest_url"] = None
    result["aat_type_uris"] = []
    result["source_updated_at"] = None

    # Everything else preserved as JSONB escape hatch.
    result["raw_metadata"] = {k: v for k, v in row.items() if k not in PROMOTED_MET_FIELDS}

    return result


def upsert_batch(
    conn: psycopg.Connection,
    batch: list[dict[str, Any]],
) -> tuple[int, int]:
    """Idempotent ON CONFLICT upsert of one batch. Return (inserted, updated)."""
    if not batch:
        return (0, 0)

    # 1. Wrap raw_metadata as Jsonb in each record (don't mutate the original — copy first)
    prepared = []
    for record in batch:
        rec = dict(record)
        rec["raw_metadata"] = Jsonb(rec["raw_metadata"])
        prepared.append(rec)

    # 2. Execute the upsert SQL with executemany + returning=True
    inserted = 0
    updated = 0
    with conn.cursor(row_factory=dict_row) as cur:
        cur.executemany(UPSERT_SQL, prepared, returning=True)
        while True:
            row = cur.fetchone()
            if row is not None:
                if row["inserted"]:
                    inserted += 1
                else:
                    updated += 1
            if not cur.nextset():
                break
    conn.commit()

    return (inserted, updated)


def run(conn: psycopg.Connection | None, args: argparse.Namespace) -> LoaderStats:
    """Drive the load: stream CSV → map → batch upsert; honor --limit and --dry-run."""
    stats = LoaderStats()
    batch: list[dict[str, Any]] = []

    # Met currently has ~484,956 rows; bar fills correctly when --limit is set.
    progress_total = args.limit if args.limit is not None else 485_000

    for csv_row_idx, raw_row in enumerate(
        tqdm(iter_csv_rows(args.csv), total=progress_total), start=1
    ):
        # Ingest only up to specified limit if set
        if args.limit is not None and stats.rows_read >= args.limit:
            break

        try:
            record = map_row_to_object(raw_row, stats)
        except Exception as e:
            stats.rows_skipped += 1
            stats.parse_errors.append((csv_row_idx, str(e)))
            continue
        stats.rows_read += 1
        batch.append(record)

        # Flush batch when it reaches the specified size
        if len(batch) >= args.batch_size:
            if not args.dry_run:
                inserted, updated = upsert_batch(conn, batch)
                stats.rows_inserted += inserted
                stats.rows_updated += updated
            batch = []

    # Flush the last partial batch if any
    if batch and not args.dry_run:
        inserted, updated = upsert_batch(conn, batch)
        stats.rows_inserted += inserted
        stats.rows_updated += updated

    return stats


def print_summary(stats: LoaderStats) -> None:
    """Print end-of-run summary tally to stdout."""
    print()
    print("=== Load summary ===")
    print(f"  Rows read:                {stats.rows_read:,}")
    print(f"  Rows inserted:            {stats.rows_inserted:,}")
    print(f"  Rows updated:             {stats.rows_updated:,}")
    print(f"  Rows skipped:             {stats.rows_skipped:,}")
    print(f"  Dirty year coercions:     {stats.dirty_year_coercions:,}")
    print(f"  9999 end-date normalized: {stats.end_date_9999_normalized:,}")
    print(f"  Parse errors:             {len(stats.parse_errors):,}")
    if stats.parse_errors:
        print("  First parse errors:")
        for csv_row, err in stats.parse_errors[:5]:
            print(f"    row {csv_row}: {err}")


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse args, open DB (unless --dry-run), run loader, print summary."""
    args = parse_args(argv)

    load_dotenv(REPO_ROOT / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set in environment or .env.", file=sys.stderr)
        return 2

    if args.dry_run:
        stats = run(None, args)
    else:
        with psycopg.connect(db_url) as conn:
            stats = run(conn, args)

    print_summary(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
