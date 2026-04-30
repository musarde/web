---
name: ingestion-adapter
description: Scaffold a new museum-source ingestion adapter for the Musarde data pipeline, encoding the project's required conventions (raw_metadata JSONB escape hatch on the artworks table, separate texts table for long-form fields, idempotent upserts keyed on (source, source_id), retry/DLQ via the Postgres SKIP LOCKED job queue, embedding model versioning, and structured logging with source/batch_id/duration). Use this skill when the user says "add adapter for <museum>," "scaffold ingestion for <source>," "wire up <museum> ingestion," "onboard <source> as a museum source," or asks how to integrate a new museum API (Met, AIC, Tate, V&A, Smithsonian, Cleveland, Harvard, Rijksmuseum, etc.) into the Musarde pipeline. Do not trigger for general data-pipeline work outside the museum-ingestion context.
---

# ingestion-adapter

Scaffold a new museum-source ingestion adapter that conforms to the Musarde pipeline conventions. Before writing any code, read the brief and confirm scope — v1 is **Met + AIC + one third source**. Seattle museums via scraping are explicitly deferred. If the requested source isn't on that list, push back and surface the scope question to the user.

## Before scaffolding

1. **Read `musarde_project.md`** for the canonical schema and pipeline shape — particularly the data-model section that defines `artworks`, `texts`, and the job queue. The `raw_metadata` JSONB column and the `texts` table shape are called out as critical Week 1 decisions; preserve them.
2. **Look for existing adapters.** Check `src/ingestion/adapters/` (or whatever directory holds them) for `met.py`/`met.ts` and `aic.py`/`aic.ts`. If they exist, treat them as canonical examples and mirror their structure exactly — naming, file layout, helper imports, logging shape. If they don't exist yet, you are establishing the pattern; flag that to the user.
3. **Confirm the source has a clean API.** v1 is "clean APIs only" per the brief. If the source requires scraping, stop and ask whether to defer to v1.5/v2 instead of scaffolding.
4. **Check `build-log/decisions.md`** for any logged decisions about retrieval, embedding, or queue shape — the adapter must match what the decisions log specifies, not what feels reasonable in isolation.

## Required conventions

Every adapter must encode these. They are not negotiable defaults — they are project-level invariants that other parts of the pipeline assume.

### Schema contracts

- **`artworks` table** is the canonical record. Stable columns hold normalized fields the retrieval layer queries on (title, artist, date, medium, source, source_id, image_url, etc.). Anything source-specific that doesn't fit a stable column goes into the `raw_metadata` JSONB column. The escape hatch is critical — never widen the stable schema for a single source's quirk.
- **`texts` table** holds long-form fields (curator notes, gallery labels, catalog essays, provenance prose). One row per (artwork_id, text_type, source, lang). Don't stuff long text into `artworks` — embeddings index `texts` separately.
- **Idempotent upsert** keyed on `(source, source_id)`. Re-running the adapter on the same input must be safe. Use `INSERT ... ON CONFLICT (source, source_id) DO UPDATE` (Postgres) or the equivalent. Never blind-insert.

### Job queue

- Use the Postgres **`SKIP LOCKED` queue** (decided over Redis Streams / SQS — see `build-log/decisions.md`). One job row per artwork or batch. The worker claims with `SELECT ... FOR UPDATE SKIP LOCKED LIMIT N`.
- **Retries:** `attempt_count` + `next_attempt_at` on the job row. Exponential backoff. Cap at N attempts (typically 5).
- **DLQ:** when `attempt_count` exceeds the cap, move the job to a `dead_jobs` table (or set `status = 'dead'`) with the last error. Don't silently drop.

### Embeddings

- **Model versioning** is required. Every embedding row records the model name and version (`embedding_model`, `embedding_model_version`). When the model changes, old vectors stay queryable until a backfill completes — never overwrite in place without versioning.
- The adapter doesn't compute embeddings inline. It enqueues an embedding job after the artwork row lands. Keep responsibilities separate: ingest → upsert → enqueue.

### Logging

Use structured logs (JSON or key=value). Every log line from an adapter run must carry:

- `source` — e.g., `"met"`, `"aic"`
- `batch_id` — UUID generated at the start of the run
- `duration_ms` — for any unit of work that takes nontrivial time (HTTP fetch, DB upsert, batch process)

Plus the obvious: level, message, error if any, source_id when relevant. Don't `print`. Don't log secrets or full image bytes.

## File layout

Mirror existing adapters once they exist. Until then, the canonical layout is:

```
src/ingestion/adapters/<source>/
├── __init__.py            # exports the adapter entry point
├── client.py              # HTTP client + auth + rate limiting for the source API
├── transform.py           # source response → artworks row + texts rows
├── adapter.py             # orchestration: fetch → transform → upsert → enqueue embedding jobs
└── tests/
    ├── fixtures/          # captured API responses for unit tests
    ├── test_transform.py  # transform is pure — test it in isolation
    └── test_adapter.py    # adapter end-to-end against fixtures
```

The transform layer is **pure** (no I/O) so it can be unit-tested without hitting the real API or DB. The adapter layer is the only place that touches network or database.

## What to scaffold

When asked to add an adapter for a source, produce:

1. The directory and files above, with skeletons that have the right imports, function signatures, and `# TODO` markers where source-specific logic goes.
2. A migration (if needed) — most adapters won't need new columns because `raw_metadata` absorbs source-specific fields.
3. A fixture-loading test in `test_transform.py` that proves the transform produces a valid `artworks` row + at least one `texts` row from a real captured response.
4. A short note appended to `build-log/decisions.md` ONLY if onboarding this source involved a real architectural choice (e.g., "picked their bulk-export endpoint over per-record pagination because…"). Otherwise don't pad the decisions log.

## After scaffolding

Tell the user what's stubbed vs. real, what they need to fill in (almost always: API auth, the field-mapping in `transform.py`, the captured fixture), and which conventions they should re-verify before the first real run. Surface any conventions you couldn't fully encode because the source's API shape is unusual.
