# Musarde — Project Brief

**Name:** Musarde — from the French *musarder*, "to dawdle pleasurably, to muse."
**Domain:** musarde.app
**Repo:** github.com/musarde/web

## What this is

A mobile-first web app that helps me get more out of museum visits. Two main surfaces:

1. **Pre-visit:** pick a museum (or aggregate current exhibitions in a city), get a curated route through the galleries with notes on which works to spend time on and why
2. **In-gallery:** photograph a work or scan a label → get deeper context, related works in the collection, links to similar works elsewhere

Launch coverage: Met + AIC + Getty as the open-data encyclopedic backbone, plus a manually-catalogued SAM substrate for local field testing.

## Why I'm building it — and what's gating

**Primary goal:** get a job by end of August 2026. Musarde is interview substrate and resume artifact in service of that goal, not the goal itself.

**The plan has two committed phases and one conditional phase:**

- **Weeks 1–6 (committed):** build to Week 6 with resume bullets ready to add. By Sunday Jun 14, ~5 in-progress bullets credible enough for the resume, plus interview-readiness audit complete (architecture defendable cold).
- **Weeks 7+ (conditional):** continued effort depends on job-search bandwidth. If interviews are moving and consuming calendar, scale back or pause Musarde. If the pipeline is quiet, continue per the original plan toward Phase 2/3 ship and the August NYC trip.

**The Week 6 milestone is the project's only hard commitment.** Everything past it is renegotiable based on what the job search actually needs.

Strong across all three resume variants:
- **ML/AI:** multimodal (vision + RAG + agent design), real eval work on a defensible domain
- **Full-Stack/Product:** deployed mobile-first PWA with real users (me)
- **Distributed Systems:** ingestion pipeline across heterogeneous museum sources spanning CSV, REST, Linked Open Data, and manually catalogued substrates

Secondary: I genuinely use this on weekends and on travel.

## Resume bullets I'm targeting

### v0.6 (in-progress versions, ready by Sunday Jun 14 / Week 6)

These are the bullets that go on the resume regardless of what happens after Week 6. They're written in present-continuous where work is ongoing; numbers are real-as-of-Week-6.

- **Building Musarde, a mobile-first museum companion app**; data integration layer for 680K+ artworks across The Met, Art Institute of Chicago, and the J. Paul Getty Museum, with pluggable adapter pattern spanning three structurally different source paradigms (CSV bulk dumps, live REST APIs, Linked Open Data via JSON-LD/SPARQL); idempotent upserts on natural keys, embedding model versioning, and re-runnable one-shot loader design driven by the slow-moving update cadence of museum collection data (months, not days).
- **Built mobile-first PWA with sub-3s end-to-end latency for ML-powered visual search of museum artworks**; SSE-streamed LLM responses for in-gallery context; presigned-URL direct-to-S3 uploads for reliable mobile photo ingestion under spotty WiFi conditions.
- **Built tool-using planning agent for museum visit routing using raw Claude function-calling API**; defined tool surface (collection search, metadata filter, time budgeting, artist context, related works), iterative replanning loop with max-step and timeout policies, and full agent-trace observability; chose raw API over framework to retain explicit control over loop semantics and termination conditions.
- **Designing multimodal retrieval eval set across phone photos at the Seattle Art Museum** (manually catalogued substrate of ~100 works with deliberate per-genre distribution); current top-5 retrieval accuracy at [X%] with CLIP + metadata-filter pipeline; methodology specifically designed to stress-test CLIP failure modes on contemporary, conceptual, and Indigenous art.
- **Built contemporary art reading companion with RAG over curated corpus of museum essays, artist interviews, and open criticism**; designed three-way comprehension-rubric eval (vanilla LLM baseline / single-shot RAG / one-round-iterative RAG) on held-out works; reader study with 5–10 participants planned.

Optional 6th bullet if Week 6 produces a real observability finding:
- **Instrumented ML inference stack with structured logging tracking p50/p95 latency, cost per query, model version, and quality regression signals**; built cost/latency dashboards revealing [specific finding] that informed [specific optimization].

### v1.0 (post-Week-6 upgrade, conditional on continued effort)

If Phases 2/3 continue, bullets upgrade to past-tense with shipped numbers, hybrid retrieval ablation results, and (if August trip happens) multi-museum eval data.

## My background context

- Senior SDE / Tech Lead, 12+ years at Amazon
- Strong on distributed systems, AWS, ML infrastructure (SageMaker, EMR/Spark)
- Less hands-on experience: vision models, modern Next.js / React 19, mobile PWA patterns, fine-tuning, agent design
- Comfortable with agent design conceptually; this is my first real agent-driven product

## Stack decisions

