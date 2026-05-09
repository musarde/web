"""Met CSV → `artists` + `object_artists` tables loader.

Re-reads MetObjects.csv (same source as objects.py — the artist columns
live in the same file, pipe-delimited for multi-artist works), parses
artist columns positionally, and idempotent-upserts via two batched
helpers driven by `executemany(..., returning=True)`:

  1. `resolve_and_upsert_artists_batch(conn, parsed_list, stats)` — the
     SINGLE chokepoint for artist identity → primary-key resolution.
     EVERY callsite that needs artist ids must route through this
     function. List-shaped: takes parsed artists, returns ids in input
     order. See Decision 2026-05-04 (artist dedup parked for v1.5): the
     v1.5 `canonical_artist_id` self-FK cutover is a one-line change at
     the return statement of this helper, not a multi-file refactor.
  2. `upsert_object_artists_batch(...)` — M:N junction batch insert.
     ON CONFLICT DO NOTHING because junctions track presence only
     (Decision 5 — no `last_seen_at` on `object_artists`).

Batching is mandatory, not optional: per-row round-trips to Neon for
the full corpus (~1.36M statements) take ~5-6 hours and ~30-60x more
Neon compute than batched. Failure mode is fail-loud: a batch raise
rolls back the batch, the run stops, the operator inspects the slice
via `--limit` bisection.

Identity policy for `(source='met', source_artist_id)`:
  - ULAN URL when Met provides one (canonical, also the basis for the
    v1.5 cross-museum dedup plan).
  - `synth:<sha256[:16]>` of "name|begin|end" otherwise — deterministic
    so re-runs collapse to the same row. Met's begin/end can be 0 for
    unknowns, so two records of the same minor artist with inconsistent
    dates will collide as separate synth keys; that drift is the
    motivation for the v1.5 dedup pass and is accepted in v1.

Ordering requirement:
  Run `objects.py` first. CSV rows whose `Object ID` isn't present in
  the `objects` table are counted as `rows_no_parent_object` and skipped
  — there is no parent FK to attach `object_artists` to.

Usage:
    python -m loaders.met.artists --csv data/raw/MetObjects.csv
    python -m loaders.met.artists --csv data/raw/MetObjects.csv --limit 5000
    python -m loaders.met.artists --csv data/raw/MetObjects.csv --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from tqdm import tqdm

from loaders._common.cli import add_common_args
from loaders._common.db import get_database_url
from loaders._common.upsert import execute_returning_batch
from loaders.met.csv_util import coerce_year, iter_csv_rows

SOURCE = "met"

# Artist columns parsed positionally per row: pipe-split each, then zip by
# index. All twelve must align — Met emits empty slots (`|Vincent van Gogh|`
# for slot-2 of three) so we cannot filter empties before zipping.
ARTIST_COLUMNS: tuple[str, ...] = (
    "Artist Role",
    "Artist Prefix",
    "Artist Display Name",
    "Artist Display Bio",
    "Artist Suffix",
    "Artist Alphabet Sort",
    "Artist Nationality",
    "Artist Begin Date",
    "Artist End Date",
    "Artist Gender",
    "Artist ULAN URL",
    "Artist Wikidata URL",
)

# Artist columns lifted to typed columns on `artists`. Everything else at
# a given position (Role / Prefix / Suffix / Alphabet Sort) flows into
# `raw_metadata` for that artist.
PROMOTED_ARTIST_FIELDS: frozenset[str] = frozenset(
    {
        "Artist Display Name",
        "Artist Display Bio",
        "Artist Begin Date",
        "Artist End Date",
        "Artist Nationality",
        "Artist Gender",
        "Artist ULAN URL",
        "Artist Wikidata URL",
    }
)


# Idempotent upsert on (source, source_artist_id). `last_seen_at` bumped
# per Decision 5: parent entity tables track freshness; junction tables
# (object_artists) don't.
ARTIST_UPSERT_SQL = """
INSERT INTO artists (
    source, source_artist_id, name, display_bio,
    birth_year, death_year, nationality, gender,
    ulan_uri, wikidata_uri, raw_metadata, source_updated_at
) VALUES (
    %(source)s, %(source_artist_id)s, %(name)s, %(display_bio)s,
    %(birth_year)s, %(death_year)s, %(nationality)s, %(gender)s,
    %(ulan_uri)s, %(wikidata_uri)s, %(raw_metadata)s, %(source_updated_at)s
)
ON CONFLICT (source, source_artist_id) DO UPDATE SET
    name              = EXCLUDED.name,
    display_bio       = EXCLUDED.display_bio,
    birth_year        = EXCLUDED.birth_year,
    death_year        = EXCLUDED.death_year,
    nationality       = EXCLUDED.nationality,
    gender            = EXCLUDED.gender,
    ulan_uri          = EXCLUDED.ulan_uri,
    wikidata_uri      = EXCLUDED.wikidata_uri,
    raw_metadata      = EXCLUDED.raw_metadata,
    source_updated_at = EXCLUDED.source_updated_at,
    last_seen_at      = NOW()
