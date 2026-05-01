---
name: ingestion-adapter
description: Scaffold a new museum-source ingestion adapter for the Musarde data pipeline, encoding the project's required conventions (raw_metadata JSONB escape hatch on the artworks table, separate texts table for long-form fields, idempotent upserts keyed on (source, source_id), embedding model versioning, and structured logging with source/batch_id/duration). The loader is a re-runnable one-shot script — no queue, no scheduler, no worker tier (cut in the Week 0 decisions log). Use this skill when the user says "add adapter for <museum>," "scaffold ingestion for <source>," "wire up <museum> ingestion," "onboard <source> as a museum source," or asks how to integrate a new museum API (Met, AIC, Getty, etc.) into the Musarde pipeline. Do not trigger for general data-pipeline work outside the museum-ingestion context.
---

# ingestion-adapter

Scaffold a new museum-source ingestion adapter that conforms to the Musarde pipeline conventions. Before writing any code, read the brief and confirm scope — v1 is **Met (CSV) + AIC (REST) + Getty (Linked Open Data) + SAM (manually catalogued ~100 works)**. Seattle museums via scraping are explicitly deferred. If the requested source isn't on that list, push back and surface the scope question to the user.

## Pipeline shape (locked in Week 0)

The loader is a **re-runnable one-shot script**. There is no queue, no scheduler, no worker tier. The decision and rationale are logged in `../build-log/decisions.md` ("Ingestion shape — one-shot loader, no queue, no scheduler"). The short version: museum collection data updates on the order of months, bulk ingestion happens twice in v1, and the user-facing photo upload path is synchronous. A queue with DLQ would solve a problem the app does not have.

Concrete consequences for adapter scaffolding:

- The adapter is a script run on demand from the user's laptop (or a one-shot VM for the ~680K bulk Met/AIC/Getty ingest). It is not a long-lived process.
- Re-runs must be safe. Idempotent upserts on natural keys do the work that retry/DLQ would in a queued system. Crashing halfway through and re-running has to leave the DB in the same state as a clean run.
- Failures are surfaced via structured logs and exit codes, not retried automatically. The user re-runs after fixing whatever broke.
- Embeddings are a **separate re-runnable script**, not enqueued mid-ingest. Ingest lands `artworks` + `texts`; the embeddings script reads rows with missing or stale-model-version embeddings and fills them. Both scripts are idempotent on the same keys.

If a future source genuinely needs streaming/webhook ingestion, that's a "would revisit" trigger — surface it to the user before scaffolding around the queue-less assumption.

## Before scaffolding

1. **Read `../build-log/musarde-project.md`** for the canonical schema and pipeline shape — particularly the data-model section that defines `artworks` and `texts`. The `raw_metadata` JSONB column and the `texts` table shape are called out as critical Week 1 decisions; preserve them.
2. **Read `../build-log/decisions.md`** for any logged decisions about ingestion, retrieval, embedding, or schema. The adapter must match what the decisions log specifies, not what feels reasonable in isolation. The "no queue, no scheduler" decision in particular is load-bearing for the file layout below.
3. **Skim `../build-log/glossary.md`** so naming (sources, schema columns, retrieval shapes) matches the rest of the project.
4. **Look for existing adapters.** Check `src/ingestion/adapters/` (or whatever directory holds them) for `met/`, `aic/`, `getty/`. If they exist, treat them as canonical examples and mirror their structure exactly — naming, file layout, helper imports, logging shape. If they don't exist yet, you are establishing the pattern; flag that to the user.
5. **Confirm the source is on the v1 list.** v1 sources are Met + AIC + Getty + SAM (manual). v1.5/v2 ambiguity gets resolved as "defer" by default per the brief — don't scaffold a Tate/V&A/Cleveland adapter just because the API exists.
6. **Confirm the source has a clean API (or a manual catalog path for SAM).** If a requested source requires scraping, stop and ask whether to defer to v1.5/v2 instead of scaffolding.

## Required conventions

Every adapter must encode these. They are not negotiable defaults — they are project-level invariants that other parts of the pipeline assume.

### Schema contracts

- **`artworks` table** is the canonical record. Stable columns hold normalized fields the retrieval layer queries on (title, artist, date, medium, source, source_id, image_url, etc.). Anything source-specific that doesn't fit a stable column goes into the `raw_metadata` JSONB column. The escape hatch is critical — never widen the stable schema for a single source's quirk.
- **`texts` table** holds long-form fields (curator notes, gallery labels, catalog essays, provenance prose). One row per (artwork_id, text_type, source, lang). Don't stuff long text into `artworks` — embeddings index `texts` separately.
- **Idempotent upsert keyed on `(source, source_id)`.** Re-running the adapter on the same input must be safe and produce the same final state. Use `INSERT ... ON CONFLICT (source, source_id) DO UPDATE` (Postgres) or the equivalent. Never blind-insert. This is the load-bearing convention now that there is no queue/retry layer to compensate for non-idempotent writes.
- **Texts upserts** are keyed on `(artwork_id, text_type, source, lang)`. Same idempotency contract.

