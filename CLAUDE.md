# Musarde — Claude Code context

## What this repo is
Mobile-first museum companion app. Pre-visit route planning + in-gallery
camera/RAG flow. Mobile-first PWA on Vercel; Next.js + Postgres/pgvector +
CLIP + Claude/GPT-4o.

The repo currently holds planning docs only. Code lands starting Mon May 4
(Week 1). See `musarde_project.md` for the full brief.

## Primary docs (read these before editing anything)
- `musarde_project.md` — master project brief, scope, 8-week plan
- `accountability-plan.md` — cadence, check-ins, interview-prep track,
  resume-bullet readiness table
- `build-log/sunday-checkin-template.md` — copy this each Sunday into
  `build-log/sunday-YYYY-MM-DD.md`
- `build-log/decisions.md` — running architectural decisions log

## Conventions when updating planning docs
- The two planning docs (`musarde_project.md`, `accountability-plan.md`)
  are interlinked. If you change scope in the project brief, check whether
  the accountability plan's phase boundaries, target dates, or
  resume-bullet table still match. Flag mismatches; don't silently fix one
  without the other.
- Target dates and the travel calendar in `accountability-plan.md` are
  load-bearing. Don't shift them without explicitly noting the trigger.
- The `raw_metadata` JSONB escape hatch and the `texts` table shape are
  schema decisions called out as critical in Week 1. Preserve those when
  any data-model section is edited.
- v1 scope is deliberately narrow: Met + AIC + one third source (clean
  APIs only). Seattle museums via scraping and multilingual translator
  are explicitly deferred. Don't drift these back into v1.
- The reading companion's eval (Week 5) requires baseline comparison vs.
  vanilla LLM and held-out works. Both are non-negotiable per the brief.

## Build-log conventions
Daily: `build-log/YYYY-MM-DD.md` — what worked, what broke, open
questions, tomorrow's first task.
Sunday: copy `sunday-checkin-template.md` to `sunday-YYYY-MM-DD.md`.
Mock interview: `build-log/mock-interview-YYYY-MM-DD.md`.

## What I want from Claude Code on planning-doc edits
- Push back on architecture choices before I commit to them
- Flag when a scope change in one doc would invalidate something in the
  other
- Don't auto-expand v1 scope. Defer-to-v1.5/v2 is the default answer for
  ambiguous additions.
- For resume bullets, demand the specific number/measurement that fills
  the placeholder. Don't let `[X%]` survive into a "ready" bullet.
