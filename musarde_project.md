# Musarde — Project Brief

**Name:** Musarde — from the French *musarder*, "to dawdle pleasurably, to muse."
**Domain:** musarde.app
**Repo:** github.com/musarde/web

## What this is

A mobile-first web app that helps me get more out of museum visits. Two main surfaces:

1. **Pre-visit:** pick a museum (or aggregate current exhibitions in a city), get a curated route through the galleries with notes on which works to spend time on and why
2. **In-gallery:** photograph a work or scan a label → get deeper context, related works in the collection, links to similar works elsewhere

Launch coverage: clean-API museums as the indexed substrate (Met + AIC committed, third source TBD). Seattle and SF museums deferred to v1.5 once the core pipeline is proven. Multilingual and cross-city agent features deferred (see Post-v1 roadmap).

## Why I'm building it

Primary goal: enrich my resume during sabbatical. Strong across all three resume variants:
- **ML/AI:** multimodal (vision + RAG + agent design), real eval work on a defensible domain
- **Full-Stack/Product:** deployed mobile-first PWA with real users (me, on actual museum visits)
- **Distributed Systems:** ingestion pipeline across heterogeneous museum sources, embedding pipeline, hybrid retrieval

Secondary: I genuinely use this on weekends and on travel.

Resume bullets I'm targeting:
- Built Musarde, a mobile-first museum companion app indexing 600K+ works across Met, Art Institute of Chicago, and additional clean-API sources, with pluggable adapter architecture supporting CSV bulk dumps and live REST integrations
- Designed multimodal eval set of 200+ phone photos taken across 5+ museum visits; achieved [X%] top-5 retrieval accuracy with hybrid CLIP + text + LLM re-ranking pipeline
- Built contemporary art reading companion with comprehension-rubric eval, validated on 5–10 readers; outperforms vanilla LLM-no-RAG baseline by [X] points on held-out works

## My background context

- Senior SDE / Tech Lead, 12+ years at Amazon
- Strong on distributed systems, AWS, ML infrastructure (SageMaker, EMR/Spark)
- Less hands-on experience: vision models, modern Next.js / React 19, mobile PWA patterns, fine-tuning
- Comfortable with agent design conceptually; this is my first real agent-driven product

## Stack decisions

- **Frontend:** Next.js (App Router), Tailwind, deployed on Vercel as PWA
- **Database:** Postgres on Supabase or Neon, with pgvector for embeddings
- **Vision:** CLIP (OpenAI or open variants via Replicate) for image embeddings
- **Text embeddings:** text-embedding-3-small
- **LLM API:** Claude for agent reasoning and annotation; GPT-4o for vision tasks where needed
- **Cron:** Vercel cron or GitHub Actions for periodic ingestion refresh

Reuse same stack as the bilingual reader — keeps mental overhead low.

## Verified ingestion sources for v1

**Committed:**
- **The Met** — CSV dump on GitHub at `metmuseum/openaccess`, ~470K works, CC0, no auth, no rate limits. Plus REST API for richer per-object data including images. Cleanest integration in the museum world.
- **Art Institute of Chicago** — REST API at `api.artic.edu/api/v1/`, no auth required, ~120K works, CC0, IIIF for images. Also offers nightly JSON data dumps on GitHub at `art-institute-of-chicago/api-data`. Actively maintained.

**Third source candidates (decide week 1 after looking at one example record from each):**
- **Cleveland Museum of Art** — Open Access API + GitHub dump, ~60K works, CC0, IIIF images included. Cleanest "image-bearing third source" option.
- **Brooklyn Museum** — REST API, encyclopedic with serious contemporary holdings. Need to verify current state of API before committing.
- **Whitney Museum** — Live API + CSV dump, 17K+ works, 20th–21st c. American focus, CC0. **Caveat:** open-access dataset is metadata-only, no images. Best as a text-retrieval source for the reading companion, not a vision substrate.
- **MoMA** — CSV dump on GitHub (`MuseumofModernArt/collection`), ~140K works, CC0, metadata-only. Same image caveat as Whitney.
- **Rijksmuseum bulk download** — ~800K objects with high-res images, CC-BY. Note: legacy REST API is deprecated; new APIs use OAI-PMH and Linked Art (more complex). Bulk download is the simplest path if chosen.

Decision criterion: pick based on whether the third source is doing the "image-bearing diversity" job (Cleveland, Brooklyn, Rijksmuseum) or the "contemporary text-rich" job for the reading companion (Whitney, MoMA).

**Deferred to v1.5 (scraping pass, after core pipeline is proven):**
- **Frye Art Museum** — small custom-stack site, scrape feasible, ~700 works estimated. Local Seattle field-test substrate when added.
- **SAM (Seattle Art Museum)** — uses eMuseum platform; ~600 highlight works publicly exposed (not the full 25K — most of the collection is unpublished). Scrapeable but adds complexity; defer.