- **Frontend:** Next.js (App Router), Tailwind, deployed on Vercel as PWA
- **Database:** Postgres on Supabase or Neon, with pgvector for embeddings
- **Vision:** CLIP-family for image embeddings — OpenCLIP ViT-L/14 (LAION-2B) as default; SigLIP under consideration as a more deliberate pick (Week 1 decision). Bulk embedding runs locally or on Modal; Replicate reserved for incremental deltas only.
- **Text embeddings:** TBD pending Week 1 three-way bake-off (text-embedding-3-small, Voyage-3, candidate OSS option) on a small held-out retrieval set. The eval scaffolding doubles as substrate for the Week 5 reading-companion comprehension eval.
- **LLM API:** Claude for agent reasoning, annotation, and vision tasks. Single provider for v1; revisit only if a specific task surfaces a real performance gap.
- **Agent layer:** raw Claude function-calling API, NOT a framework. Decision logged Week 1.
- **Loader runtime:** on-demand re-runnable Python script. No cron, no queue. Collection data updates on the order of months, so quarterly hand-triggered re-runs are operationally honest. Decision logged Week 0.

Reuse same stack as the bilingual reader.

## Verified ingestion sources for v1

**Committed:**
- **The Met** (NYC) — CSV dump on GitHub at `metmuseum/openaccess`, ~470K works, CC0. Plus REST API for richer per-object data including images. *Capstone field-test target if August NYC trip happens.*
- **Art Institute of Chicago** (Chicago) — REST API at `api.artic.edu/api/v1/`, ~120K works, CC0, IIIF for images. Nightly JSON dumps on GitHub.
- **The J. Paul Getty Museum** (LA) — Linked Open Data via `data.getty.edu`, ~88K open-content images CC0. Linked Art format (JSON-LD/SPARQL). IIIF for images. The most architecturally novel integration.
- **Seattle Art Museum** — manually catalogued substrate of ~100 works captured during visits. OCR pipeline for label metadata + reference photos for embeddings. Used for local field-test iteration. Sidesteps both the technical bot-protection and legal questions of scraping.

**v1.5 expansion candidates (post-launch):** Cleveland, Brooklyn, LACMA, Whitney, MoMA, Rijksmuseum, Frye (with permission), expanded SAM coverage.

**Cut from v1:** Henry Art Gallery (relationship-based access only), SFMOMA (API offline), FAMSF (no public dump), Portland Art Museum / Vancouver Art Gallery (no public APIs).

## Scope — what's in v1

- Indexed collections: Met + AIC + Getty (~680K open-data works) + SAM (~100 manually catalogued)
- **Pre-visit route as a tool-using planning agent** (Week 2): tools for collection search, metadata filter, time budgeting, artist context lookup, related works. Multi-step planning loop, full agent-trace observability. Raw Claude function-calling API.
- Cross-city exhibition aggregation **primitive**: pluggable source adapters, taste-vector ranking. Single-city scope in v1; full multi-city agent in v1.5.
- In-gallery camera flow: photograph work → context + related works
- Mobile-first PWA with offline cache for the curated route
- **Contemporary art reading companion** (Week 5): plain-English explainer with RAG over curated corpus, light-iterative retrieval pattern, comprehension-rubric eval
- Just me + 2–3 friends as users

## Scope — explicitly out of v1

- True gallery wayfinding / floor plans (v2)
- Multilingual museum label translator (v2 / trip-driven)
- Cross-city exhibition agent with multi-source aggregation (v1.5)
- Scraping-based ingestion (deferred to v1.5)
- Public launch / user accounts at scale
- Native mobile app
- Fully agentic multi-hop retrieval for the reading companion

## Build plan

**Headline shape:** 6 weeks committed (Phases 1–2 partial, Weeks 1–6) ending in resume-bullets-ready and interview-readiness audit. Weeks 7+ conditional on job-search bandwidth.

### Week 1 — Data foundation: Met + AIC (May 4–10)
- Postgres + pgvector. Generic ingestion adapter pattern with `raw_metadata` JSONB escape hatch and separate `texts` table.
- Met CSV adapter (Day 1–2). AIC REST adapter (Day 3–4). Polish + full embeddings (Day 5–6).
- **Day 7:** decisions-log entry on raw tool-use API vs. framework. Sketch Week 2 tool surface on paper.

### Week 2 — Tool-using planning agent (May 11–17)
- Tools: `search_collection`, `filter_by_metadata`, `estimate_time_budget`, `lookup_artist_context`, `find_related_works`
- Loop: max 5–8 steps, hard timeout, full trace logging
- **Decisions-log entries (target 4–5):** tool surface granularity, termination policy, history management, failure handling, observability schema
- SF travel May 15–20: real Week 2 deadline is Thu May 14 EOD