### Embeddings (separate from ingest)

- **Model versioning is required.** Every embedding row records the model name and version (`embedding_model`, `embedding_model_version`). When the model changes, old vectors stay queryable until a backfill completes — never overwrite in place without versioning.
- The adapter **does not compute embeddings inline.** Ingest lands `artworks` and `texts` rows. A separate embeddings script reads rows where the embedding is missing or the model version is stale, computes, and upserts. Both scripts are idempotent — running either twice in a row is a no-op on the second pass.
- This separation is what replaces the "enqueue embedding job" step from the queued design. The script-pair is the queue.

### Logging

Use structured logs (JSON or key=value). Every log line from an adapter run must carry:

- `source` — e.g., `"met"`, `"aic"`, `"getty"`, `"sam"`
- `batch_id` — UUID generated at the start of the run; lets you correlate every log line from a single invocation across both the ingest script and the downstream embeddings script
- `duration_ms` — for any unit of work that takes nontrivial time (HTTP fetch, DB upsert batch, transform pass)

Plus the obvious: level, message, error if any, source_id when relevant. Don't `print`. Don't log secrets or full image bytes. End-of-run summary line should report: rows seen, rows upserted (insert vs. update), rows skipped, rows errored. That's the human-readable smoke test for whether a re-run did what you expected.

## File layout

Mirror existing adapters once they exist. Until then, the canonical layout is:

```
src/ingestion/adapters/<source>/
├── __init__.py            # exports the adapter entry point
├── client.py              # source access: HTTP client + auth + rate limiting (REST/LOD), CSV reader (Met), or local-file loader (SAM)
├── transform.py           # source response/row → artworks row + texts rows (pure, no I/O)
├── adapter.py             # orchestration: fetch → transform → upsert artworks → upsert texts
├── run.py                 # CLI entry point: `python -m ingestion.adapters.<source>.run [--limit N] [--since DATE]`
└── tests/
    ├── fixtures/          # captured API responses or CSV samples for unit tests
    ├── test_transform.py  # transform is pure — test it in isolation
    └── test_adapter.py    # adapter end-to-end against fixtures + a test DB
```

The transform layer is **pure** (no I/O) so it can be unit-tested without hitting the real API or DB. The adapter layer is the only place that touches network or database. `run.py` is the user-facing CLI — it parses args, sets up logging with a fresh `batch_id`, calls the adapter, and exits with a non-zero code on failure.

There is no `worker.py`, no `queue.py`, no `dead_jobs` handling. If you find yourself reaching for one, that's the signal to re-read the Week 0 decisions-log entry.

## What to scaffold

When asked to add an adapter for a source, produce:

1. The directory and files above, with skeletons that have the right imports, function signatures, and `# TODO` markers where source-specific logic goes.
2. A migration (if needed) — most adapters won't need new columns because `raw_metadata` absorbs source-specific fields. If you do need a new column, justify it in the PR and consider whether `raw_metadata` would have done.
3. A fixture-loading test in `test_transform.py` that proves the transform produces a valid `artworks` row + at least one `texts` row from a real captured response.
4. An idempotency test in `test_adapter.py` that runs the adapter twice against the same fixture and asserts the second run produces zero new inserts (only updates, ideally no-op updates). Without a queue/retry layer, this test is the safety net.
5. A short note appended to `../build-log/decisions.md` ONLY if onboarding this source involved a real architectural choice (e.g., "picked Met's bulk CSV over per-record API for the initial ingest because…"). Otherwise don't pad the decisions log.

## After scaffolding

Tell the user what's stubbed vs. real, what they need to fill in (almost always: API auth, the field-mapping in `transform.py`, the captured fixture), and which conventions they should re-verify before the first real run. Specifically call out:

- The idempotency test result — if it doesn't pass on the stub, the adapter is not safe to re-run.
- Whether the source has any update-cadence assumption that would conflict with the "re-run quarterly or on-demand" model. If a source publishes daily diffs the user will actually want to consume, that's a queue-revisit trigger and worth flagging.
- The end-of-run summary log line — confirm the user knows what counts they should see on a clean run vs. a re-run.

Surface any conventions you couldn't fully encode because the source's API shape is unusual.
