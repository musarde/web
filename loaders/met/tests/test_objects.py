"""Tests for `loaders.met.objects`.

Two layers:
- TestTransform — pure-function tests against the captured CSV fixture.
  No DB. These verify map_row_to_object's behavior on the edge cases
  (9999 end-date sentinel, non-numeric year, empty Title, raw_metadata
  partition).
- TestIdempotency — the safety net. Per the Week 0 ingestion-shape
  decision (re-runnable one-shot loader, no queue, no retry/DLQ), the
  loader's contract is that re-running on the same input produces zero
  new inserts and leaves the DB in the same final state. A failing
  idempotency test means the loader is unsafe to re-run.

Run from the project root:
    python -m pytest loaders/met/tests/ -v

Idempotency tests are skipped when DATABASE_URL isn't set; the
transform tests run anywhere.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

from loaders.met.objects import (
    SOURCE,
    LoaderStats,
    iter_csv_rows,
    map_row_to_object,
    run,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CSV = FIXTURES_DIR / "met_objects_sample.csv"

# Synthetic Object IDs well above Met's real range (~700K). Lets the
# idempotency test clean up only its own rows without touching real data
# even when the test DB is shared with prod-shaped fixtures.
FIXTURE_OBJECT_IDS = [
    "9990000001",
    "9990000002",
    "9990000003",
    "9990000004",
]


# ---------------------------------------------------------------------------
# Pure transform tests (no DB required)
# ---------------------------------------------------------------------------


class TestTransform:
    def test_basic_row_maps_to_objects_record(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        stats = LoaderStats()
        record = map_row_to_object(rows[0], stats)

        assert record["source"] == SOURCE
        assert record["source_object_id"] == "9990000001"
        assert record["title"] == "Wheat Field with Cypresses"
        assert record["object_name"] == "Painting"
        assert record["object_number"] == "1995.4"
        assert record["date_string"] == "1889"
        assert record["date_start_year"] == 1889
        assert record["date_end_year"] == 1889
        assert record["department"] == "European Paintings"
        assert record["classification"] == "Paintings"
        assert record["medium"] == "Oil on canvas"
        assert record["is_public_domain"] is True
        assert record["is_highlight"] is False
        # Schema columns Met's CSV doesn't populate.
        assert record["is_on_view"] is None
        assert record["iiif_manifest_url"] is None
        assert record["aat_type_uris"] == []
        assert record["source_updated_at"] is None

    def test_9999_end_date_sentinel_normalized_to_null(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        stats = LoaderStats()
        record = map_row_to_object(rows[1], stats)

        assert record["date_end_year"] is None
        assert stats.end_date_9999_normalized == 1
        # 9999 is a known sentinel, not dirty data — should not bump dirty count.
        assert stats.dirty_year_coercions == 0

    def test_dirty_year_coerced_to_null_and_tracked(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        stats = LoaderStats()
        record = map_row_to_object(rows[2], stats)

        assert record["date_start_year"] is None
        assert stats.dirty_year_coercions == 1

    def test_empty_title_becomes_null(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        stats = LoaderStats()
        record = map_row_to_object(rows[3], stats)

        assert record["title"] is None

    def test_raw_metadata_excludes_promoted_columns(self):
        rows = list(iter_csv_rows(SAMPLE_CSV))
        stats = LoaderStats()
        record = map_row_to_object(rows[0], stats)

        promoted_keys = {
            "Object ID", "Title", "Object Name", "Object Number",
            "Object Date", "Object Begin Date", "Object End Date",
            "Department", "Classification", "Medium",
            "Is Public Domain", "Is Highlight",
        }
        for key in promoted_keys:
            assert key not in record["raw_metadata"], (
                f"raw_metadata leaked promoted column '{key}'"
            )

        # Non-promoted columns are preserved verbatim.
        assert record["raw_metadata"]["Description"] == "A painting by Vincent van Gogh."
        assert record["raw_metadata"]["Tags"] == "landscape|painting"
        assert record["raw_metadata"]["Country"] == "France"

    def test_iter_csv_rows_strips_utf8_bom(self):
        """The fixture is written with a UTF-8 BOM. iter_csv_rows uses
        encoding='utf-8-sig' which must strip it; otherwise the first
        column header becomes '\\ufeffObject ID' and every lookup fails."""
        rows = list(iter_csv_rows(SAMPLE_CSV))
        first_row_keys = set(rows[0].keys())

        assert "Object ID" in first_row_keys
        assert "﻿Object ID" not in first_row_keys

    def test_transform_is_pure_no_input_mutation(self):
        """map_row_to_object must not mutate its input row — re-mapping
        the same row twice should produce equal records."""
        rows = list(iter_csv_rows(SAMPLE_CSV))
        original = dict(rows[0])

        map_row_to_object(rows[0], LoaderStats())
        map_row_to_object(rows[0], LoaderStats())

        assert rows[0] == original


# ---------------------------------------------------------------------------
# Idempotency tests (DB required)
# ---------------------------------------------------------------------------

# .env lives at the repo root: web/.env. This file is at
# web/loaders/met/tests/test_objects.py, so three .parent hops up.
load_dotenv(Path(__file__).resolve().parents[3] / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL")

needs_db = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="DATABASE_URL not set; idempotency test requires a real DB",
)


@pytest.fixture
def db_conn():
    """Yield a psycopg connection. Deletes fixture rows before AND after
    each test so a failed prior run can't poison the next one."""
    conn = psycopg.connect(DATABASE_URL)

    def _delete_fixture_rows():
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM objects WHERE source = %s AND source_object_id = ANY(%s)",
                (SOURCE, FIXTURE_OBJECT_IDS),
            )
        conn.commit()

    _delete_fixture_rows()
    try:
        yield conn
    finally:
        _delete_fixture_rows()
        conn.close()


