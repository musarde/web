# Accountability Plan

Cadence and self-review structure for the Musarde build, with the priority frame **layered explicitly: job by end of August 2026 is the primary goal; Musarde is interview substrate and resume artifact in service of that goal.** The plan has two committed phases and one conditional phase.

Lives at the repo root so it stays in view; revisit at each Sunday check-in.

## Goal stack (priority order, since they pull against each other)

1. **Get a job by end of August 2026.** Interview prep, applications, outreach, mock interviews. This wins every conflict.
2. **Build interview substrate by Week 6 (Sunday Jun 14).** Real architectural decisions made and defensible. Resume bullets ready to add. By Week 6, can whiteboard the system from memory and walk through trade-offs cold.
3. **Ship resume artifact through Phase 2/3 (conditional).** Continue toward Week 8 ship and August NYC trip *if* job-search bandwidth allows. Otherwise scale back or pause.
4. **Build the personal-use product.** I want to use this on weekends and on travel.

When 1 and 2 conflict (a project hour vs. an application hour), 1 wins. When 2 and 3 conflict at Week 6, 2 already won — the bullets are on the resume regardless. When 3 and 4 conflict, pick deliberately rather than drifting.

## Target dates

- **Week 0 (setup):** Wed Apr 29 – Sun May 3
- **Week 1 starts:** Mon May 4
- **Phase 1 ends (foundation):** Sun May 31
- **🔑 Week 6 ship-or-pause checkpoint:** Sun Jun 14 — **the only hard milestone.**
- **Conditional Phase 2 ends:** Sun Jun 28 (Week 8)
- **Conditional Phase 3 ends:** Sun Jul 26 (Week 12)
- **Conditional NYC capstone:** Aug 3–9 (Week 14) or Aug 10–16 (Week 15)
- **Conditional Phase 4 ends:** Sun Aug 23 (Week 16)

## Travel calendar

### May 15–20 (Fri–Wed): San Francisco — BTS concert

Spans end of Week 2 / start of Week 3. ~8–12 work hours across 6 days vs. ~30 in a normal week. Net loss: ~3–4 working days.

**Effect on Phase 1 timeline:** Phase 1 ends Sun May 31. With SF eating most of week 3, polish compresses into week 4. Tight but achievable.

**Effect on Week 2 deadline:** Thu May 14 EOD is the real Week 2 deadline. Sunday May 17 check-in moves to Thu May 14 evening.

### August 3–9 or Aug 10–16: NYC capstone trip (conditional)

**Only happens if Week 6 ship-or-pause decision is "continue."** If continuing, book by mid-July (Week 11) for reasonable flight prices. If scaling back or pausing, the trip becomes either a personal vacation that opportunistically captures eval data, or doesn't happen as project work at all.

## Daily rhythm

- **Morning (~4–5 focused hours):** project work through Week 6. After Week 6, allocation depends on the ship-or-pause decision.
- **Afternoon split:** job applications + interview prep. After Week 6, this is likely the larger share.
- **End of project session:** 15-minute decisions-log update.

### Interview-prep weekly minimums (non-skippable, every week including post-Week-6)

These are floor commitments. If a week skips any, the Sunday check-in flags it.

- **One mock interview per week.** Friend, paid (Hello Interview, interviewing.io), or self-recorded with the project as substrate.
- **One architecture-whiteboard practice per week.** Draw current system state from memory in 10 min, talk through it out loud.
- **One hellointerview deep-dive per week.** Pick a key technology integrated this week.

After Week 6, these minimums *increase* if the ship-or-pause decision was scale-back or pause. The point of the framework is more interview prep, not less, when project bandwidth shrinks.

### No mid-task context switching

If a tricky bug runs past lunch, finish the bug; push job apps to evening. If that pattern repeats more than twice in a week, accept the timeline skews longer.

## Decisions log — tracked artifact

A running document at `/build-log/decisions.md`. Every architectural choice gets an entry:

```
## YYYY-MM-DD: [Decision title]

**Context:** What problem was I solving?
**Considered:** Alternatives.
**Picked:** X
**Why:** [Trade-offs.]
**Would revisit if:** [What changes my mind.]
**Interview talking-point version:** [30-second version.]
```

Every Sunday: "What got added to the decisions log this week?" Zero entries is a flag.

Already logged (Week 0):
- One-shot loader over queue infrastructure
- Decision filter: workload over resume