**Cut entirely:**
- **Henry Art Gallery** — would require relationship-based access (email outreach), not on critical path
- **SFMOMA** — public Collection API has been deprecated/offline for years despite docs claiming "temporarily unavailable"
- **FAMSF (de Young + Legion)** — no public bulk dump available; would require scraping with no compensating benefit over Met/AIC encyclopedic coverage

## Scope — what's in v1

- Indexed collections: Met + AIC + one additional source (TBD week 1)
- Pre-visit route: pick museum + interests → ranked list of works with notes
- Cross-city exhibition aggregation **primitive**: pluggable source adapters, taste-vector ranking. Single-city scope in v1; full multi-city agent comes in v1.5.
- In-gallery camera flow: photograph work → context + related works
- Mobile-first PWA with offline cache for the curated route
- **Contemporary art reading companion** (week 5, reframed from earlier "hybrid retrieval" plan): plain-English explainer for dense art writing, RAG over a curated corpus of exhibition essays + artist interviews + open criticism. Comprehension-rubric eval on self + 5–10 friends. Strict baseline: must beat vanilla LLM-no-RAG to justify the corpus.
- Just me + 2–3 friends as users

## Scope — explicitly out of v1

- True gallery wayfinding / floor plans (v2)
- Multilingual museum label translator (v2 / trip-driven, when a Japan or Korea trip is on the calendar)
- Cross-city exhibition agent with multi-source aggregation across galleries, fairs, Instagram (v1.5 / post-launch)
- Seattle museum integration via scraping (v1.5)
- Public launch / user accounts at scale
- Native mobile app

## 8-week build plan (10–12 weeks realistic alongside job applications)

### Week 1 — Data foundation
- Postgres + pgvector set up (Supabase or Neon)
- Generic ingestion adapter pattern with two key schema affordances:
  - `raw_metadata` JSONB column on objects table — full source-specific record stored verbatim. Escape hatch for fields not modeled in v1.
  - Separate `texts` table keyed by `(object_id, type, language, source)` for future multilingual / multi-text-type support
- **Day 1–2:** Met CSV adapter end-to-end (download, parse, normalize, store, generate CLIP embeddings for sample). First win banked.
- **Day 3–4:** AIC REST adapter, exercises pagination + REST shape. Confirms adapter pattern works across two integration shapes.
- **Day 5:** 60-minute exercise — pull one example record from each candidate third source (Cleveland, Brooklyn, Whitney, MoMA, Rijksmuseum). Use the field shapes to inform schema design before committing. Decide third source.
- **Day 6–7:** Implement third source adapter. Generate full embeddings.
- **Sanity check:** pick a Met work, find nearest neighbors across all three collections. Do they make art-historical sense?

### Week 2 — Pre-visit planning + cross-city primitive
- Standard flow: museum + interests → curated route
- Build the cross-city aggregation **primitive** with pluggable source adapters. Even though v1 only ranks across the museums in the indexed collection, design the abstraction so the v1.5 agent expansion drops in cleanly.
- First agent: reason about user interests + collection metadata + time budget

### Week 3 — In-gallery experience + first field test
- Mobile-first PWA, offline cache for curated route
- "I'm here" view: next stop, current work, notes, related works
- Streaming LLM responses (latency matters in galleries)
- **Field test:** when in-gallery flow works, take it to whichever museum is convenient (likely opportunistic during travel given v1 has no Seattle museums). Notebook for failures. Triage and fix top 3 next morning.

### Week 4 — Vision feature + extended field test
- Camera input → CLIP embedding → nearest-neighbor in indexed collection
- Fallback for works not in index
- Latency target: <3 seconds end-to-end
- **Field test:** photograph 30–40 works at a museum where coverage exists. This is the eval set. Without Seattle museums in v1, this likely happens during a trip.

### Week 5 — Contemporary art reading companion
**Reframed from "hybrid retrieval for contemporary works" — same underlying retrieval engineering, much sharper resume artifact.**
- Build a plain-English explainer for dense art writing (artist statements, exhibition essays, press releases). Outputs: explanation of what the work/show is about, art-historical references, similar artists/movements, questions to ask yourself when looking.
- RAG over a curated corpus of exhibition essays. Clean sources only: museum-published essays, Art21 transcripts, BOMB and BrooklynRail interviews, artist gallery-page writing. Skip paywalled and ToS-restricted sources (Artforum, Frieze, e-flux).
- **Eval is the senior-grade artifact.** Comprehension test format: read explanation → answer 3 questions about the work → score. Held-out works whose criticism is NOT in the corpus, to measure generalization rather than memorization. Baseline: vanilla LLM with the artwork image and no RAG. If RAG'd version doesn't beat baseline, the corpus isn't earning its keep.

