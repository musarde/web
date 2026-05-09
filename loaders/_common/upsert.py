"""Generic batched-upsert executor.

The single primitive that backs every loader's table writes:
`executemany(sql, records, returning=True)` plus the result-set walking
that Postgres requires when you want one returned row per input row.

The SQL is owned by the caller (each (source, table) loader has its own
INSERT ... ON CONFLICT DO UPDATE statement that knows its own columns
and conflict key). This helper is responsible only for the bind/execute/
collect-rows mechanics.

Convention for callers that want (inserted, updated) counts: include
`(xmax = 0) AS inserted` in the RETURNING clause and pass the result
rows to `count_inserts_updates`. Postgres sets `xmax = 0` on a fresh
INSERT and to the txid on the UPDATE branch, so the boolean flips for
free without an extra round-trip.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def execute_returning_batch(
    conn: psycopg.Connection,
    sql: str,
    records: list[dict[str, Any]],
    jsonb_fields: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Execute `sql` once per record. Return one row per input record, in input order.

    `jsonb_fields` lists keys whose values should be wrapped as Jsonb
    before binding (psycopg won't coerce raw dicts into JSONB columns).
    Records are not mutated; copies are made when wrapping is needed.

    Caller's `sql` must be a single statement that RETURNING-yields
    exactly one row per execution — typically
    `INSERT ... ON CONFLICT DO UPDATE ... RETURNING ...`. A statement
    that conditionally returns zero rows (e.g. ON CONFLICT DO NOTHING
    without a forced row) breaks the input → output positional mapping
    and must use a different helper.
    """
    if not records:
        return []

    if jsonb_fields:
        prepared = []
        for record in records:
            rec = dict(record)
            for field in jsonb_fields:
                if field in rec:
                    rec[field] = Jsonb(rec[field])
            prepared.append(rec)
    else:
        prepared = records

    result_rows: list[dict[str, Any]] = []
    with conn.cursor(row_factory=dict_row) as cur:
        cur.executemany(sql, prepared, returning=True)
        while True:
            row = cur.fetchone()
            if row is not None:
                result_rows.append(row)
            if not cur.nextset():
                break

    assert len(result_rows) == len(records), (
        f"executemany returned {len(result_rows)} rows for {len(records)} input records — "
        f"the SQL must return exactly one row per execution"
    )
    return result_rows


def count_inserts_updates(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Tally inserts vs updates from rows that include `(xmax = 0) AS inserted`."""
    inserted = sum(1 for row in rows if row["inserted"])
    updated = len(rows) - inserted
    return (inserted, updated)
