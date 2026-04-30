# Accountability Plan

Cadence and self-review structure for the 14–16 week phased build of Musarde. **Now layered with explicit interview-prep deliverables (Option A from the system-design pivot).** The project still proceeds toward the resume-artifact and personal-use goals, but interview readiness is a parallel first-class track, not an afterthought.

Lives at the repo root so it stays in view; revisit at each Sunday check-in.

## Goal stack (in priority order, since they sometimes pull against each other)

1. **Build interview substrate.** Real architectural decisions made and defensible. By week 6, can whiteboard the system from memory and walk through trade-offs cold.
2. **Ship resume artifact.** Phase boundaries are independent shipping points. By week 6, at least two strong resume bullets are immediately addable.
3. **Build the personal-use product.** I want to use this on weekends and on travel.

When 1 and 2 conflict (e.g., a feature is great for the product but architecturally uninteresting), 1 wins. When 2 and 3 conflict (a feature is great for me personally but doesn't strengthen the resume), pick deliberately rather than drifting.

## Target dates

- **Week 0 (setup):** Wed Apr 29 – Sun May 3
- **Week 1 starts:** Mon May 4
- **Phase 1 ends (foundation):** Sun May 31
- **Week 6 interview-readiness checkpoint:** Sun Jun 14
- **Phase 2 ends (multimodal eval shipped):** Sun Jun 28
- **Phase 3 ends (senior ML-systems story):** Sun Jul 26
- **Phase 4 ends (cross-city agent, optional):** Sun Aug 23
- **Decision points:**
  - Week 4 Sunday (May 31): is interview-prep ROI still high? (See "Continue/stop decision" below.)
  - Week 6 Sunday (Jun 14): interview-readiness checkpoint. Can I defend this project cold in an interview?
  - Week 12 Sunday (Jul 26): is phase 4 worth the calendar time, or is it diminishing returns vs. interview reps?

## Travel calendar

### May 15–20 (Fri–Wed): San Francisco — BTS concert

Spans end of Week 2 and start of Week 3 (Phase 1, weeks 1–4). Realistic availability: ~8–12 work hours across the 6 days vs. ~30 in a normal week. Net loss: roughly 3–4 working days, ~half a week.

**Effect on Phase 1 timeline:** Phase 1 ends nominally Sun May 31. With the SF trip eating most of week 3, Phase 1's polish gets compressed into week 4. Phase 1 remains achievable but tight.

**Effect on Week 2 deadline:** treat **Thu May 14 EOD** as the real Week 2 deadline. Whatever isn't done by then is Week 3 work.

**Effect on the Sunday May 17 check-in:** do it **Thu May 14 evening** instead. Set Week 3's primary deliverable before flying, not after landing.

**Effect on Week 3:** effectively starts Wed May 21. The Week 3 deliverable (mobile PWA in-gallery flow) likely slides into the start of week 4.

### Decision point — Wed May 13 (Week 2 mid-week pulse)

**Updated framing:** Earlier version of this plan considered SF museums as a possible field-test opportunity. With the project rescoped to clean-integration museums only (Met + AIC + 3rd source), SF museums are NOT in the index. A field test in SF would only test cross-collection nearest-neighbor on works that happen to have stylistic matches in indexed collections — interesting but not central.

**Revised decision at May 13:** Is the in-gallery PWA testable by Thu May 14? If yes and time permits, do an opportunistic walk-through at SFMOMA or de Young — partial coverage is fine for a smoke test. If no, let the trip be the trip. **The field test that matters happens in week 4 or week 7 at a museum where coverage is real.**

## Daily rhythm

- **Morning (~4–5 focused hours):** project work. End each session with build-log entry including "tomorrow's first task."
- **Afternoon split:** job applications + interview prep. Interview prep is no longer the residual; it's explicit calendar time.
- **End of project session:** 15-minute decisions-log update. Even on days with no new architectural choice, write "no new decisions today" — that itself is data.

### Interview-prep weekly minimums (non-skippable)

These are floor commitments, not nice-to-haves. If a week skips any of them, the Sunday check-in flags it.

- **One mock interview per week.** Either with a friend role-playing, paid mock (Hello Interview, interviewing.io), or self-recorded with the project as substrate ("Tell me about a system you've built recently"). The point is real-time articulation under pressure.
- **One architecture-whiteboard practice per week.** Stand at a whiteboard or tablet, draw the current state of the system from memory in 10 minutes, talk through it out loud as if to an interviewer. Notice what you can't draw cleanly — that's what to think about this week.
- **One hellointerview deep-dive per week.** Pick a key technology you've integrated this week (Redis, SSE, S3, pgvector) and read the corresponding hellointerview deep-dive. Goal: vocabulary alignment with what interviewers expect.

### No mid-task context switching

If a tricky bug runs past lunch, finish the bug; push job apps to evening. If that pattern repeats more than twice in a week, accept that the 14–16 week timeline skews longer.

## Decisions log — tracked artifact

A running document at `/build-log/decisions.md`. Every real architectural choice gets an entry. Format:

```
## YYYY-MM-DD: [Decision title]

**Context:** What problem was I solving?
**Considered:** Alternative A, alternative B, alternative C.
**Picked:** X
**Why:** [The case for X over the alternatives, including trade-offs.]
**Would revisit if:** [What would change my mind.]
**Interview talking-point version:** [The 30-second version of this story.]
```

Every Sunday check-in asks: "What got added to the decisions log this week?" If a week generates zero decisions-log entries, it's a weak interview-prep week even if a lot of code was written.

Already-anticipated entries from the project brief (start the log with these on day 1, fill in details as you build):
- Postgres + pgvector over DynamoDB + dedicated vector DB
- Postgres SKIP LOCKED queue over Redis Streams or SQS
- In-process LRU cache over Redis for single-instance deploy
- SSE over WebSockets for streaming LLM responses
- Postgres FTS over Elasticsearch for the corpus size
- S3 + presigned URLs over API-server-mediated uploads
- Redis for rate limiting only (deliberately scoped use)
- CLIP + text-embedding-3 architecture choice
- Hybrid retrieval pipeline shape (filter → vector → rerank)

## Mid-week pulse — Wednesdays, 5 minutes

Two questions:

1. *Am I going to hit this week's primary deliverable by Sunday?* If no, decide Wednesday whether to cut scope or extend timeline. Letting a slip drift to Sunday costs the whole week.
2. *Am I going to hit this week's interview-prep minimums?* (Mock interview, whiteboard practice, deep-dive read.) If no, schedule them now.

## Sunday check-in — ~45 minutes (longer than before)

Use the updated template at `build-log/sunday-checkin-template.md`. Save as `build-log/sunday-YYYY-MM-DD.md`.

Time has grown because interview-readiness questions are added. The structure now spans both project progress and interview-prep progress.

## Critical-week flags

Extra time budgeted at these Sunday check-ins. Don't skip the audits.

### Week 1 (Sun May 10) — Schema review

The `raw_metadata` JSONB escape hatch protects against wrong field choices, but the `texts` table shape is harder to migrate later. Spend 60 minutes asking: *would I regret this schema in Week 5 when the reading companion corpus arrives, or in Week 10 when hybrid retrieval lands?* Adjust now, not then.

### Week 4 (Sun May 31) — Phase 1 boundary + continue/stop decision

Two audits:
- **Vision performance audit.** After the field-test eval set is captured, measure top-5 retrieval accuracy honestly. If it's below ~60%, plan Week 7 hybrid retrieval work aggressively.
- **Continue/stop decision.** This is the first real "is interview prep still earning ROI?" check. By end of week 4, I should have two strong resume bullets ready. If I do, and the marginal week-5 work is still architecturally rich (Redis, observability, reading companion), continue. If the next phase is mostly polish, that's a signal interview-prep value is plateauing.

### Week 6 (Sun Jun 14) — Interview-readiness checkpoint

**This is the new most-important checkpoint in the plan.** The whole point of the project-as-interview-prep approach is that by week 6 I should be ready to walk into a system-design interview cold and use this project as the substrate. Audit:

- Can I whiteboard the full architecture from memory in 10 minutes?
- Can I name the top 5 architectural decisions and defend each in 2 minutes?
- For each connected technology (Postgres, pgvector, S3, presigned URLs, SSE, Redis, in-process LRU), can I state the business requirement and why I picked this tool over alternatives?
- What did mock interviews surface that I still can't answer well? Block time week 7 to fix the worst gaps.
- **Are at least two of the resume bullets below ready to add to the resume today?** (See "Resume-bullet readiness by week 6" below.)

If the answers are mostly no, week 7 is for catching up on interview-prep, not pushing forward on features.

### Week 5 or 6 — deliberate stress test

One of these weeks, plan a "break something" exercise that forces a real redesign. Candidates:
- Run embedding pipeline against a corrupted-image batch — what's the failure mode? How does idempotency hold up?
- Load-test pgvector at 10x current data size with synthetic vectors — where does latency degrade?
- Simulate Vercel function timeout mid-LLM-stream — does SSE recover gracefully?
- Run the ingestion adapter against a deliberately malformed source record — does the JSONB escape hatch save you?

Pick one. Document the failure, the diagnosis, and the fix. **This becomes one of the strongest interview stories in the project**, because synthetic stress tests with real diagnoses are rare in personal projects.

### Week 12 (Sun Jul 26) — Phase 3 boundary + scope question

By here, the senior ML-systems story is complete. Honest assessment: is phase 4 (cross-city agent) earning more ROI than the same time spent on intensive interview reps with the existing project as substrate? Either is defensible. Decide consciously.

## Resume-bullet readiness by week 6

The point of layering interview prep with the build is that real bullets are ready early, even if more bullets ship later. By end of Week 6, these should be on the resume:

### Bullet 1 — Distributed ingestion pipeline (ready end of week 4)

> Built distributed ingestion pipeline processing 600K+ artworks across The Met, Art Institute of Chicago, and [3rd source] with batched ML inference (CLIP image embeddings + text-embedding-3), fault-tolerant Postgres-backed job queue using SKIP LOCKED with retry/DLQ semantics, idempotency, and embedding model versioning supporting zero-downtime model swaps.

Data needed by Week 6: actual artwork count ingested, actual ingestion runtime, actual retry/failure counts.

### Bullet 2 — Mobile PWA + ML-powered visual search (ready end of week 4)

> Built mobile-first PWA with sub-3s end-to-end latency for ML-powered visual search of museum artworks; SSE-streamed LLM responses for in-gallery context; presigned-URL direct-to-S3 uploads with multipart resumable uploads for reliable mobile photo ingestion under spotty WiFi conditions.

Data needed by Week 6: measured p50/p95 end-to-end latency, working demo (video or live).

### Bullet 3 — Multimodal eval design (data ready by Week 6 from Week 4 + Week 7 field tests)

> Designed multimodal retrieval eval across [N] phone photos taken at [M] museum visits; measured top-5 retrieval accuracy at [X]% with CLIP + metadata-filter pipeline; held-out test set covers [Y] artists not in the indexed metadata.

Data needed by Week 6: at least 30–50 photos from a real field test. The full 200+ photo eval set lands later, but a credible bullet exists with smaller N.

### Bullet 4 — ML observability stack (ready end of week 6)

> Instrumented ML inference stack with structured logging tracking p50/p95 latency, cost per query, model version, and quality regression signals across [N] queries during development; built cost/latency dashboards revealing [specific finding, e.g., "30% of LLM cost was on the explainer path"] that informed [specific optimization].

Data needed by Week 6: real measurements, at least one specific finding from the dashboards.

### What's NOT ready by Week 6 (and that's OK)

- A/B retrieval infrastructure (Week 9)
- Hybrid retrieval (vector + lexical + rerank) (Week 10)
- Continuous eval harness (Week 11)
- Reading companion comprehension eval results (Week 6 designs the eval; results need readers and time)
- Cross-city agent / PostGIS (Phase 4)
- CDN edge cache layer (Week 9)

These are Phase 2/3/4 bullets. Don't try to claim them at Week 6.

## Mock interview cadence

Weekly, non-skippable. Use the project as substrate.

**Format options (rotate):**
- "Tell me about a system you've built recently and walk me through the architecture." (Most common opener; this is the one to nail.)
- "Design a system to do [X]" where X is intentionally similar to but not identical to the project (e.g., "design a similar-image search for an e-commerce site"). Forces you to abstract from the specific to the general.
- "Walk me through how you'd scale your project to 10M users." Tests scale-thinking and the "what I'd reach for at scale" answers from the decisions log.

**After each mock, log in `build-log/mock-interview-YYYY-MM-DD.md`:**
- Who interviewed (or that it was self-recorded)
- The question/prompt
- What I answered well
- What I fumbled or couldn't answer
- The thing to think about this week to fix the gap

**Triage:** if the same gap shows up two mocks in a row, that's a Sunday-check-in flag — block project time to address it.

## Resume-bullet data tracking

Every Sunday, ask whether this week generated data that fills the placeholders in the target bullets. If a week generates none, ask why.

| Bullet | Data needed | Generated by |
|---|---|---|
| 1 — Ingestion pipeline (600K+ works) | Ingestion counts, adapter coverage, retry/DLQ event counts | Phase 1 (weeks 1–4) |
| 2 — Mobile PWA / vision feature | p50/p95 latency measurements, working demo | Weeks 3–4 |
| 3 — Multimodal eval | Field-test photo log + annotated eval results | Week 4 first field test, Week 7 extended |
| 4 — ML observability | Real query volume in logs, cost/latency dashboards, specific findings | Weeks 5–6 |
| 5 — Hybrid retrieval (later bullet) | Hybrid vs. vector-only eval comparison | Week 10 |
| 6 — A/B retrieval infra (later bullet) | Strategies tested, regression catches | Weeks 9–11 |
| 7 — Reading companion (later bullet) | Comprehension scores from 5–10 readers on held-out works | Week 6 design, Week 11+ results |

Track museum visits as a first-class metric in each Sunday check-in. Target: 3+ visits by Week 6, 5+ by Week 12.

## Known risks (review at each Sunday check-in)

- Week 1 ingestion always takes longer than expected.
- Museum API status changes faster than expected — verify before committing.
- Week 4 vision work has highest variance.
- Week 5+ reading companion eval is easy to do badly — baseline + held-out works are non-negotiable.
- Field testing depends on travel calendar.
- **Operational complexity grows over phases.** Phase 1 has one stateful service. Phase 3 has Postgres + Redis + S3 + CDN. Watch for ops thrash.
- **(New) Interview-prep avoidance via project work.** Building feels productive; mock interviews feel uncomfortable. The plan is failing if mock interviews keep getting skipped while project work fills the time.

## When the plan is failing

Signals to stop and re-plan rather than push harder:
- Two consecutive Sundays of "partial" or "missed" on the primary deliverable.
- A week that generated zero decisions-log entries when it should have.
- A week that skipped the mock interview for any reason other than illness or the SF trip.
- Job applications stalling because project bleeds into afternoons more than twice a week.
- Same gap surfaces in two consecutive mock interviews without focused work to address it.
- A risk on the list above has materialized and not been re-planned around.

## Cross-reference

Project brief at root: master plan for what's being built.
This file: how I keep myself accountable to building it.
`build-log/decisions.md`: running architectural decisions log (interview substrate).
`build-log/sunday-YYYY-MM-DD.md`: weekly check-ins.
`build-log/mock-interview-YYYY-MM-DD.md`: mock interview reflections.
`build-log/YYYY-MM-DD.md`: daily build log entries.