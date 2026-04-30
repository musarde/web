# Musarde — Week-by-Week Decision Checklist

A running list of decisions surfaced from the project brief and accountability plan. Each decision should land in `/build-log/decisions.md` with the standard format (context, considered, picked, why, would-revisit-if, interview-talking-point).

The plan has two committed phases (Weeks 1–6) and one conditional phase (Weeks 7+). The Week 6 check-in is the only hard milestone; everything past it is renegotiable based on job-search status.

---

## Week 0 — Setup (Wed Apr 29 – Sun May 3)

- [ ] **Postgres host: Supabase or Neon?** Decide before Week 1 Day 1.
- [ ] Commit cadence and branch strategy
- [ ] Set up `/build-log/decisions.md` with template

---

## Week 1 — Data foundation: Met + AIC (May 4–10)

Schema decisions made this week ripple through everything else.

- [ ] **`texts` table key tuple.** `(object_id, type, language, source)` proposed. Sunday check-in audits.
- [ ] **Embedding model versioning approach.** Decide before generating any embeddings.
- [ ] **CLIP variant.** Default: OpenCLIP ViT-L/14 trained on LAION-2B. SigLIP if you want to defend a more deliberate choice.
- [ ] **🔑 Raw tool-use API vs. framework.** Day 7 deliverable. Recommend raw API; 200+ word entry.
- [ ] **Week 2 tool surface — sketched on paper.** Tool names, signatures, return shapes.

**Sunday May 10 check-in:** schema review (60 min). Flag concerns about Getty Linked Open Data fit coming in Week 6.

---

## Week 2 — Tool-using planning agent (May 11–17)

Densest decision week — target 4–5 entries. SF travel May 15–20: real Week 2 deadline is Thu May 14 EOD.

- [ ] **Tool surface granularity.** Coarse mega-tool vs. fine composable tools.
- [ ] **Termination policy.** Max steps, hard timeout, "good enough" criteria.
- [ ] **History management strategy.** Full vs. summarized vs. windowed.
- [ ] **Failure handling per tool.** Empty results, 404s, model loops.
- [ ] **Agent observability schema.** Step number, tool, args, result, reasoning, latency, cost.
- [ ] **Cross-city aggregation primitive — adapter shape.** Single-city in v1, fan-out in v1.5.

---

## Week 3 — In-gallery PWA + first PWA field test (May 18–24)

Effectively starts Wed May 21 due to SF trip.

- [ ] **Streaming approach for LLM responses.** SSE vs. WebSockets.
- [ ] **Offline cache scope.** Route, images, text, agent traces?
- [ ] **Field-test target museum (Seattle).** SAM, SAAM, Tacoma, or Frye as visitor.
- [ ] **Field-test failure-logging format.** Decide before the visit.

---

## Week 4 — Vision feature + SAM manual catalog (May 25–31)

Phase 1 boundary. First continue/stop decision.

- [ ] **Vision pipeline architecture.** Filtering, k, fallback for works not in index.
- [ ] **Photo upload path.** Presigned-URL direct-to-S3 vs. through API.
- [ ] **Latency budget breakdown.** <3s end-to-end target.
- [ ] **🔑 SAM manual catalog protocol.** Pre-built before the visit:
  - OCR pipeline tested on sample labels
  - Schema for SAM-manual records
  - Capture flow rehearsed
  - Distribution targets locked: ~25 representational, ~20 abstract/modern, ~20 contemporary/conceptual, ~15 Asian art, ~10 Indigenous Northwest Coast, ~10 sculpture
- [ ] **🔑 Eval set capture protocol.** Label scan + work photo + condition tags. Pair-by-timestamp or pair-by-explicit-key?
- [ ] **SAM visit logistics.** One Saturday or two? Combine SAM + SAAM?
- [ ] **🔑 Phase 1 continue/stop check.** Are bullets 1 and 2 credible? Is Week 5+ work architecturally rich?

**Sunday May 31 check-in:** vision performance audit + Phase 1 boundary review.

---

## Week 5 — Reading companion (Jun 1–7)

- [ ] **Corpus sourcing scope.** Quality over quantity.
- [ ] **Chunking strategy.** Fixed vs. semantic-boundary. Size?
- [ ] **Retrieval k.**
- [ ] **🔑 Iterative retrieval trigger.** When does the LLM decide a second round is needed?
- [ ] **Reranker choice.** None vs. cross-encoder vs. LLM-as-judge.
- [ ] **Eval comprehension rubric — concrete.** 3 questions per held-out work. Scoring method.
- [ ] **Held-out work selection.** Verify with grep that criticism is NOT in corpus.

---

## Week 6 — Getty integration + interview-readiness checkpoint + 🔑 ship-or-pause decision (Jun 8–14)

**The only hard milestone. The whole 6-week commitment lands here.**