Anticipated future entries:
- Postgres + pgvector over DynamoDB + dedicated vector DB
- In-process LRU cache over Redis for single-instance deploy
- SSE over WebSockets for streaming LLM responses
- Postgres FTS over Elasticsearch
- S3 + presigned URLs over API-server-mediated uploads
- Raw Claude tool-use API over LangGraph or similar agent framework (Week 1)
- Text embedding model bake-off result (Week 1)
- CLIP variant choice — OpenCLIP vs SigLIP (Week 1)
- Hybrid retrieval pipeline shape (Week 7 if continuing)
- Linked Open Data parsing approach — full JSON-LD library vs. nested-JSON (Week 6)

## Mid-week pulse — Wednesdays, 5 minutes

1. *Am I going to hit this week's primary deliverable by Sunday?* If no, decide Wednesday whether to cut scope or extend timeline.
2. *Am I going to hit this week's interview-prep minimums?* If no, schedule them now.
3. *Are job applications stalling because project work is bleeding into afternoons?* If yes for two consecutive weeks, the priority stack is failing — re-plan.

## Sunday check-in — ~45 minutes

Use template at `build-log/sunday-checkin-template.md`. Save as `build-log/sunday-YYYY-MM-DD.md`.

## Critical-week flags

### Week 1 (Sun May 10) — Schema review

The `raw_metadata` JSONB escape hatch protects against wrong field choices, but the `texts` table shape is harder to migrate later. Spend 60 minutes asking: *would I regret this schema in Week 5 reading-companion or Week 6 Getty integration?* Adjust now.

### Week 4 (Sun May 31) — Phase 1 boundary

Two audits:
- **Vision performance audit.** After SAM eval set is captured, measure top-5 honestly.
- **Mid-cycle check.** Is the project on track to have ready bullets by Week 6? If not, what scope must be cut?

### 🔑 Week 6 (Sun Jun 14) — Ship-or-pause checkpoint

**The single most important milestone in the plan.** This decision is binding for at least the next 2 weeks.

**Project-side audit:**
- Can I whiteboard the full architecture from memory in 10 minutes?
- Top 5 architectural decisions defended in 2 min each?
- Each integrated technology — business requirement and tool rationale?
- **Are at least 5 resume bullets ready to add to the resume today?** (See "Resume-bullet readiness" below.)
- What did mock interviews surface that I still can't answer well?

**Job-search-side audit:**
- Job applications submitted in the past 2 weeks: count.
- Phone screens scheduled: count.
- Onsite interviews scheduled or recently completed: count.
- Pipeline trend: building, flat, or stalling?

**The ship-or-pause framework:**

**CONTINUE at full pace** if:
- Pipeline is flat or quiet (few interviews scheduled)
- Phase 2 work (Week 7 hybrid retrieval, Week 8 ship) would meaningfully strengthen interview substrate
- August NYC trip is realistically book-able and would produce useful eval data
- I have genuine capacity for ~25 project hours/week without crowding job-search effort

**SCALE BACK to on-call mode (5–8 hours/week)** if:
- Pipeline is moderate (interviews scheduled, applications converting)
- The marginal week of project work is incremental, not transformative
- Job-search effort needs more bandwidth but doesn't need 100% of it
- I want to keep using the app as a personal product without expanding it

**PAUSE entirely** if:
- Pipeline is hot (multiple onsites in flight, offers expected)
- Interview prep needs the morning blocks too
- Resume bullets at v0.6 are doing the job they need to do

The decision must be honest. Project work feels productive; job-search work feels uncomfortable. The discomfort is the point. If it's hard to choose pause or scale-back when the data says I should, that itself is a flag.

### Week 5 or 6 — deliberate stress test (if continuing)

One of these weeks, if continuing, plan a "break something" exercise:
- Run embedding pipeline against corrupted-image batch
- Load-test pgvector at 10x with synthetic vectors
- Simulate Vercel function timeout mid-LLM-stream
- Run ingestion adapter against malformed source record

Pick one. Document failure, diagnosis, fix. **Becomes one of the strongest interview stories in the project.**

### Week 12 (Sun Jul 26) — Phase 3 boundary + Phase 4 decision (only if continuing)

By here, the senior ML-systems story is complete (if Phase 3 happened). Honest assessment: is Phase 4 (cross-city agent) earning more ROI than the same time on intensive interview reps? Either is defensible.

## Resume-bullet readiness

By Sunday Jun 14 (Week 6), these bullets should be on the resume regardless of what comes next.

### v0.6 set (the Week 6 commitment)