def _fixture_args() -> argparse.Namespace:
    return argparse.Namespace(
        csv=SAMPLE_CSV,
        limit=None,
        batch_size=500,
        dry_run=False,
    )


@needs_db
class TestIdempotency:
    """The contract that replaces a queue's retry/DLQ.

    Re-running the loader on the same input must produce zero new inserts.
    Every row from the second run must be an update on the natural key
    `(source, source_object_id)`. If this fails, partial-failure recovery
    by re-run is broken and the no-queue decision becomes unsafe.
    """

    def test_second_run_inserts_zero_rows(self, db_conn):
        args = _fixture_args()
        expected_rows = len(FIXTURE_OBJECT_IDS)

        first = run(db_conn, args)
        assert first.rows_inserted == expected_rows, (
            f"first run: expected {expected_rows} inserts, got {first.rows_inserted}"
        )
        assert first.rows_updated == 0

        second = run(db_conn, args)
        assert second.rows_inserted == 0, (
            f"loader is non-idempotent: second run produced "
            f"{second.rows_inserted} inserts (expected 0). "
            f"Re-running after a partial failure would create duplicate rows."
        )
        assert second.rows_updated == expected_rows

    def test_ingested_at_immutable_across_reruns(self, db_conn):
        """Per 2026-05-04 freshness decision: `ingested_at` is set on first
        INSERT and never moves. `last_seen_at` bumps on every upsert."""
        args = _fixture_args()

        run(db_conn, args)
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT source_object_id, ingested_at FROM objects "
                "WHERE source = %s AND source_object_id = ANY(%s)",
                (SOURCE, FIXTURE_OBJECT_IDS),
            )
            first_ingested_at = {row[0]: row[1] for row in cur.fetchall()}

        run(db_conn, args)
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT source_object_id, ingested_at, last_seen_at FROM objects "
                "WHERE source = %s AND source_object_id = ANY(%s)",
                (SOURCE, FIXTURE_OBJECT_IDS),
            )
            second_pass = cur.fetchall()

        for source_object_id, ingested_at, last_seen_at in second_pass:
            assert ingested_at == first_ingested_at[source_object_id], (
                f"ingested_at moved on re-run for {source_object_id} — "
                f"freshness pattern broken"
            )
            assert last_seen_at >= ingested_at