RETURNING id, (xmax = 0) AS inserted
"""

# DO NOTHING because object_artists has no last_seen_at (Decision 5 —
# junctions track presence, not freshness). Display-order or role drift
# between runs is accepted in v1; full attribution-change detection
# requires snapshot diffing, which is out of scope.
OBJECT_ARTIST_INSERT_SQL = """
INSERT INTO object_artists (object_id, artist_id, role, display_order)
VALUES (%(object_id)s, %(artist_id)s, %(role)s, %(display_order)s)
ON CONFLICT (object_id, artist_id, role) DO NOTHING
RETURNING id
"""


@dataclass
class ParsedArtist:
    """One artist parsed from one position in a row's pipe-split columns."""

    name: str
    display_bio: str | None
    birth_year: int | None
    death_year: int | None
    nationality: str | None
    gender: str | None
    ulan_uri: str | None
    wikidata_uri: str | None
    role: str | None
    display_order: int
    raw_position_fields: dict[str, str]


@dataclass
class BatchEntry:
    """One artist accumulated for a batch flush, paired with its parent
    object's primary key so the M:N junction insert knows where to point."""

    parsed: ParsedArtist
    object_id: int


@dataclass
class LoaderStats:
    rows_read: int = 0
    rows_no_parent_object: int = 0
    rows_no_artists: int = 0
    # Per-resolve counters (NOT unique-artist counts — same artist
    # resolved across N rows increments these N times). On a fresh DB,
    # `artists_inserted` happens to equal the unique artist count
    # because each source_artist_id only inserts once; on re-runs it
    # drops to 0 and `artists_updated` carries the full resolve total.
    # For unique counts, query `artists` directly.
    artists_inserted: int = 0
    artists_updated: int = 0
    ulan_key_resolves: int = 0
    synth_key_resolves: int = 0
    object_artists_inserted: int = 0
    object_artists_skipped_dupe: int = 0
    parse_errors: list[tuple[int, str]] = field(default_factory=list)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the Met artists loader."""
    parser = argparse.ArgumentParser(
        description=(
            "Load Met CSV artist data into `artists` + `object_artists` "
            "(idempotent upsert). Run objects.py first; CSV rows whose "
            "Object ID isn't in `objects` are skipped."
        ),
    )
    parser.add_argument(
        "--csv",
        required=True,
        type=Path,
        help="Path to MetObjects.csv (e.g. data/raw/MetObjects.csv).",
    )
    add_common_args(parser)
    return parser.parse_args(argv)


def split_pipe(value: str) -> list[str]:
    """Met's pipe-delimited multi-artist split. Preserves empty positions."""
    if value == "":
        return []
    return value.split("|")


def parse_artists_from_row(row: dict[str, str]) -> list[ParsedArtist]:
    """Zip pipe-split artist columns positionally; one ParsedArtist per
    non-empty Display Name slot. Empty Display Name = no listed artist
    at that position (anonymous works, missing slots) — skipped."""
    columns = {col: split_pipe(row.get(col, "")) for col in ARTIST_COLUMNS}
    n = max((len(v) for v in columns.values()), default=0)
    if n == 0:
        return []

    # Pad shorter columns to n with "" so positional indexing is safe.
    for col in ARTIST_COLUMNS:
        if len(columns[col]) < n:
            columns[col].extend([""] * (n - len(columns[col])))

    parsed: list[ParsedArtist] = []
    for i in range(n):
        name = columns["Artist Display Name"][i].strip()
        if not name:
            continue
        birth_year, _ = coerce_year(columns["Artist Begin Date"][i])
        death_year, _ = coerce_year(columns["Artist End Date"][i])
        # Empty role → NULL (not ""), so UNIQUE NULLS NOT DISTINCT on
        # object_artists collapses unknown-role duplicates correctly.
        role = columns["Artist Role"][i].strip() or None
        position_raw = {
            col: columns[col][i]
            for col in ARTIST_COLUMNS
            if col not in PROMOTED_ARTIST_FIELDS and columns[col][i] != ""
        }
        parsed.append(
            ParsedArtist(
                name=name,
                display_bio=columns["Artist Display Bio"][i].strip() or None,
                birth_year=birth_year,
                death_year=death_year,
                nationality=columns["Artist Nationality"][i].strip() or None,
                gender=columns["Artist Gender"][i].strip() or None,
                ulan_uri=columns["Artist ULAN URL"][i].strip() or None,
                wikidata_uri=columns["Artist Wikidata URL"][i].strip() or None,
                role=role,
                display_order=i,
                raw_position_fields=position_raw,
            )
        )
    return parsed


