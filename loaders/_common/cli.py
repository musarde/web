"""Shared CLI argument shape for loaders.

Every loader takes `--limit`, `--batch-size`, and `--dry-run`. Source-
specific args (e.g. Met's `--csv`, AIC's `--dump-dir` / `--rest-since`)
stay in the per-source `parse_args`.
"""

from __future__ import annotations

import argparse


def add_common_args(parser: argparse.ArgumentParser, default_batch_size: int = 500) -> None:
    """Add --limit, --batch-size, --dry-run to an existing parser."""
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after processing N source records. Omit to process the full input.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=default_batch_size,
        help=f"Records per upsert batch (default: {default_batch_size}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and tally without writing to the database.",
    )
