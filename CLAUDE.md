# Musarde — Claude Code context

## What this repo is
Mobile-first museum companion app. Pre-visit route planning + in-gallery
camera/RAG flow. Mobile-first PWA on Vercel; Next.js + Postgres/pgvector +
CLIP + Claude.

The repo currently holds scaffolding only. Code lands starting Mon May 4
(Week 1).

## Where the planning docs live
Project planning, decisions log, and weekly check-ins live in a separate
**private** repo at `../build-log/` (sibling directory, not a submodule).
Claude Code can read them via relative paths when run from this directory.

Primary references:
- `../build-log/musarde-project.md` — master project brief, scope, plan
- `../build-log/accountability-plan.md` — cadence, Sunday check-ins,
  resume-bullet readiness table, Week 6 ship-or-pause framework
- `../build-log/decisions.md` — running architectural decisions log
- `../build-log/glossary.md` — project-specific terms
- `../build-log/decision-checklist.md` — week-by-week decisions surfaced
- `../build-log/weekly/sunday-checkin-template.md` — copied each Sunday into
  `../build-log/weekly/sunday-YYYY-MM-DD.md`

The Musarde build-log is project-only. Job-search status, mock-interview
reflections, and HelloInterview / system-design study live in a separate
Sabbatical Strategy project — don't pull or reference them from build-log
files.

If `../build-log/` isn't present (e.g. someone cloned just `web/`), these
references won't resolve. That's expected — the planning material is
deliberately separated from the public code repo.

## Plan shape (as of Apr 30 2026)
- **Weeks 1–6 are committed.** Sunday Jun 14 is the only hard milestone:
  resume bullets ready, interview-readiness audit complete, ship-or-pause
  decision made.
- **Weeks 7+ are conditional** on job-search bandwidth at Week 6.
- Primary goal is a job by end of August 2026. Musarde is interview
  substrate in service of that goal, not the goal itself.

## Stack (current as of Week 0)
- Next.js (App Router), Tailwind, Vercel as PWA
- Postgres on Neon, pgvector for embeddings
- Vision: OpenCLIP ViT-L/14 default; SigLIP under consideration (Week 1)
- Text embeddings: TBD pending Week 3 three-way bake-off (Thu May 21
  hard deadline; reslotted from Week 1 — see decisions.md 2026-05-11
  calendar contract entry)
- LLM: Claude only. Single provider for v1 — GPT-4o was cut in Week 0.
- Agent: raw Claude function-calling API, not a framework
- Loader: on-demand re-runnable Python script. No queue, no cron.
  Decision logged Week 0.

## v1 ingestion sources (locked)
Met (CSV) + AIC (REST) + Getty (Linked Open Data) + SAM (manually
catalogued ~100 works, captured during visits — not scraped). Don't
drift other Seattle museums or scraping-based sources back into v1.

## Conventions when updating planning docs in `../build-log/`
- The brief and accountability plan are interlinked. If scope changes in
  one, check whether phase boundaries, target dates, or the resume-bullet
  table still match in the other. Flag mismatches; don't silently fix one
  without the other.
- Target dates and the travel calendar are load-bearing. Don't shift them
  without explicitly noting the trigger.
- The `raw_metadata` JSONB escape hatch and the `texts` table shape are
  schema decisions called out as critical in Week 1. Preserve those when
  any data-model section is edited.
- v1 scope is deliberately narrow. Defer-to-v1.5/v2 is the default answer
  for ambiguous additions.
- The reading companion's eval (Week 5) requires three-way comparison
  (vanilla LLM / single-shot RAG / iterative RAG) and held-out works.
  Both are non-negotiable per the brief.
- For resume bullets, demand the specific number/measurement that fills
  any placeholder. Don't let `[X%]` survive into a "ready" bullet.
- Decisions-log entries follow the standard format (context, considered,
  picked, why, would-revisit-if, interview talking-point version).

## Build-log file conventions (in `../build-log/`)
- Daily build logs live in `../build-log/daily/`:
  `daily/YYYY-MM-DD.md` — what worked, what broke, open questions,
  tomorrow's first task
- Sunday check-ins live in `../build-log/weekly/`:
  copy `weekly/sunday-checkin-template.md` to `weekly/sunday-YYYY-MM-DD.md`
- In-place planning files (`musarde-project.md`, `accountability-plan.md`,
  `decisions.md`, `decision-checklist.md`, `glossary.md`) stay at the
  `../build-log/` root
- No mock-interview files here — they live in `~/vaults/kokochi/Mock Interviews/`,
  governed by the Sabbatical Strategy project

## What I want from Claude Code
- Push back on architecture choices before I commit to them, especially
  in the weak areas: vision/multimodal, agent design, Linked Open Data
- Apply the workload-vs-resume filter (Week 0 governing decision): for
  any piece of infrastructure, name a concrete thing the app does this
  quarter that requires it. If the answer is "it would be impressive on
  a resume," cut it.
- Flag when a scope change in one planning doc would invalidate
  something in another
- Don't auto-expand v1 scope
- Verify museum API status before assuming it from training data