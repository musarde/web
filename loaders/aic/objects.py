"""AIC (Art Institute of Chicago) → `objects` table loader.

Two-phase ingest per Decision 2026-05-06 (AIC bulk ingestion — dump
seed + REST top-up):

  Phase 1 — DUMP. Iterate the locally-extracted AIC data dump
    (``--dump-dir <path>`` pointing at the extracted artworks/ tree).
    The dump tarball lives at
    https://artic-api-data.s3.amazonaws.com/artic-api-data.tar.bz2
    and was last refreshed 2025-02-16 as of the decision.

  Phase 2 — REST top-up. Paginate ``/artworks/search`` filtered by
    ``source_updated_at >= --rest-since`` to catch records that
    changed after the dump cut. Same record-mapping function as Phase 1
    — the dump and REST shapes share the artwork object structure.

The two phases are run independently. Operator chooses which to run
each invocation:

    # Phase 1: load the dump
    python -m loaders.aic.objects --dump-dir /tmp/artic-api-data/json/artworks

    # Phase 2: top up everything updated since the dump's S3 Last-Modified
    python -m loaders.aic.objects --rest-since 2025-02-16

Idempotent upsert on ``(source='aic', source_object_id)`` so re-running
either phase is safe — the natural-key UNIQUE constraint plus
``ON CONFLICT DO UPDATE`` is the entire failure-recovery story (no
queue, no retry layer; see Decision 2026-04-30).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from tqdm import tqdm

from loaders._common.cli import add_common_args
from loaders._common.db import get_database_url
from loaders._common.upsert import count_inserts_updates, execute_returning_batch

SOURCE = "aic"

# AIC's REST endpoint. Per AIC API terms, identify yourself in
# User-Agent so they can contact you if a script misbehaves.
AIC_REST_BASE = "https://api.artic.edu/api/v1"
AIC_USER_AGENT = "musarde-loader/0.1 (natalielam@me.com)"

# Fields lifted to typed columns on `objects`. Everything else from the
# AIC artwork blob flows into `raw_metadata` for the escape-hatch
# convention (Week 1 schema decision).
PROMOTED_AIC_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "title",
        "main_reference_number",
        "date_display",
        "date_start",
        "date_end",
        "department_title",
        "classification_title",
        "artwork_type_title",
        "medium_display",
        "is_public_domain",
        "is_on_view",
        "image_id",
        "source_updated_at",
    }
)

# Idempotent upsert on (source, source_object_id) — the contract that
# replaces a queue's retry layer. `ingested_at` deliberately not in the
# SET clause (Decision 2026-05-04 freshness pattern). `last_seen_at`
# bumped on every successful upsert. RETURNING (xmax = 0) lets the
# helper distinguish inserts from updates without a follow-up SELECT.
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
    rows_no_id: int = 0
    rows_no_pd_flag: int = 0
    parse_errors: list[tuple[str, str]] = field(default_factory=list)
    # Phase context — set in `run()` before the per-record loop.
    phase: str = ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments. Exactly one of --dump-dir or --rest-since is required."""
    parser = argparse.ArgumentParser(
        description=(
            "Load AIC artworks into the `objects` table (idempotent upsert). "
            "Pick exactly one phase per invocation: --dump-dir for the bulk "
            "dump, --rest-since for a REST top-up filtered by source_updated_at."
        ),
    )
    phase_group = parser.add_mutually_exclusive_group(required=True)
    phase_group.add_argument(
        "--dump-dir",
        type=Path,
        default=None,
        help=(
            "Directory containing extracted AIC artwork JSON files (e.g. "
            "/tmp/artic-api-data/json/artworks). One JSON per record, "
            "iterated recursively as **/*.json."
        ),
    )
    phase_group.add_argument(
        "--rest-since",
        type=str,
        default=None,
        help=(
            "ISO date (YYYY-MM-DD) for the REST top-up phase. Pulls every "
            "AIC record with source_updated_at >= this date. Use the dump "
            "tarball's S3 Last-Modified date as the cut."
        ),
    )
    add_common_args(parser)
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Record sourcing — dump or REST. Both yield raw artwork dicts (not the
# REST envelope; envelope unwrapping is in `unwrap_record`).
# ---------------------------------------------------------------------------


def unwrap_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize: REST single-record responses are `{"data": {...}, "config": ...}`;
    dump files are the bare artwork dict. Return the bare artwork dict either way.
    """
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        return payload["data"]
    return payload


def iter_dump_records(dump_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield artwork dicts from the locally-extracted AIC data dump.

    Globs `**/*.json` so the operator can point at the artworks/ subdir
    or the tarball root — both work. Files that don't parse as JSON or
    aren't dict-shaped are skipped silently and counted in stats by the
    caller.
    """
    for path in sorted(dump_dir.glob("**/*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(payload, dict):
            yield unwrap_record(payload)


def iter_rest_topup_records(since: str, page_size: int = 100) -> Iterator[dict[str, Any]]:
    """Paginate /artworks/search filtered by source_updated_at >= since.

    Uses AIC's Elasticsearch-passthrough query shape on /artworks/search
    so the filter pushes down to AIC's index instead of being applied
    after a full-corpus pull. Sort is ascending on source_updated_at so
    re-running with the same --rest-since yields the same order; that
    matters if you cancel a partial run and restart.

    NOTE: /artworks/search returns abridged records by default. We pass
    `fields=*` to get the full record shape — same fields the dump
    files contain. If AIC ever caps that, fall back to per-id fetch
    via /artworks/{id}.
    """
    url = f"{AIC_REST_BASE}/artworks/search"
    page = 1
    while True:
        body = {
            "query": {"range": {"source_updated_at": {"gte": since}}},
            "sort": [{"source_updated_at": "asc"}],
            "fields": "*",
            "limit": page_size,
            "page": page,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": AIC_USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())

        records = payload.get("data", [])
        if not records:
            return
        for record in records:
            yield record

        pagination = payload.get("pagination", {})
        if page >= pagination.get("total_pages", 0):
            return
        page += 1
        # AIC asks for ≤60 req/min; one page per ~1s is well under.
        time.sleep(0.5)


# ---------------------------------------------------------------------------
# Pure mapping function. Tested without a DB.
# ---------------------------------------------------------------------------


def coerce_year(raw: Any) -> int | None:
    """AIC's date_start / date_end are integers (or None). BCE dates are
    negative. Treat anything non-integer as missing."""
    if raw is None:
        return None
    if isinstance(raw, bool):  # bool is subclass of int — guard explicitly
        return None
    if isinstance(raw, int):
        return raw
    return None


def map_record_to_object(record: dict[str, Any], stats: LoaderStats) -> dict[str, Any]:
    """Map an AIC artwork dict to the column→value dict for the `objects` table.

    Same function used for both dump and REST phases — both produce the
    same artwork shape. Caller must have already passed the record
    through `unwrap_record`.
    """
    # Natural key. AIC ids are integers; stringify so the column type
    # matches across sources (Met uses string ids too).
    aic_id = record.get("id")
    if aic_id is None:
        raise KeyError("AIC record missing required 'id' field")
    source_object_id = str(aic_id)

    # `is_public_domain` is NOT NULL on the schema. Some AIC records
    # omit the flag entirely; treat absent as False (unsafe to assume
    # PD on a missing signal). Counted separately so the operator can
    # see when this happens.
    is_pd_raw = record.get("is_public_domain")
    if is_pd_raw is None:
        stats.rows_no_pd_flag += 1
        is_public_domain = False
    else:
        is_public_domain = bool(is_pd_raw)

    # IIIF manifest URL: AIC serves IIIF v2 at {iiif_url}/{image_id}.
    # The image_id is a UUID; absent on records without imagery.
    image_id = record.get("image_id")
    iiif_manifest_url = (
        f"https://www.artic.edu/iiif/2/{image_id}" if image_id else None
    )

    # `object_name` per project glossary is the broad type — AIC's
    # `artwork_type_title` ("Painting", "Sculpture") is the closer
    # analogue than `classification_title` (which AIC uses for medium-ish
    # display strings like "oil on canvas"). `classification` column
    # carries `classification_title` for parity with the schema's intent.
    return {
        "source": SOURCE,
        "source_object_id": source_object_id,
        "title": record.get("title") or None,
        "object_name": record.get("artwork_type_title") or None,
        "object_number": record.get("main_reference_number") or None,
        "date_string": record.get("date_display") or None,
        "date_start_year": coerce_year(record.get("date_start")),
        "date_end_year": coerce_year(record.get("date_end")),
        "department": record.get("department_title") or None,
        "classification": record.get("classification_title") or None,
        "medium": record.get("medium_display") or None,
        # AIC doesn't expose AAT URIs directly; cross-museum AAT joins
        # rely on Getty's `aat_type_uris`. Empty array preserves the
        # NOT NULL DEFAULT '{}' contract.
        "aat_type_uris": [],
        "is_public_domain": is_public_domain,
        # AIC has no per-record "highlight" flag analogous to Met's.
        "is_highlight": False,
        "is_on_view": record.get("is_on_view"),
        "iiif_manifest_url": iiif_manifest_url,
        "source_updated_at": record.get("source_updated_at"),
        "raw_metadata": {
            k: v for k, v in record.items() if k not in PROMOTED_AIC_FIELDS
        },
    }


# ---------------------------------------------------------------------------
# Drive: stream → batch → upsert.
# ---------------------------------------------------------------------------


def upsert_batch(
    conn: psycopg.Connection,
    batch: list[dict[str, Any]],
) -> tuple[int, int]:
    """Idempotent ON CONFLICT upsert of one batch. Return (inserted, updated)."""
    if not batch:
        return (0, 0)
    rows = execute_returning_batch(
        conn, UPSERT_SQL, batch, jsonb_fields=("raw_metadata",)
    )
    conn.commit()
    return count_inserts_updates(rows)


def run(conn: psycopg.Connection | None, args: argparse.Namespace) -> LoaderStats:
    """Drive the load: select phase, stream → map → batch upsert."""
    stats = LoaderStats()
    if args.dump_dir is not None:
        stats.phase = "dump"
        record_iter: Iterator[dict[str, Any]] = iter_dump_records(args.dump_dir)
        # AIC corpus is ~125k artworks as of last dump; bar fills correctly
        # under --limit too.
        progress_total = args.limit if args.limit is not None else 125_000
    else:
        stats.phase = "rest"
        record_iter = iter_rest_topup_records(args.rest_since)
        # No upfront count for REST top-up; tqdm shows rate without total.
        progress_total = args.limit

    batch: list[dict[str, Any]] = []
    for record in tqdm(record_iter, total=progress_total):
        if args.limit is not None and stats.rows_read >= args.limit:
            break

        try:
            record_id = str(record.get("id", "<no id>"))
            mapped = map_record_to_object(record, stats)
        except Exception as e:
            stats.rows_skipped += 1
            stats.parse_errors.append((record_id, str(e)))
            if record.get("id") is None:
                stats.rows_no_id += 1
            continue

        stats.rows_read += 1
        batch.append(mapped)

        if len(batch) >= args.batch_size:
            if not args.dry_run:
                inserted, updated = upsert_batch(conn, batch)
                stats.rows_inserted += inserted
                stats.rows_updated += updated
            batch = []

    if batch and not args.dry_run:
        inserted, updated = upsert_batch(conn, batch)
        stats.rows_inserted += inserted
        stats.rows_updated += updated

    return stats


def print_summary(stats: LoaderStats) -> None:
    """Print end-of-run summary tally to stdout."""
    print()
    print(f"=== Load summary ({stats.phase} phase) ===")
    print(f"  Rows read:                {stats.rows_read:,}")
    print(f"  Rows inserted:            {stats.rows_inserted:,}")
    print(f"  Rows updated:             {stats.rows_updated:,}")
    print(f"  Rows skipped:             {stats.rows_skipped:,}")
    print(f"  Rows missing 'id':        {stats.rows_no_id:,}")
    print(f"  Rows missing PD flag:     {stats.rows_no_pd_flag:,}")
    print(f"  Parse errors:             {len(stats.parse_errors):,}")
    if stats.parse_errors:
        print("  First parse errors:")
        for record_id, err in stats.parse_errors[:5]:
            print(f"    id {record_id}: {err}")


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse args, open DB (unless --dry-run), run, summarize."""
    args = parse_args(argv)

    db_url = get_database_url()
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