### Week 3 — In-gallery PWA + first PWA field test (May 18–24)
- Mobile-first PWA, offline cache, "I'm here" view, streaming LLM responses
- Field test at Seattle museum using Met or AIC as test substrate (PWA UX doesn't need SAM ingestion)

### Week 4 — Vision feature + SAM manual catalog + first vision field test (May 25–31)
- Camera input → CLIP embedding → nearest-neighbor. Latency target <3s end-to-end.
- **SAM manual catalog protocol (build first, before the visit):** OCR-label-to-JSON pipeline, schema for SAM-manual records, eval-set capture protocol.
- **Field test (full Saturday at SAM):** catalogue ~100 works with deliberate distribution. Same visit captures 30–40 phone-photo eval queries.
- Phase 1 boundary review.

### Week 5 — Reading companion (Jun 1–7)
- RAG over curated corpus, light-iterative retrieval (single-shot + one conditional follow-up round)
- Three-way comprehension eval design: vanilla LLM no-RAG / single-shot RAG / iterative RAG, on held-out works

### Week 6 — Getty integration + minimal taste profile + interview-readiness checkpoint (Jun 8–14)
**The committed milestone.**

- **Day 1–3:** Getty Linked Open Data adapter. Parse JSON-LD documents, normalize Linked Art concepts. CLIP embeddings on ~88K open-content images.
- **Day 4:** Schema audit post-Getty.
- **Day 5:** Taste profile (minimal — bag-of-embeddings with mean aggregation, stub for v1.5 deepening).
- **Day 6–7:** **Interview-readiness audit.** Whiteboard architecture from memory. Defend top 5 architectural decisions in 2 min each. Confirm resume bullets are ready to add.

**Sunday Jun 14 check-in:** the **continue / scale-back / pause decision** for Musarde based on current job-search status. See accountability plan for the framework.

### Weeks 7+ — Conditional

**If continuing at full pace:**
- Week 7: Hybrid retrieval + second SAM field test
- Week 8: Phase 2 ship — polish, deploy, blog post, demo video, resume bullets v1.0
- Weeks 9–12: Phase 3 — A/B retrieval, hybrid retrieval deepening, continuous eval, observability
- Week 14 (early August): NYC capstone field test at the Met (~100 phone-photo eval queries, validate hybrid retrieval in the wild, bullet 3 upgraded to multi-museum framing)
- Weeks 15–16: Phase 4 wrap or interview-prep weeks

**If scaling back (a few hours per week, on-call mode):**
- Iterate locally on what shipped through Week 6
- Use Musarde as personal-use product on weekends
- Keep one interview-mock per week using the Week 6 substrate
- No new feature work; resume bullets stay at v0.6

**If pausing:**
- Week 6 bullets are on the resume regardless
- Interview substrate is the Week 6 audit material
- Project resumes when job search lands

## Post-v1 roadmap (whenever v1 ships)

**v1.5 (4–6 weeks, post-launch):**
- Cross-city exhibition agent with multi-source aggregation
- Source expansion via permission/scraping
- SAM manual catalog deepening

**v2 (trip-driven):**
- Multilingual label translator (Japanese/Korean) — when a Japan or Korea trip is on the calendar

## Known risks

- Week 1 ingestion always takes longer than expected. Schema decisions on day 1 ripple through.
- **Museum API status changes.** Verify each source before committing.
- **Week 2 agent loop has highest design risk.** Tool surface is most of the engineering.
- **Week 4 vision work has highest variance.** CLIP underperforms on conceptual work.
- **Week 4 SAM manual catalog is fatiguing.** Pre-build OCR pipeline before the visit.
- **Week 6 Getty Linked Open Data is the most architecturally novel adapter.** Budget 3 days; don't be surprised if it's 4.
- Week 5 reading companion eval is the resume-grade artifact and easy to do badly.
- **Job search vs. project-effort drift.** The biggest risk after Week 6 is that project work feels productive and crowds out interview prep, applications, and outreach. The accountability plan's mock-interview-cadence requirement exists specifically to prevent this.
- **Resume-driven over-engineering.** The symmetric failure mode to the one above: adding infrastructure (queues, schedulers, A/B harnesses, retry layers) because it sounds good on a resume rather than because the app demands it. Senior interviewers — Bar Raisers especially — ding over-engineering harder than under-engineering. The honest filter for any piece of infrastructure: name a concrete thing the app does this quarter that requires it. If the answer is "it would be impressive," cut it. Both this risk and the one above are the project warping around something other than the app's actual needs.
- **Week 6 over-investment risk.** Getting too attached to Phase 2 ship goals can produce slip into Week 7+ even when interviews are picking up. The continue/scale-back/pause decision at Week 6 must be honest, not aspirational.

## How I want Claude to help

- **Architecture decisions:** push back when my approach has issues
- **Vision/multimodal:** weakest area, be explanatory
- **Agent design:** also weak, push hard on tool surface and loop semantics
- **Linked Open Data parsing:** new for me, be explanatory
- **Eval design:** push hard on rigor and fairness
- **Code reviews:** senior pair-programming energy
- **Resume framing:** specific and credible, including in-progress framing
- **Verify museum API status before committing.** Don't trust training data.

## Build log convention

Date-stamped notes in `/build-log/YYYY-MM-DD.md`. Each entry: what I worked on, what worked, what broke / surprised me, open questions, tomorrow's first task. Longer entries after museum field tests.

## Cross-project note

Bilingual reader project is parallel work stream. Same stack. Reader's annotation infrastructure may plug into Musarde's v2 multilingual feature.

## Status

Named, scaffolded, ready to build. Domain registered, GitHub org created, Vercel project provisioned. Target start: Mon May 4 (Week 1). **Committed milestone:** Sunday Jun 14 (Week 6) — resume bullets ready, interview-readiness audit complete, continue/scale-back/pause decision made. Subsequent timeline is conditional on job-search status at that point.