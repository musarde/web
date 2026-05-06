"""Apply Musarde v1 schema migration 001 and verify the result.

Reads DATABASE_URL from .env, applies db/migrations/001_v1_schema.sql in
a single transaction, then prints an inventory of every table, index,
constraint, and FK so you can eyeball that nothing landed wrong.

Exits non-zero if any expected table is missing or the pgvector
extension didn't load. Otherwise prints "OK" and exits 0.

Usage:
    python scripts/apply_migration_001.py              # apply + verify
    python scripts/apply_migration_001.py --verify     # verify only
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILE = REPO_ROOT / "db" / "migrations" / "001_v1_schema.sql"

EXPECTED_TABLES = [
    "objects",
    "images",
    "image_embeddings",
    "artists",
    "object_artists",
    "documents",
    "document_objects",
    "document_artists",
    "document_chunks",
]


def apply_migration(conn: psycopg.Connection) -> None:
    """Execute the v1 schema SQL file in a single committed transaction."""
    sql = MIGRATION_FILE.read_text()
    print(f"Reading migration: {MIGRATION_FILE.relative_to(REPO_ROOT)} ({len(sql):,} chars)")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("Migration applied (transaction committed).")


def verify(conn: psycopg.Connection) -> bool:
    """Print schema inventory; True iff all expected tables present and pgvector loaded."""
    ok = True
    with conn.cursor() as cur:
        # Extension
        cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
        row = cur.fetchone()
        if row:
            print(f"\n[ext] vector {row[1]}")
        else:
            print("\n[ext] vector  -- MISSING")
            ok = False

        # Tables
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        actual_tables = {r[0] for r in cur.fetchall()}
        expected = set(EXPECTED_TABLES)
        missing = expected - actual_tables
        unexpected = actual_tables - expected

        print(f"\n[tables] {len(actual_tables & expected)}/{len(expected)} expected")
        for t in EXPECTED_TABLES:
            mark = "  +" if t in actual_tables else "  ! MISSING"
            print(f"{mark} {t}")
        if unexpected:
            print(f"  (also present, not expected: {sorted(unexpected)})")
        if missing:
            ok = False

        # Indexes per table
        cur.execute("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)
        rows = cur.fetchall()
        print(f"\n[indexes] {len(rows)} total")
        last_table = None
        for tablename, indexname, indexdef in rows:
            if tablename != last_table:
                print(f"  {tablename}:")
                last_table = tablename
            kind = _index_kind(indexdef)
            print(f"    {kind:<16} {indexname}")

        # Constraints (CHECK + FK; PK and UNIQUE show up via indexes already)
        cur.execute("""
            SELECT
                c.conrelid::regclass::text AS table_name,
                c.conname AS constraint_name,
                c.contype,
                pg_get_constraintdef(c.oid) AS def
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public'
              AND c.contype IN ('c', 'f')
            ORDER BY table_name, c.contype DESC, c.conname;
        """)
        constraints = cur.fetchall()
        check_count = sum(1 for _, _, t, _ in constraints if t == "c")
        fk_count = sum(1 for _, _, t, _ in constraints if t == "f")
        print(f"\n[constraints] {check_count} CHECK, {fk_count} FK")
        last_table = None
        for table_name, conname, contype, defn in constraints:
            if table_name != last_table:
                print(f"  {table_name}:")
                last_table = table_name
            kind = "CHECK" if contype == "c" else "FK"
            print(f"    [{kind}] {conname}: {defn}")

    return ok


def _index_kind(indexdef: str) -> str:
    """Classify a pg_indexes definition string into a short tag for the inventory printout."""
    if "USING gin" in indexdef:
        return "[GIN]"
    if "USING hnsw" in indexdef:
        return "[HNSW]"
    if "UNIQUE" in indexdef and "WHERE" in indexdef:
        return "[partial UQ]"
    if "UNIQUE" in indexdef:
        return "[UNIQUE]"
    return "[btree]"


def main() -> int:
    """Parse args, load DATABASE_URL, apply/verify schema; exit 0 ok, 1 fail, 2 missing config."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Skip the apply step; only print the schema inventory.",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment or .env.", file=sys.stderr)
        return 2

    with psycopg.connect(db_url) as conn:
        if not args.verify:
            apply_migration(conn)

        ok = verify(conn)

    print()
    if ok:
        print("OK: all expected schema elements present.")
        return 0
    else:
        print("FAIL: schema verification found missing elements (see above).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