- [ ] **Getty data fetch strategy.** SPARQL vs. bulk export. JSON-LD parsing approach.
- [ ] **Linked Art concept normalization.** Production events, artist nodes, materials/techniques URIs.
- [ ] **Schema audit post-Getty.** Anything in `raw_metadata` JSONB deserve promotion?
- [ ] **Taste profile representation (minimal stub).** Mean aggregation. v1 only; deeper in v1.5.
- [ ] **🔑 Interview-readiness self-audit.**
  - Whiteboard architecture from memory in 10 minutes
  - Top 5 architectural decisions defended in 2 min each
  - Agent's tool surface and loop semantics cold
  - Each technology choice — business requirement and tool rationale
  - Resume bullets ready to add today
- [ ] **🔑 CONTINUE / SCALE-BACK / PAUSE DECISION.** Based on job-search bandwidth at this point. See accountability plan for framework. The decision is binding for at least the next 2 weeks.

**Sunday Jun 14 check-in:** full interview-readiness audit. Project bullets land on the resume regardless of what comes next. The continue/scale-back/pause framing dictates the rest of the plan.

---

## Weeks 7+ — Conditional decisions

The decisions below only apply if the Week 6 check-in chose "continue" or "scale back."

### If continuing at full pace

**Week 7 — Hybrid retrieval + second SAM field test**
- [ ] Hybrid retrieval architecture (CLIP + text + LLM rerank — order, weights, fallback)
- [ ] Hybrid eval design — how is "contemporary subset" defined?
- [ ] Coverage gaps to address in second SAM visit
- [ ] Optional: extend Week 5's iterative retrieval if gains were clear

**Week 8 — Phase 2 ship**
- [ ] Public blog post topic — agent loop, multimodal eval, or comprehension eval. Pick one.
- [ ] Demo video format and venue.
- [ ] **🔑 Resume bullets v1.0.** Lock numbers. SAM-only data; multi-museum framing comes after potential August trip.
- [ ] **🔑 NYC trip dates.** Aug 3–9 or Aug 10–16. Decide based on calendar; book by mid-July.
- [ ] Trip scope: Met main only, or Met + Cloisters?

**Phase 3 (Weeks 9–12)**
- [ ] A/B retrieval architecture (Week 9)
- [ ] CDN edge cache layer (Week 9)
- [ ] Hybrid retrieval deepening (Week 10) — reranker choice if not finalized
- [ ] Continuous eval harness (Week 11)
- [ ] **Trip booking deadline: Sunday Jul 12 (Week 11).**
- [ ] **🔑 Phase 4 vs. interview-reps decision (Week 12).** Cross-city agent or more mock interviews?
- [ ] **🔑 NYC eval-capture protocol refresh.** Adjust for the Met's scale.

**Week 13 — Pre-trip prep**
- [ ] Trip itinerary (Met main + Cloisters split)
- [ ] Phase 4 cross-city agent shape (if happening)
- [ ] Eval-capture toolchain rehearsed against Met data
- [ ] Optional v1.5 source for opportunistic NYC capture (Brooklyn Museum?)

**Week 14 — NYC capstone field test (Aug 3–9)**
- [ ] Daily route — agent-generated or hand-picked?
- [ ] Per-day eval target (~30 photos × 3 days = 90)
- [ ] Real-time logging discipline
- [ ] Reading companion test on contemporary works
- [ ] Phase 4 trip-as-agent test (if happening)

**Weeks 15–16 — Trip data + resume finalization**
- [ ] Full multi-museum eval computation
- [ ] **🔑 Resume bullets v1.1 — multi-museum upgrade.** Lock final numbers.
- [ ] Final blog post / demo video update
- [ ] Phase 4 wrap (if happening)
- [ ] **🔑 Project ship decision (Sunday Aug 23).**

### If scaling back to on-call mode

- [ ] Decide weekly cap on Musarde hours (e.g., 5–8 hours/week)
- [ ] Use the project as personal-use surface; capture iteration ideas without immediately building them
- [ ] Maintain weekly mock interview using Week 6 substrate
- [ ] At each Sunday check-in, re-evaluate whether to push back to full or pause

### If pausing

- [ ] Resume bullets v0.6 stay on the resume
- [ ] Interview substrate is the Week 6 audit material
- [ ] Decision criterion for un-pausing: explicitly write what would trigger restart

---

## Recurring decisions (every Sunday)

- [ ] Continue/stop on optional features
- [ ] Travel calendar updates
- [ ] Risk pulse — especially: interview-prep avoidance via project work, momentum decay, project effort drifting against job search
- [ ] Decisions-log entries this week (zero is a flag)

---

## Decisions to *not* re-litigate

Once made, leave alone unless something concrete breaks.

- Stack choice (Next.js, Tailwind, Vercel, Postgres+pgvector)
- Met + AIC + Getty + SAM-manual as v1 sources
- Raw tool-use API over framework (after Week 1 entry)
- SAM as manually-catalogued (not scraped) substrate
- Reading companion uses light-iterative retrieval
- NYC as the capstone field-test target (if August trip happens)
- **Week 6 as the only hard milestone; Weeks 7+ are conditional**

If one starts feeling wrong, write a decisions-log entry on *why* before deciding to change.