def compute_source_artist_id(parsed: ParsedArtist, stats: LoaderStats) -> str:
    """Derive the natural key for an artist row.

    ULAN URI when Met supplies one — canonical authority record, also
    the basis for the v1.5 cross-museum dedup plan. Otherwise a
    deterministic synthetic key from (name | begin | end). Changing this
    formula later forces a re-dedup pass, so it is pinned now.
    """
    if parsed.ulan_uri:
        stats.ulan_key_resolves += 1
        return parsed.ulan_uri
    raw = f"{parsed.name}|{parsed.birth_year or ''}|{parsed.death_year or ''}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    stats.synth_key_resolves += 1
    return f"synth:{digest}"


def build_artist_record(parsed: ParsedArtist, source_artist_id: str) -> dict[str, Any]:
    """Map a ParsedArtist to the column→value dict for the `artists` table.

    `raw_metadata` is left as a plain dict; the upsert helper wraps it
    as Jsonb at bind time (see `jsonb_fields` arg to
    `execute_returning_batch`).
    """
    return {
        "source": SOURCE,
        "source_artist_id": source_artist_id,
        "name": parsed.name,
        "display_bio": parsed.display_bio,
        "birth_year": parsed.birth_year,
        "death_year": parsed.death_year,
        "nationality": parsed.nationality,
        "gender": parsed.gender,
        "ulan_uri": parsed.ulan_uri,
        "wikidata_uri": parsed.wikidata_uri,
        "raw_metadata": parsed.raw_position_fields,
        "source_updated_at": None,
    }


def resolve_and_upsert_artists_batch(
    conn: psycopg.Connection,
    parsed_list: list[ParsedArtist],
    stats: LoaderStats,
) -> list[int]:
    """SINGLE chokepoint for artist identity → primary-key resolution.

    Decision 2026-05-04 (artist dedup parked for v1.5) requires that
    every artist lookup route through ONE function. When v1.5 adds the
    `canonical_artist_id` self-FK, this is the one place that learns
    about it; the rest of the loader stays unchanged. Do not bypass
    this helper by upserting `artists` inline anywhere else.

    Batched form: takes parsed artists, returns their primary-key ids
    in input order via `executemany(..., returning=True)`. Each
    statement returns exactly one row (ARTIST_UPSERT_SQL uses DO UPDATE),
    so the input → output mapping is unambiguous.
    """
    if not parsed_list:
        return []
    records = [
        build_artist_record(p, compute_source_artist_id(p, stats))
        for p in parsed_list
    ]
    result_rows = execute_returning_batch(
        conn, ARTIST_UPSERT_SQL, records, jsonb_fields=("raw_metadata",)
    )
    for row in result_rows:
        if row["inserted"]:
            stats.artists_inserted += 1
        else:
            stats.artists_updated += 1
    return [row["id"] for row in result_rows]
    # v1.5 dedup hook (one-line change after canonical_artist_id ships):
    #   return [row["canonical_artist_id"] or row["id"] for row in result_rows]


def upsert_object_artists_batch(
    conn: psycopg.Connection,
    pairings: list[dict[str, Any]],
    stats: LoaderStats,
) -> None:
    """Batch-insert object_artists. ON CONFLICT DO NOTHING per Decision 5
    (junctions track presence, not freshness).

    Each statement returns 0 rows (conflict skipped) or 1 row (insert
    succeeded). `fetchall()` per result set disambiguates empty-set from
    exhausted-set.
    """
    if not pairings:
        return
    with conn.cursor() as cur:
        cur.executemany(OBJECT_ARTIST_INSERT_SQL, pairings, returning=True)
        while True:
            rows = cur.fetchall()
            if rows:
                stats.object_artists_inserted += len(rows)
            else:
                stats.object_artists_skipped_dupe += 1
            if not cur.nextset():
                break


