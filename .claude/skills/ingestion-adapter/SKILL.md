---
name: ingestion-adapter
description: Scaffold a new museum-source ingestion adapter for the Musarde data pipeline, encoding the project's required conventions (raw_metadata JSONB escape hatch on the objects table, separate documents table for long-form fields, idempotent upserts keyed on (source, source_object_id), embedding model versioning, and structured logging with source/batch_id/duration). The loader is a re-runnable one-shot script — no queue, no scheduler, no worker tier (cut in the Week 0 decisions log). Use this skill when the user says "add adapter for <museum>," "scaffold ingestion for <source>," "wire up <museum> ingestion," "onboard <source> as a museum source," or asks how to integrate a new museum API (Met, AIC, Getty, etc.) into the Musarde pipeline. Do not trigger for general data-pipeline work outside the museum-ingestion context.
---

# ingestion-adapter

Scaffold a new museum-source ingestion adapter that conforms to the Musarde pipeline conventions. Before writing any code, read the brief and confirm scope — v1 is **Met (CSV) + AIC (REST) + Getty (Linked Open Data) + SAM (manually catalogued ~100 works)**. Seattle museums via scraping are explicitly deferred. If the requested source isn't on that list, push back and surface the scope question to the user.

## Pipeline shape (locked in Week 0)

The loader is a **re-runnable one-shot script**. There is no queue, no scheduler, no worker tier. The decision and rationale are logged in `../build-log/decisions.md` ("Ingestion shape — one-shot loader, no queue, no scheduler"). The short version: museum collection data updates on the order of months, bulk ingestion happens twice in v1, and the user-facing photo upload path is synchronous. A queue with DLQ would solve a problem the app does not have.

Concrete consequences for adapter scaffolding:

- The adapter is a script run on demand from the user's laptop (or a one-shot VM for the ~680K bulk Met/AIC/Getty ingest). It is not a long-lived process.
- Re-runs must be safe. Idempotent upserts on natural keys do the work that retry/DLQ would in a queued system. Crashing halfway through and re-running has to leave the DB in the same state as a clean run.
- Failures are surfaced via structured logs and exit codes, not retried automatically. The user re-runs after fixing whatever broke.
- Embeddings are a **separate re-runnable script**, not enqueued mid-ingest. Ingest lands `objects` + `documents`; the embeddings script reads rows with missing or stale-model-version embeddings and fills them. Both scripts are idempotent on the same keys.

If a future source genuinely needs streaming/webhook ingestion, that's a "would revisit" trigger — surface it to the user before scaffolding around the queue-less assumption.

## Before scaffolding

1. **Read `../build-log/musarde-project.md`** for the canonical schema and pipeline shape — particularly the data-model section that defines `objects` and `documents`. The `raw_metadata` JSONB column and the `documents` table shape are called out as critical Week 1 decisions; preserve them.
2. **Read `../build-log/decisions.md`** for any logged decisions about ingestion, retrieval, embedding, or schema. The adapter must match what the decisions log specifies, not what feels reasonable in isolation. The "no queue, no scheduler" decision in particular is load-bearing for the file layout below.
3. **Skim `../build-log/glossary.md`** so naming (sources, schema columns, retrieval shapes) matches the rest of the project.
4. **Look for existing adapters.** Check `loaders/` for `met/`, `aic/`, `getty/`. If they exist, treat them as canonical examples and mirror their structure exactly — naming, file layout, helper imports, logging shape. If they don't exist yet, you are establishing the pattern; flag that to the user.
5. **Confirm the source is on the v1 list.** v1 sources are Met + AIC + Getty + SAM (manual). v1.5/v2 ambiguity gets resolved as "defer" by default per the brief — don't scaffold a Tate/V&A/Cleveland adapter just because the API exists.
6. **Confirm the source has a clean API (or a manual catalog path for SAM).** If a requested source requires scraping, stop and ask whether to defer to v1.5/v2 instead of scaffolding.

## Required conventions

Every adapter must encode these. They are not negotiable defaults — they are project-level invariants that other parts of the pipeline assume.

### Schema contracts