### Week 6 — Personalization + taste profile
*(Multilingual moved to v2.)*
- Taste profile from saved/liked works: bag-of-CLIP-embeddings + bag-of-text-embeddings of artist statements engaged with
- Cross-museum recommendations within indexed collections
- Design taste-profile object deliberately — it's shared infrastructure for the v1.5 cross-city agent

### Week 7 — Iteration on hardest cases
- Test edge cases surfaced by week 4 vision field test, particularly contemporary works
- Hybrid retrieval improvements: CLIP + text retrieval over wall text/essays + LLM re-ranking
- Eval: hybrid vs. CLIP-only on contemporary subset
- Where senior-grade engineering shows up — naïve approach works on a Vermeer, fails on a Trisha Donnelly

### Week 8 — Polish, deploy, write up
- UI pass (designer friend if available)
- Performance: lighthouse scores, image lazy loading, embedding caching
- Public blog post: architecture + one specific hard problem solved. Recommend writing about either the multimodal eval or the reading companion's comprehension-rubric eval — both are distinctive.
- Demo video shot during an actual museum visit
- Resume bullets finalized

## Post-v1 roadmap

**v1.5 (4–6 weeks, post-launch):**
- **Cross-city exhibition agent** with multi-source aggregation: museum APIs + gallery sites (ArtRabbit, See Saw) + e-flux announcements. Real itinerary planner with scheduling, opening-hours awareness, walking distances. Maps to 2026 hiring on agentic systems.
- **Seattle museum integration** via scraping: Frye (small, low-risk), SAM eMuseum (~600 highlights, predictable patterns). Build politeness primitives, robots.txt compliance, JSON-LD-first parsing, response caching. Local field-test substrate.

**v2 (trip-driven):**
- **Multilingual label translator** (Japanese/Korean) — focused 2–3 week sub-project when a Japan or Korea trip is on the calendar. OCR (vertical Japanese is non-trivial), vision-style recognition, RAG over Japanese/Korean art history. Don't build until there's a real trip and a real test set.

## Known risks

- Week 1 ingestion always takes longer than expected, even with clean APIs. Schema decisions on day 1 ripple through the rest of the project. The `raw_metadata` JSONB escape hatch is the most important affordance — it means "I designed for the wrong fields" is always a SQL migration away, not a re-ingest.
- **Museum API status changes faster than expected.** SFMOMA went offline; Rijksmuseum's legacy API was deprecated; SAM has no API; FAMSF has no public dump. Verify each candidate source is actually accessible before committing to it. Don't build on assumed-working integrations.
- Week 4 vision work has highest variance. CLIP underperforms on conceptual / installation work. Plan 1–2 days of experimentation before committing to architecture.
- Week 5 reading companion's eval is the resume-grade artifact and easy to do badly. Baseline comparison with vanilla LLM is non-negotiable. Held-out works are non-negotiable.
- Field testing pushed out: with no Seattle museums in v1, opportunistic field tests during travel become the primary feedback loop. Plan trips accordingly or accept the trade.

## How I want Claude to help

- **Architecture decisions:** before I commit to data model, retrieval architecture, agent structure, etc., help me think through alternatives. Push back when my approach has issues.
- **Vision/multimodal:** this is my weakest area. Be more explanatory here than elsewhere. Flag when there's a standard practice I'm missing.
- **Scraping/ingestion strategy:** help me think through ethical and rate-limit considerations for each museum source.
- **Eval design:** the multimodal eval and the reading companion's comprehension eval are the senior-grade artifacts. Push hard on whether evals are rigorous and fair.
- **Code reviews:** senior pair-programming energy, not basics.
- **Resume framing:** help me write bullets that are specific and credible.
- **Verify museum API status before committing.** Don't trust your training data on which APIs exist; the landscape shifts.

## Build log convention

Date-stamped notes per work session in `/build-log/YYYY-MM-DD.md`. Each entry:
- What I worked on
- What worked
- What broke / surprised me
- Open questions
- Tomorrow's first task

After each museum field test, longer entry with photo log, failure cases, and triage.

## Cross-project note

Bilingual reader project is the parallel work stream. Same tech stack. The reader's annotation infrastructure may plug into Musarde's v2 multilingual feature when that comes. Don't merge codebases; do reuse mental models.

## Status

Named, scaffolded, ready to build. Domain registered (musarde.app), GitHub org created (github.com/musarde), Vercel project provisioned. Target start: Mon May 4 (Week 1). Target ship: 8 weeks focused, 10–12 weeks realistic with job search overhead.