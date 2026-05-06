"""Tests for `loaders.met.artists`.

Two layers, mirroring test_objects.py:
- TestTransform — pure-function tests against the captured CSV fixture.
  No DB. Verifies pipe-split positional parse, empty-slot skipping,
  empty-role → None, ULAN-vs-synth identity policy, and the
  raw_metadata partition for the artist position.
- TestIdempotency — the chokepoint contract under re-run. Per Decision
  2026-05-04 (artist dedup parked for v1.5) and Decision 5 (parents
  freshness, junctions presence-only), re-running the loader on the
  same input must produce zero new artist rows AND zero new
  object_artists rows. A failing idempotency test means the loader is
  unsafe to re-run — and re-runnability is the substitute for a
  retry/DLQ tier.

Run from the project root:
    python -m pytest loaders/met/tests/ -v

Idempotency tests are skipped when DATABASE_URL isn't set.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

from loaders.met.artists import (
    SOURCE,
    LoaderStats,
    build_artist_record,
    compute_source_artist_id,
    parse_artists_from_row,
    run,
    split_pipe,
)
from loaders.met.csv_util import iter_csv_rows
from loaders.met.objects import run as run_objects

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CSV = FIXTURES_DIR / "met_objects_sample.csv"

# Same synthetic Object IDs as test_objects.py — the artist columns
# share the fixture file so both loaders read the same source of truth.
FIXTURE_OBJECT_IDS = [
    "9990000001",
    "9990000002",
    "9990000003",
    "9990000004",
]


def _synth_key(name: str, begin: int | str, end: int | str) -> str:
    """Re-implement the synth-key formula for cleanup/assertions.

    Mirrors `compute_source_artist_id` exactly. If the formula in
    artists.py changes, this helper must change in lockstep — which is
    intentional, since the formula is pinned (Decision 2026-05-04).
    """
    raw = f"{name}|{begin}|{end}"
    return "synth:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# Test ULANs use a clearly-fake host so cleanup can never collide with
# real Getty ULANs even when the test DB is shared with prod-shaped data.
FIXTURE_ULAN_ALPHA = "http://test.example.org/ulan/alpha"
FIXTURE_ULAN_GAMMA = "http://test.example.org/ulan/gamma"
FIXTURE_SYNTH_BETA = _synth_key("Test Anonymous Beta", 1900, 1980)
FIXTURE_SYNTH_DELTA = _synth_key("Test Artist Delta", 1880, 1980)

FIXTURE_ARTIST_KEYS = [
    FIXTURE_ULAN_ALPHA,
    FIXTURE_ULAN_GAMMA,
    FIXTURE_SYNTH_BETA,
    FIXTURE_SYNTH_DELTA,
]


# ---------------------------------------------------------------------------
# Pure transform tests (no DB required)
# ---------------------------------------------------------------------------


class TestTransform:
    def test_split_pipe_empty_string_returns_empty_list(self):
        assert split_pipe("") == []

    def test_split_pipe_preserves_empty_positions(self):
        # Met emits empty slots at any position; positional zip across
        # all 12 artist columns relies on these being preserved.
        assert split_pipe("|a|") == ["", "a", ""]
        assert split_pipe("a||b") == ["a", "", "b"]
        assert split_pipe("a") == ["a"]

    def test_parse_single_artist_with_ulan(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[0])

        assert len(parsed) == 1
        artist = parsed[0]
        assert artist.name == "Test Artist Alpha"
        assert artist.role == "Artist"
        assert artist.display_order == 0
        assert artist.ulan_uri == FIXTURE_ULAN_ALPHA
        assert artist.birth_year == 1853
        assert artist.death_year == 1890
        assert artist.nationality == "TestNationality1"

    def test_parse_no_artist_returns_empty_list(self):
        """Row with all artist columns empty → no ParsedArtist; the run
        loop counts this as rows_no_artists and skips it."""
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[1])
        assert parsed == []

    def test_parse_empty_role_becomes_none(self):
        """Empty role → None (not ""), so UNIQUE NULLS NOT DISTINCT on
        object_artists collapses unknown-role duplicates correctly."""
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[2])

        assert len(parsed) == 1
        assert parsed[0].role is None
        assert parsed[0].name == "Test Anonymous Beta"

    def test_parse_multi_artist_with_empty_middle_slot(self):
        """Three pipe-positions, middle one empty Display Name. Positional
        zip must keep position 2 aligned (display_order=2), not collapse
        it to display_order=1."""
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[3])

        assert len(parsed) == 2
        first, second = parsed

        assert first.name == "Test Artist Gamma"
        assert first.display_order == 0
        assert first.role == "Designer"
        assert first.ulan_uri == FIXTURE_ULAN_GAMMA
        assert first.birth_year == 1480
        assert first.death_year == 1530

        assert second.name == "Test Artist Delta"
        assert second.display_order == 2
        assert second.role == "Painter"
        assert second.ulan_uri is None
        assert second.birth_year == 1880
        assert second.death_year == 1980

    def test_compute_source_artist_id_with_ulan_returns_ulan_uri(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[0])[0]
        stats = LoaderStats()

        key = compute_source_artist_id(parsed, stats)

        assert key == FIXTURE_ULAN_ALPHA
        assert stats.ulan_key_resolves == 1
        assert stats.synth_key_resolves == 0

    def test_compute_source_artist_id_without_ulan_returns_synth(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[2])[0]  # Beta, no ULAN
        stats = LoaderStats()

        key = compute_source_artist_id(parsed, stats)

        assert key.startswith("synth:")
        assert key == FIXTURE_SYNTH_BETA
        assert stats.synth_key_resolves == 1
        assert stats.ulan_key_resolves == 0

    def test_compute_source_artist_id_synth_is_deterministic(self):
        """Same name + begin + end → identical synth key. This is the
        property that makes re-runs collapse no-ULAN artists onto the
        same row instead of inserting duplicates."""
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[2])[0]

        key_1 = compute_source_artist_id(parsed, LoaderStats())
        key_2 = compute_source_artist_id(parsed, LoaderStats())

        assert key_1 == key_2

    def test_compute_source_artist_id_synth_differs_on_different_dates(self):
        """Two artists with identical name but different birth years
        must produce different synth keys — the v1 dedup tradeoff
        documented in Decision 2026-05-04."""
        rows = list(iter_csv_rows(SAMPLE_CSV))
        beta = parse_artists_from_row(rows[2])[0]

        # Synthesize a same-name-different-date variant in memory.
        from dataclasses import replace

        beta_alt = replace(beta, birth_year=1850, death_year=1920)

        key_beta = compute_source_artist_id(beta, LoaderStats())
        key_alt = compute_source_artist_id(beta_alt, LoaderStats())

        assert key_beta != key_alt

    def test_build_artist_record_maps_typed_fields(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[0])[0]

        record = build_artist_record(parsed, FIXTURE_ULAN_ALPHA)

        assert record["source"] == SOURCE
        assert record["source_artist_id"] == FIXTURE_ULAN_ALPHA
        assert record["name"] == "Test Artist Alpha"
        assert record["display_bio"] == "Test Bio Alpha 1853-1890"
        assert record["birth_year"] == 1853
        assert record["death_year"] == 1890
        assert record["nationality"] == "TestNationality1"
        assert record["ulan_uri"] == FIXTURE_ULAN_ALPHA
        assert record["wikidata_uri"] is None
        # Met CSV doesn't carry a per-artist source_updated_at.
        assert record["source_updated_at"] is None

    def test_raw_metadata_excludes_promoted_artist_fields(self):
        """raw_position_fields is the per-artist JSONB escape hatch; it
        must hold ONLY columns not lifted to typed columns on `artists`."""
        rows = list(iter_csv_rows(SAMPLE_CSV))
        parsed = parse_artists_from_row(rows[0])[0]

        promoted_keys = {
            "Artist Display Name",
            "Artist Display Bio",
            "Artist Begin Date",
            "Artist End Date",
            "Artist Nationality",
            "Artist Gender",
            "Artist ULAN URL",
            "Artist Wikidata URL",
        }
        for key in promoted_keys:
            assert key not in parsed.raw_position_fields, (
                f"raw_position_fields leaked promoted column '{key}'"
            )

        # Non-promoted columns at this position are preserved verbatim.
        assert parsed.raw_position_fields["Artist Role"] == "Artist"
        assert parsed.raw_position_fields["Artist Alphabet Sort"] == "Alpha Test Artist"


# ---------------------------------------------------------------------------
# Idempotency tests (DB required)
# ---------------------------------------------------------------------------

# .env lives at the repo root: web/.env. This file is at
# web/loaders/met/tests/test_artists.py, so three .parent hops up.
load_dotenv(Path(__file__).resolve().parents[3] / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL")

needs_db = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="DATABASE_URL not set; idempotency test requires a real DB",
)


def _fixture_args() -> argparse.Namespace:
    return argparse.Namespace(
        csv=SAMPLE_CSV,
        limit=None,
        batch_size=500,
        dry_run=False,
    )


@pytest.fixture
def db_conn_with_objects():
    """Yield a psycopg connection with parent fixture objects pre-loaded.

    artists.py reads the `objects` table at startup to map
    source_object_id → object_id. Each test starts with the 4 fixture
    objects already in place so artist-attachment is exercised end-to-end.
    Cleanup deletes objects (cascades object_artists) AND artists by their
    known fixture keys, before AND after each test.
    """
    conn = psycopg.connect(DATABASE_URL)

    def _cleanup():
        with conn.cursor() as cur:
            # Delete objects → cascades object_artists rows referencing them.
            cur.execute(
                "DELETE FROM objects WHERE source = %s AND source_object_id = ANY(%s)",
                (SOURCE, FIXTURE_OBJECT_IDS),
            )
            # Delete fixture artists by their deterministic source_artist_ids.
            cur.execute(
                "DELETE FROM artists WHERE source = %s AND source_artist_id = ANY(%s)",
                (SOURCE, FIXTURE_ARTIST_KEYS),
            )
        conn.commit()

    _cleanup()
    # Pre-load parent objects so artists.py has valid FKs to attach to.
    run_objects(conn, _fixture_args())
    try:
        yield conn
    finally:
        _cleanup()
        conn.close()


@needs_db
class TestIdempotency:
    """The contract that replaces a queue's retry/DLQ for the artists pass.

    Re-running the loader on the same input must produce zero new
    artist inserts AND zero new object_artists inserts. If this fails,
    partial-failure recovery by re-run is broken.
    """

    def test_first_run_inserts_expected_artist_counts(self, db_conn_with_objects):
        first = run(db_conn_with_objects, _fixture_args())

        # 4 distinct artists across 4 fixture rows: Alpha (row 1, ULAN),
        # Beta (row 3, synth), Gamma (row 4 pos 0, ULAN), Delta (row 4
        # pos 2, synth). Row 2 has no artists.
        assert first.artists_inserted == 4
        assert first.artists_updated == 0
        assert first.rows_no_artists == 1

    def test_first_run_inserts_expected_object_artist_counts(
        self, db_conn_with_objects
    ):
        first = run(db_conn_with_objects, _fixture_args())

        # Pairings: (obj1, alpha), (obj3, beta), (obj4, gamma), (obj4, delta).
        assert first.object_artists_inserted == 4
        assert first.object_artists_skipped_dupe == 0

    def test_first_run_counters_split_ulan_vs_synth(self, db_conn_with_objects):
        """Identity-policy resolution should bump the right counter
        depending on whether Met provided a ULAN."""
        first = run(db_conn_with_objects, _fixture_args())

        assert first.ulan_key_resolves == 2  # Alpha + Gamma
        assert first.synth_key_resolves == 2  # Beta + Delta

    def test_second_run_inserts_zero_rows(self, db_conn_with_objects):
        args = _fixture_args()

        first = run(db_conn_with_objects, args)
        assert first.artists_inserted == 4
        assert first.object_artists_inserted == 4

        second = run(db_conn_with_objects, args)
        assert second.artists_inserted == 0, (
            f"loader is non-idempotent on artists: second run produced "
            f"{second.artists_inserted} inserts (expected 0)."
        )
        assert second.artists_updated == 4
        assert second.object_artists_inserted == 0, (
            f"loader is non-idempotent on object_artists: second run "
            f"produced {second.object_artists_inserted} inserts (expected 0)."
        )
        assert second.object_artists_skipped_dupe == 4

    def test_artist_ingested_at_immutable_across_reruns(self, db_conn_with_objects):
        """Per Decision 5: `ingested_at` set on first INSERT and never
        moves; `last_seen_at` bumps on every upsert."""
        args = _fixture_args()

        run(db_conn_with_objects, args)
        with db_conn_with_objects.cursor() as cur:
            cur.execute(
                "SELECT source_artist_id, ingested_at FROM artists "
                "WHERE source = %s AND source_artist_id = ANY(%s)",
                (SOURCE, FIXTURE_ARTIST_KEYS),
            )
            first_ingested_at = {row[0]: row[1] for row in cur.fetchall()}

        run(db_conn_with_objects, args)
        with db_conn_with_objects.cursor() as cur:
            cur.execute(
                "SELECT source_artist_id, ingested_at, last_seen_at FROM artists "
                "WHERE source = %s AND source_artist_id = ANY(%s)",
                (SOURCE, FIXTURE_ARTIST_KEYS),
            )
            second_pass = cur.fetchall()

        for source_artist_id, ingested_at, last_seen_at in second_pass:
            assert ingested_at == first_ingested_at[source_artist_id], (
                f"ingested_at moved on re-run for {source_artist_id} — "
                f"freshness pattern broken"
            )
            assert last_seen_at >= ingested_at

    def test_empty_csv_role_becomes_null_in_object_artists(
        self, db_conn_with_objects
    ):
        """Beta's CSV role is ""; the loader must persist it as NULL so
        the UNIQUE NULLS NOT DISTINCT constraint on object_artists
        collapses unknown-role duplicates correctly."""
        run(db_conn_with_objects, _fixture_args())

        with db_conn_with_objects.cursor() as cur:
            cur.execute(
                """
                SELECT oa.role
                FROM object_artists oa
                JOIN artists a ON a.id = oa.artist_id
                WHERE a.source = %s AND a.source_artist_id = %s
                """,
                (SOURCE, FIXTURE_SYNTH_BETA),
            )
            rows = cur.fetchall()

        assert len(rows) == 1
        assert rows[0][0] is None, (
            "empty CSV role persisted as something other than NULL — "
            "UNIQUE NULLS NOT DISTINCT semantics will misbehave"
        )

    def test_ulan_uri_preserved_on_artists_row(self, db_conn_with_objects):
        """The artists row keyed by ULAN should have its ulan_uri column
        populated — not just used as the natural key."""
        run(db_conn_with_objects, _fixture_args())

        with db_conn_with_objects.cursor() as cur:
            cur.execute(
                "SELECT ulan_uri FROM artists "
                "WHERE source = %s AND source_artist_id = %s",
                (SOURCE, FIXTURE_ULAN_ALPHA),
            )
            row = cur.fetchone()

        assert row is not None
        assert row[0] == FIXTURE_ULAN_ALPHA