- **`objects` table** is the canonical record. Stable columns hold normalized fields the retrieval layer queries on (title, object_name, date_string, date_start_year, date_end_year, classification, medium, source, source_object_id, etc.). Anything source-specific that doesn't fit a stable column goes into the `raw_metadata` JSONB column. The escape hatch is critical — never widen the stable schema for a single source's quirk.
- **`documents` + `document_objects` + `document_artists` + `document_chunks`** hold long-form fields (curator notes, gallery labels, catalog essays, artist biographies, criticism, etc.). Per the 2026-05-04 Option B decision: `documents` is the content table; `document_objects` and `document_artists` are M:N joins to `objects` and `artists` respectively; `document_chunks` holds RAG-ready chunks. Don't stuff long text into `objects` — embeddings index `document_chunks` separately.
- **Idempotent upsert keyed on `(source, source_object_id)`** for `objects`. Re-running the adapter on the same input must be safe and produce the same final state. Use `INSERT ... ON CONFLICT (source, source_object_id) DO UPDATE` (Postgres) or the equivalent. Never blind-insert. This is the load-bearing convention now that there is no queue/retry layer to compensate for non-idempotent writes. Same shape for `artists` (`(source, source_artist_id)`).
- **Documents upserts** are keyed on `(source, source_document_id)` via a partial unique index `WHERE source_document_id IS NOT NULL` (the `'curated'` source is allowed to omit the upstream ID). Junction-table upserts are keyed on `(document_id, object_id)` and `(document_id, artist_id)` respectively. Same idempotency contract.

### Embeddings (separate from ingest)

- **Model versioning is required.** Every embedding row records the model name and version (`model_name`, `model_version` on `image_embeddings`; same shape will apply to `document_chunk_embeddings` once the Week 1 text-embedding bake-off picks a winner). When the model changes, old vectors stay queryable until a backfill completes — never overwrite in place without versioning.
- The adapter **does not compute embeddings inline.** Ingest lands `objects`, `images`, `artists`, `documents`, `document_chunks` rows. A separate embeddings script reads rows where the embedding is missing or the model version is stale, computes, and upserts. Both scripts are idempotent — running either twice in a row is a no-op on the second pass.
- This separation is what replaces the "enqueue embedding job" step from the queued design. The script-pair is the queue.

### Logging

Use structured logs (JSON or key=value). Every log line from an adapter run must carry:

- `source` — e.g., `"met"`, `"aic"`, `"getty"`, `"sam"`
- `batch_id` — UUID generated at the start of the run; lets you correlate every log line from a single invocation across both the ingest script and the downstream embeddings script
- `duration_ms` — for any unit of work that takes nontrivial time (HTTP fetch, DB upsert batch, transform pass)

Plus the obvious: level, message, error if any, `source_object_id` when relevant. Don't `print`. Don't log secrets or full image bytes. End-of-run summary line should report: rows seen, rows upserted (insert vs. update), rows skipped, rows errored. That's the human-readable smoke test for whether a re-run did what you expected.

## File layout

The unit of file decomposition is **(source, table)**, not source. Each source populates many tables — `objects`, `artists`, `images`, `documents`, the document M:N joins, `document_chunks` — and each is its own re-runnable ingest target with its own natural key. Bundling them into a single per-source file makes a multi-thousand-line grab-bag and breaks partial re-runs. Splitting each (source, table) pair into separate `client.py` / `transform.py` / `adapter.py` / `run.py` files multiplies the file count by ~5× without buying anything: those four files are not reusable across sources or across tables, so the split optimizes for intra-file separation-of-concerns at the cost of repo navigability.

Three axes of reuse, three places code lives:

```
loaders/
├── _common/                 # cross-source plumbing — used by every (source, table) loader
│   ├── upsert.py            # parameterized ON CONFLICT helper (table, conflict-key, columns)
│   ├── stats.py             # LoaderStats + print_summary
│   ├── cli.py               # base argparser (--limit, --batch-size, --dry-run)
│   ├── logging.py           # structured logging with source + batch_id + duration_ms
│   └── db.py                # load_dotenv + DATABASE_URL + psycopg.connect helper
├── met/
│   ├── _csv.py              # per-source helper: BOM-aware reader, field-size limit, row iter
│   ├── objects.py           # one file per (source, table) ingest target
│   ├── artists.py
│   ├── images.py
│   ├── documents.py
│   └── ...
├── aic/
│   ├── _client.py           # per-source helper: HTTP client + auth + rate limit
│   ├── objects.py
│   └── ...
├── getty/
│   ├── _sparql.py           # per-source helper: SPARQL endpoint + result iteration
│   └── objects.py
└── sam/
    ├── _catalog.py          # per-source helper: local-file catalog loader
    └── objects.py
```

