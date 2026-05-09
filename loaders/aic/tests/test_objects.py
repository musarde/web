"""Tests for `loaders.aic.objects`.

Two layers, mirroring `loaders/met/tests/test_objects.py`:

- TestTransform — pure-function tests against a captured AIC API
  fixture (artwork id 27992, Seurat's "A Sunday on La Grande Jatte").
  No DB. Verifies `map_record_to_object` against real-shape data plus
  synthetic edge cases (missing image_id, missing is_public_domain,
  REST envelope unwrap, BCE date_start).

- TestIdempotency — the safety net required by the no-queue ingestion
  shape (Decision 2026-04-30). Re-running the loader on the same input
  must produce zero new inserts. Skipped when DATABASE_URL isn't set.

Run from the project root:
    python -m pytest loaders/aic/tests/ -v
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

from loaders.aic.objects import (
    SOURCE,
    LoaderStats,
    map_record_to_object,
    run,
    unwrap_record,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_REST_RESPONSE = FIXTURES_DIR / "aic_object_27992.json"

# Synthetic AIC ids well above the live id space (~270k as of 2026)
# so the idempotency test can clean up only its own rows even when
# sharing a DB with real ingest data.
FIXTURE_OBJECT_IDS = [
    "9990000001",
    "9990000002",
    "9990000003",
]


def _load_fixture_artwork() -> dict:
    """Read the captured REST response and return the bare artwork dict."""
    with open(SAMPLE_REST_RESPONSE) as f:
        payload = json.load(f)
    return unwrap_record(payload)


def _synthetic_record(**overrides) -> dict:
    """Build an AIC artwork dict from the captured fixture with field
    overrides — convenient for edge-case tests without re-capturing
    a whole real record."""
    record = dict(_load_fixture_artwork())
    record.update(overrides)
    return record


# ---------------------------------------------------------------------------
# Pure transform tests (no DB required)
# ---------------------------------------------------------------------------


class TestTransform:
    def test_real_record_maps_to_objects_record(self):
        """Captured AIC record → expected `objects` row shape."""
        record = _load_fixture_artwork()
        stats = LoaderStats()
        mapped = map_record_to_object(record, stats)

        assert mapped["source"] == SOURCE
        assert mapped["source_object_id"] == "27992"
        assert mapped["title"] == "A Sunday on La Grande Jatte — 1884"
        assert mapped["object_name"] == "Painting"
        assert mapped["object_number"]  # main_reference_number is non-empty
        assert mapped["date_string"]
        assert mapped["date_start_year"] == 1884
        assert mapped["date_end_year"] == 1886
        assert mapped["department"] == "Painting and Sculpture of Europe"
        assert mapped["classification"] == "oil on canvas"
        assert mapped["medium"] == "Oil on canvas"
        assert mapped["is_public_domain"] is True
        assert mapped["is_highlight"] is False  # AIC has no analogue; default
        assert mapped["aat_type_uris"] == []
        assert mapped["iiif_manifest_url"] is not None
        assert mapped["iiif_manifest_url"].startswith("https://www.artic.edu/iiif/2/")

    def test_unwrap_record_handles_rest_envelope(self):
        """REST single-record responses wrap the artwork in `data`."""
        with open(SAMPLE_REST_RESPONSE) as f:
            payload = json.load(f)
        assert "data" in payload
        unwrapped = unwrap_record(payload)
        assert "id" in unwrapped
        assert "data" not in unwrapped

    def test_unwrap_record_passes_through_bare_artwork(self):
        """Dump files contain the bare artwork dict — `unwrap_record` no-ops."""
        bare = {"id": 1, "title": "x"}
        assert unwrap_record(bare) is bare

    def test_missing_id_raises(self):
        """A record without `id` cannot be upserted (natural key required)."""
        record = _synthetic_record()
        del record["id"]
        with pytest.raises(KeyError):
            map_record_to_object(record, LoaderStats())

    def test_missing_pd_flag_defaults_false_and_tracked(self):
        """is_public_domain is NOT NULL on the schema; absent → False, counted."""
        record = _synthetic_record(id=9990000001, is_public_domain=None)
        stats = LoaderStats()
        mapped = map_record_to_object(record, stats)

        assert mapped["is_public_domain"] is False
        assert stats.rows_no_pd_flag == 1

    def test_missing_image_id_yields_null_iiif_url(self):
        """Records without imagery get NULL iiif_manifest_url, not a broken URL."""
        record = _synthetic_record(id=9990000002, image_id=None)
        mapped = map_record_to_object(record, LoaderStats())
        assert mapped["iiif_manifest_url"] is None

    def test_bce_date_start_preserved_as_negative_int(self):
        """AIC encodes BCE dates as negative date_start ints; preserve them."""
        record = _synthetic_record(id=9990000003, date_start=-500, date_end=-450)
        mapped = map_record_to_object(record, LoaderStats())
        assert mapped["date_start_year"] == -500
        assert mapped["date_end_year"] == -450

    def test_raw_metadata_excludes_promoted_columns(self):
        """raw_metadata must not duplicate any field we lifted to a typed column."""
        record = _load_fixture_artwork()
        mapped = map_record_to_object(record, LoaderStats())

        promoted_keys = {
            "id", "title", "main_reference_number", "date_display",
            "date_start", "date_end", "department_title",
            "classification_title", "artwork_type_title", "medium_display",
            "is_public_domain", "is_on_view", "image_id", "source_updated_at",
        }
        for key in promoted_keys:
            assert key not in mapped["raw_metadata"], (
                f"raw_metadata leaked promoted column '{key}'"
            )
        # Non-promoted AIC fields preserved (escape-hatch convention).
        assert "artist_display" in mapped["raw_metadata"]

    def test_transform_is_pure_no_input_mutation(self):
        """map_record_to_object must not mutate its input dict."""
        record = _load_fixture_artwork()
        snapshot = json.loads(json.dumps(record))

        map_record_to_object(record, LoaderStats())
        map_record_to_object(record, LoaderStats())

        assert record == snapshot


# ---------------------------------------------------------------------------
# Idempotency tests (DB required)
# ---------------------------------------------------------------------------

# .env lives at the repo root: web/.env. This file is at
# web/loaders/aic/tests/test_objects.py, so three .parent hops up.
load_dotenv(Path(__file__).resolve().parents[3] / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL")

needs_db = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="DATABASE_URL not set; idempotency test requires a real DB",
)


def _write_dump_dir(tmp_path: Path) -> Path:
    """Materialize three synthetic dump-shaped JSON files under tmp_path
    and return the directory the loader should iterate.

    The `id` field carries a synthetic int that maps to the str values in
    `FIXTURE_OBJECT_IDS` (the loader stringifies). This mirrors the
    real dump's "one bare artwork JSON per file" layout.
    """
    base_record = _load_fixture_artwork()
    dump_dir = tmp_path / "artworks"
    dump_dir.mkdir()
    for source_id in FIXTURE_OBJECT_IDS:
        record = dict(base_record)
        record["id"] = int(source_id)
        record["main_reference_number"] = f"FIXTURE.{source_id}"
        with open(dump_dir / f"{source_id}.json", "w") as f:
            json.dump(record, f)
    return dump_dir


@pytest.fixture
def db_conn():
    """Connection wrapped in cleanup that runs before AND after each test
    so a failed prior run can't poison the next one."""
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


