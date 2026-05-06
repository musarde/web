# Decisions Log — Test Fixture

Smoke fixture for decisions_drift tests. Two real-shape entries plus
one entry with long-form bullets (no extractable short names).

## Entry template

```
## YYYY-MM-DD: [Decision title]

**Context:** What problem was I solving?
```

---

## 2026-04-30: Postgres host — Neon over Supabase

**Context:** v1 needs Postgres + pgvector.

**Considered:**
- Supabase — Postgres-plus-(auth, storage, realtime, edge functions)
- Neon — focused Postgres-as-a-service with copy-on-write data branching

**Picked:** Neon.

**Why:** ecosystem tax on cut features.

**Would revisit if:** auth/realtime needs grow.

**Interview talking-point version:** "I'm using none of Supabase's non-Postgres surface."

---

## 2026-05-01: Postgres version — 17 over 18

**Context:** Neon supports both PG17 and PG18. Need to pick before Week 1.

**Considered:**
- PG18 — newer, async I/O, native UUIDv7
- PG17 — production miles, mature pgvector ecosystem

**Picked:** PG17.

**Why:** No v1 workload needs PG18-only features.

---

## 2026-05-02: Decision filter — workload over resume

**Context:** Multiple Week-0 picks had resume-driven framing.

**Considered:**
- Build the substrate the resume bullets describe, then justify post-hoc
- Build the app the workload demands, then describe honestly what got built

**Picked:** Workload-first.

**Why:** Senior interviewers ding over-engineering harder than under-engineering.