Each `<source>/<table>.py` is shaped like the existing `loaders/met/objects.py`: a pure mapping function (`map_row_to_<table>`), table-specific upsert SQL, a `run()` that drives stream → batch → upsert, and a `main()` CLI entry. Purity of the mapping function is enforced at the function level, not by giving it its own file — the existing `map_row_to_object` is already trivially testable in isolation without a separate `transform.py`. Tests for that file live in `loaders/<source>/tests/test_<table>.py`.

There is no `worker.py`, no `queue.py`, no `dead_jobs` handling. If you find yourself reaching for one, that's the signal to re-read the Week 0 decisions-log entry.

### Shared library extraction policy

Do not pre-build `_common/` or per-source helper files (`_csv.py`, `_client.py`, `_sparql.py`). Promote shared code into them only when the **second user** appears.

- Met objects (Day 2) is the first user of the upsert pattern, `LoaderStats`, the CLI args, and the DB connection helper. It lives entirely inside `loaders/met/objects.py` — a single ~330-line file, not split into 4–5 files.
- The first AIC loader (Day 3+) will be the second user. That is when `_common/` gets created, with the shape that both Met and AIC genuinely share. Met objects gets refactored at the same time so both adapters use the same plumbing.
- Same rule for per-source helpers: a `met/_csv.py` is created only when Met gets a *second* table loader (e.g. `artists.py`) that needs the same CSV reader, not while `objects.py` is the only file in the directory.

Extracting from a single example produces speculative abstractions that the second user has to fight. Extracting from two real users produces a helper shaped by actual reuse. This matches the Week 0 workload-vs-resume filter: name a concrete second caller before adding the abstraction.

## What to scaffold

When asked to add a loader for a (source, table) pair, produce:

1. A single file at `loaders/<source>/<table>.py` shaped like `loaders/met/objects.py`: pure mapping function, table-specific upsert SQL, `run()`, `main()`, `# TODO` markers where source-specific logic goes. Do not pre-create `client.py` / `transform.py` / `adapter.py` / `run.py` — that's the splay the layout section explicitly rejects.
2. If this is the second user of any helper that already lives inline in another loader (upsert exec, `LoaderStats`, CLI args, DB connection, source-level CSV/HTTP/SPARQL helper), extract it per the shared-library extraction policy. Refactor the first user in the same change so both call sites share the helper.
3. A migration (if needed) — most loaders won't need new columns because `raw_metadata` absorbs source-specific fields. If you do need a new column, justify it in the PR and consider whether `raw_metadata` would have done.
4. A fixture-loading test in `loaders/<source>/tests/test_<table>.py` that proves the mapping function produces a valid row from a real captured response (CSV sample, API JSON, SPARQL result, etc.). Fixtures live in `loaders/<source>/tests/fixtures/`.
5. An idempotency test in the same `test_<table>.py` that runs the loader twice against the same fixture and asserts the second run produces zero new inserts (only updates, ideally no-op updates). Without a queue/retry layer, this test is the safety net.
6. A short note appended to `../build-log/decisions.md` ONLY if onboarding this loader involved a real architectural choice (e.g., "picked Met's bulk CSV over per-record API for the initial ingest because…"). Otherwise don't pad the decisions log.

## After scaffolding

Tell the user what's stubbed vs. real, what they need to fill in (almost always: API auth, the field-mapping inside `map_row_to_<table>`, the captured fixture), and which conventions they should re-verify before the first real run. Specifically call out:

- The idempotency test result — if it doesn't pass on the stub, the adapter is not safe to re-run.
- Whether the source has any update-cadence assumption that would conflict with the "re-run quarterly or on-demand" model. If a source publishes daily diffs the user will actually want to consume, that's a queue-revisit trigger and worth flagging.
- The end-of-run summary log line — confirm the user knows what counts they should see on a clean run vs. a re-run.

Surface any conventions you couldn't fully encode because the source's API shape is unusual.