| Bullet | Status | Data needed by Week 6 |
|---|---|---|
| 1 — Ingestion pipeline (~680K works across CSV, REST, Linked Open Data) | Built end of Week 6 | Actual ingested counts, runtime, retry/failure counts |
| 2 — Mobile PWA + ML-powered visual search | Built end of Week 4 | Measured p50/p95 latency, working demo |
| 3 — Multimodal eval at SAM (in-progress framing) | Designed end of Week 4, refined Week 6 | Real top-5 accuracy from ~40 SAM photos, breakdown by genre |
| 4 — ML observability *(optional bullet)* | Conditional on Week 6 dashboard producing real finding | One specific finding worth quoting |
| 5 — Tool-using planning agent | Built end of Week 2, refined through Week 6 | Tool surface, loop semantics, observability schema documented |
| 6 — Reading companion + comprehension eval (in-progress framing) | Designed end of Week 5, reader study planned | Eval methodology, baseline comparison, planned reader study |

### v1.0 set (post-Week 6, only if continuing)

These are upgrades, not Week 6 requirements:
- Bullet 3 absorbs hybrid retrieval results (Week 7) and potentially Met data (Week 14)
- New bullet for hybrid retrieval ablation (Week 7)
- New bullet for A/B retrieval infrastructure (Week 9)
- New bullet for continuous eval harness (Week 11)

### Honesty test for in-progress bullets

For each Week 6 bullet ask:
- Is every number in this bullet a real measurement I made?
- Is every system in this bullet actually built and runnable?
- Could I demo the system in front of an interviewer right now?
- Am I using "Building" / "Designing" honestly, or as a hedge for "barely started"?

If any answer is no, the bullet isn't ready. Cut or downgrade.

Museum visits this week: **N**. Running total: **N**. (Target: 2+ by Week 6 — first SAM visit in Week 4 plus possibly second in Week 7 if continuing.)

## Mock interview cadence

Weekly, non-skippable. Project as substrate.

**Format options (rotate):**
- "Tell me about a system you've built recently and walk me through the architecture." (Most common opener; nail this.)
- "Design a system to do [X]" where X is similar but not identical (e.g., "design similar-image search for an e-commerce site").
- "Walk me through how you'd scale your project to 10M users."

**After each mock, log in `build-log/mock-interview-YYYY-MM-DD.md`:**
- Who interviewed (or self-recorded)
- The question/prompt
- What I answered well
- What I fumbled or couldn't answer
- The thing to think about this week to fix the gap

If the same gap shows up two mocks in a row → Sunday-check-in flag → block project time to address it.

## Known risks

- Week 1 ingestion always takes longer than expected.
- Museum API status changes faster than expected.
- Week 4 vision work has highest variance.
- Week 5+ reading companion eval is easy to do badly.
- Week 6 Getty Linked Open Data integration is the most architecturally novel adapter.
- **Operational complexity grows over phases** (if continuing past Week 6).
- **Interview-prep avoidance via project work.** Building feels productive; mock interviews feel uncomfortable. The plan is failing if mocks keep getting skipped while project time fills.
- **Resume-driven over-engineering.** The symmetric failure mode to the one above: adding infrastructure (queues, schedulers, A/B harnesses, retry layers) because it sounds good on a resume rather than because the app demands it. Filter: name a concrete thing the app does this quarter that requires this piece of infrastructure. If the answer is "it would be impressive," cut it. Both risks are the project warping around something other than the app's actual workload.
- **Week 6 over-investment.** Getting attached to Phase 2 ship goals can cause slip into Week 7+ even when the honest call is scale-back or pause. The ship-or-pause decision must reflect job-search reality, not aspiration.
- **Long-timeline drift if continuing.** By Week 14 you'd be 3.5 months in. Risk: momentum decay through Phase 3 makes the trip a "demo what's done" event rather than a real test.

## When the plan is failing

Signals to stop and re-plan rather than push harder:
- Two consecutive Sundays of "partial" or "missed" on the primary deliverable
- A week with zero decisions-log entries when there should have been some
- A week that skipped the mock interview for any reason other than illness or pre-scheduled travel
- Job applications stalling because project bleeds into afternoons more than twice a week
- Same gap surfaces in two consecutive mock interviews without focused work
- Week 6 ship-or-pause decision being deferred ("I'll decide in Week 7") rather than made

## Cross-reference

Project brief at root: master plan for what's being built.
This file: how I keep myself accountable.
`build-log/decisions.md`: running architectural decisions log (interview substrate).
`build-log/sunday-YYYY-MM-DD.md`: weekly check-ins.
`build-log/mock-interview-YYYY-MM-DD.md`: mock interview reflections.
`build-log/YYYY-MM-DD.md`: daily build log entries.