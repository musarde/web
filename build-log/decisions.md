# Decisions Log — Musarde

Running architectural decisions log. Every meaningful choice gets an entry. Read every Sunday during check-in. Zero entries in a week is a flag.

## Entry template

```
## YYYY-MM-DD: [Decision title]

**Context:** What problem was I solving?
**Considered:** Alternatives.
**Picked:** X
**Why:** [Trade-offs.]
**Would revisit if:** [What changes my mind.]
**Interview talking-point version:** [30-second version.]
```

---

## 2026-04-30: Ingestion shape — one-shot loader, no queue, no scheduler

**Context:** v1 indexes ~680K artworks from Met, AIC, Getty, plus ~100 manually-catalogued from SAM. Initial framing assumed a "fault-tolerant ingestion pipeline" with a Postgres-backed job queue (SKIP LOCKED, retry/DLQ) and Vercel cron for scheduled refreshes. Stress-testing the stack in Week 0 surfaced that this was infrastructure designed around a resume bullet rather than around the actual workload.

**Considered:**
- Postgres SKIP LOCKED queue + always-on worker container (Render / Fly.io / Railway, ~$5–10/month)
- Postgres SKIP LOCKED queue + Vercel cron-triggered short-lived functions
- One-shot loader script, run on-demand from laptop or one-shot VM, with idempotent upserts

**Picked:** One-shot loader script. Idempotent upserts on natural keys. Re-run quarterly or on-demand when a source publishes a notable update. No queue, no scheduler, no worker tier.

**Why:** Three observations made the queue infrastructure indefensible:
1. Museum collection data updates on the order of months, not hours. Met publishes weekly CSVs but the diffs are tiny — mostly new acquisitions and field corrections. AIC and Getty are similar.
2. Bulk ingestion happens twice in v1 (Week 1 for Met + AIC, Week 6 for Getty). Steady-state delta volume after that is tens-to-hundreds of records per quarter.
3. The user-facing in-gallery photo upload path is synchronous (S3 → embed → return result), not queued — the user is waiting for the result.

A queue with DLQ would be infrastructure solving a problem the app does not have. The interesting integration story is the adapter pattern across three structurally different source paradigms (CSV, REST, Linked Open Data), not the operational layer above it.

**Would revisit if:** A source moves to a streaming/webhook update model; v1.5 adds a source whose update cadence is daily-or-faster; user upload volume grows to where async processing is genuinely warranted.

**Interview talking-point version:** "I started by asking what the workload actually was. Museum collections update on the order of months, the project ingests three sources twice in v1, and the user-facing upload path is synchronous. None of that justified queue infrastructure, so the loader is a re-runnable script with idempotent upserts on natural keys. The interesting work is the adapter pattern across three source paradigms — CSV, REST, Linked Open Data — not an operational layer the workload didn't ask for."

---

## 2026-04-30: Decision filter — match infrastructure to workload, not to resume

**Context:** Week 0 stack stress test surfaced multiple pieces of the original plan (job queue with DLQ, Vercel cron, GPT-4o-as-second-provider) that were chosen partly because they would produce interview-grade resume bullets, not because the app needed them. The pattern surfaced twice in one Week 0 conversation; it was worth naming as a governing principle rather than handling case-by-case.

**Considered:**
- Build the substrate the resume bullets describe, then justify post-hoc
- Build the app the workload demands, then describe honestly what got built

**Picked:** Workload-first. For every piece of infrastructure, the honesty test is: name a concrete thing the app does this quarter that requires it. If the answer is "it would be impressive on a resume" or "it shows I know about distributed systems," cut it.

**Why:** Senior interviewers — Bar Raisers especially — ding over-engineering harder than under-engineering. A defensible "I didn't build X because the workload didn't justify it" beats a shaky "I built X" every time. Resume-driven over-engineering is also the symmetric failure mode to interview-prep avoidance via project work: both are the project warping around something other than the app's actual needs.

This filter is what produced the no-queue, no-cron, Claude-only stack decisions in Week 0. It will govern downstream calls about the A/B retrieval harness (Week 9), continuous eval harness (Week 11), and the hybrid retrieval reranker (Week 7) when those come up.

**Would revisit if:** Never. This is the governing principle.

**Interview talking-point version:** "I had to actively resist the temptation to add infrastructure the project didn't need just because it would sound good on a resume. The discipline I held was: name a concrete thing the app does this quarter that requires this piece of infrastructure. If I couldn't, I cut it. That's how I ended up with no job queue, no cron scheduler, and one LLM provider instead of two — and it gave me cleaner architectural answers, not weaker ones."

---