def _fixture_args(dump_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        dump_dir=dump_dir,
        rest_since=None,
        limit=None,
        batch_size=500,
        dry_run=False,
    )


@needs_db
class TestIdempotency:
    """The contract that replaces a queue's retry/DLQ.

    Re-running the loader on the same input must produce zero new
    inserts. Per Decision 2026-04-30 (no queue, no scheduler), this is
    the entire failure-recovery story — if it fails, partial-failure
    recovery by re-run is broken.
    """

    def test_second_run_inserts_zero_rows(self, db_conn, tmp_path):
        dump_dir = _write_dump_dir(tmp_path)
        expected = len(FIXTURE_OBJECT_IDS)

        first = run(db_conn, _fixture_args(dump_dir))
        assert first.rows_inserted == expected, (
            f"first run: expected {expected} inserts, got {first.rows_inserted}"
        )
        assert first.rows_updated == 0

        second = run(db_conn, _fixture_args(dump_dir))
        assert second.rows_inserted == 0, (
            f"loader is non-idempotent: second run produced "
            f"{second.rows_inserted} inserts (expected 0). "
            f"Re-running after a partial failure would create duplicate rows."
        )
        assert second.rows_updated == expected

    def test_ingested_at_immutable_across_reruns(self, db_conn, tmp_path):
        """Per Decision 2026-05-04 freshness pattern: ingested_at is set
        on first INSERT and never moves; last_seen_at bumps every upsert."""
        dump_dir = _write_dump_dir(tmp_path)

        run(db_conn, _fixture_args(dump_dir))
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT source_object_id, ingested_at FROM objects "
                "WHERE source = %s AND source_object_id = ANY(%s)",
                (SOURCE, FIXTURE_OBJECT_IDS),
            )
            first_ingested_at = {row[0]: row[1] for row in cur.fetchall()}

        run(db_conn, _fixture_args(dump_dir))
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
