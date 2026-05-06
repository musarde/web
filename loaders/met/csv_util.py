"""Met CSV parsing utilities shared by all Met loaders.

Holds primitives that any script reading MetObjects.csv needs: streaming
row iteration with Met's encoding/embedded-newline quirks handled, and
year coercion that respects Met's `9999` end-date sentinel. Kept in its
own module so loader scripts (objects.py, artists.py, future ones) don't
import from each other — each loader stays independently runnable.
"""

from __future__ import annotations

import csv
import sys
from collections.abc import Iterator
from pathlib import Path

# Met cells (notably Description, Provenance) exceed the csv module's
# default ~131KB per-field limit. Raise it once at import time.
csv.field_size_limit(sys.maxsize)


def iter_csv_rows(csv_path: Path) -> Iterator[dict[str, str]]:
    """Yield Met CSV rows as dicts; BOM- and embedded-newline-aware."""
    with open(csv_path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            yield row


def coerce_year(raw: str | None) -> tuple[int | None, bool]:
    """Parse a Met year string. Return (year_or_None, was_dirty); 9999 → (None, False)."""
    if raw is None or raw.strip() == "":
        return (None, False)
    try:
        value = int(raw)
    except ValueError:
        return (None, True)
    if value == 9999:
        return (None, False)
    return (value, False)
