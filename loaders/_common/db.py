"""Database connection helpers shared by every loader.

Single place for the .env discovery + DATABASE_URL lookup. Kept tiny
because the no-queue ingestion shape (Decision 2026-04-30) means the
loader's only DB concern is a single `psycopg.connect(url)` call —
there is no pool, no worker tier, no long-lived process.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# loaders/_common/db.py → web/ is two parents up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def get_database_url() -> str | None:
    """Load .env from the repo root and return DATABASE_URL (or None)."""
    load_dotenv(REPO_ROOT / ".env")
    return os.environ.get("DATABASE_URL")