def flush_batch(
    conn: psycopg.Connection,
    entries: list[BatchEntry],
    stats: LoaderStats,
) -> None:
    """Resolve all artists in the batch via the chokepoint, then bulk-
    insert their object_artists pairings. No exception handling — a
    raise propagates up so the surrounding transaction rolls back the
    whole batch (fail-loud)."""
    if not entries:
        return
    parsed_list = [e.parsed for e in entries]
    artist_ids = resolve_and_upsert_artists_batch(conn, parsed_list, stats)
    pairings = [
        {
            "object_id": e.object_id,
            "artist_id": aid,
            "role": e.parsed.role,
            "display_order": e.parsed.display_order,
        }
        for e, aid in zip(entries, artist_ids, strict=True)
    ]
    upsert_object_artists_batch(conn, pairings, stats)


def load_object_id_map(conn: psycopg.Connection) -> dict[str, int]:
    """Pre-load (source_object_id → id) for all source='met' rows.

    One SELECT keeps per-CSV-row dispatch O(1) instead of an extra round
    trip per row. ~485k entries × ~30 bytes ≈ 15MB resident.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT source_object_id, id FROM objects WHERE source = %s",
            (SOURCE,),
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def run(conn: psycopg.Connection | None, args: argparse.Namespace) -> LoaderStats:
    """Drive the load: stream CSV → accumulate parsed artists into a
    BatchEntry list → flush every `--batch-size` CSV rows.

    Fail-loud on batch errors: `flush_batch` does not catch exceptions.
    A constraint violation, connection drop, or bad encoding propagates
    up, the implicit transaction rolls back, and the script exits
    non-zero. Operator inspects the failing slice via `--limit` bisection.
    """
    stats = LoaderStats()
    object_id_map: dict[str, int] = (
        load_object_id_map(conn) if conn is not None else {}
    )

    batch_entries: list[BatchEntry] = []
    csv_rows_in_batch = 0
    progress_total = args.limit if args.limit is not None else 485_000

    for csv_row_idx, raw_row in enumerate(
        tqdm(iter_csv_rows(args.csv), total=progress_total), start=1
    ):
        if args.limit is not None and stats.rows_read >= args.limit:
            break
        stats.rows_read += 1

        try:
            object_source_id = raw_row["Object ID"]
            object_id = object_id_map.get(object_source_id)
            if conn is not None and object_id is None:
                stats.rows_no_parent_object += 1
                continue

            parsed_artists = parse_artists_from_row(raw_row)
            if not parsed_artists:
                stats.rows_no_artists += 1
                continue

            if args.dry_run:
                # Exercise key derivation; skip SQL accumulation.
                for parsed in parsed_artists:
                    compute_source_artist_id(parsed, stats)
                continue

            assert object_id is not None
            for parsed in parsed_artists:
                batch_entries.append(BatchEntry(parsed=parsed, object_id=object_id))
        except Exception as e:
            stats.parse_errors.append((csv_row_idx, str(e)))
            continue

        csv_rows_in_batch += 1
        if conn is not None and csv_rows_in_batch >= args.batch_size:
            flush_batch(conn, batch_entries, stats)
            conn.commit()
            batch_entries = []
            csv_rows_in_batch = 0

    if conn is not None and batch_entries:
        flush_batch(conn, batch_entries, stats)
        conn.commit()

    return stats


def print_summary(stats: LoaderStats) -> None:
    """Print end-of-run summary tally to stdout."""
    print()
    print("=== Load summary ===")
    print(f"  CSV rows read:              {stats.rows_read:,}")
    print(f"  CSV rows w/ no parent obj:  {stats.rows_no_parent_object:,}")
    print(f"  CSV rows w/ no artists:     {stats.rows_no_artists:,}")
    total_resolves = stats.artists_inserted + stats.artists_updated
    print(f"  Artist resolves (total):    {total_resolves:,}")
    print(f"    inserts (first occurrence): {stats.artists_inserted:,}")
    print(f"    updates (re-resolved):    {stats.artists_updated:,}")
    print(f"    ULAN-keyed:               {stats.ulan_key_resolves:,}")
    print(f"    synth-keyed:              {stats.synth_key_resolves:,}")
    print("    NOTE: per-resolve, not unique. Query `artists` for unique count.")
    print(f"  object_artists inserted:    {stats.object_artists_inserted:,}")
    print(f"  object_artists dupes:       {stats.object_artists_skipped_dupe:,}")
    print(f"  Parse errors:               {len(stats.parse_errors):,}")
    if stats.parse_errors:
        print("  First parse errors:")
        for csv_row, err in stats.parse_errors[:5]:
            print(f"    row {csv_row}: {err}")


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
