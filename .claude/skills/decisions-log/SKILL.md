---
name: decisions-log
description: Draft entries for build-log/decisions.md in the Musarde architectural decision log format (Context / Considered / Picked / Why / Would-revisit-if / Interview-talking-point). Use this skill when the user explicitly asks to "log a decision," "add an ADR," "write this up for the decisions log," or when the user has just resolved an architectural tradeoff in conversation (e.g., picked Postgres pgvector over a dedicated vector DB, chose SKIP LOCKED over a separate queue service, decided on an embedding model, settled a schema question) and is ready to capture it. Do not trigger on routine code edits, bug fixes, or implementation details — only on choices that compare named alternatives and shape system architecture.
---

# decisions-log

Draft a new entry for `build-log/decisions.md`. The decisions log is interview substrate, not a changelog — every entry has to be defensible cold in 2 minutes to a system-design interviewer. Skip flavor text. Match the existing voice (terse, opinionated, no hedge words like "we feel" or "it seems").

## Before drafting

1. **Read `build-log/decisions.md`.** Check whether the decision is already logged or is on the "anticipated entries" list at the bottom. If it's anticipated, you are turning a placeholder into a real entry — remove it from the anticipated list as part of the edit.
2. **Read the most recent ~5 commits** (`git log --oneline -20`) to ground the Context section in what just shipped or got built. The decision usually corresponds to code that exists or is about to exist.
3. **Skim `accountability-plan.md` §"Decisions log — tracked artifact"** if the format below feels ambiguous — the canonical spec lives there.
4. **Confirm the choice is actually architectural.** Library version bumps, lint rules, file naming — not architectural. Schema shape, vendor selection, queue/cache design, embedding model, retrieval pipeline shape, agent framework — architectural. If unclear, ask the user before drafting.

## Format

Use this exact template. The heading date is today (or the date the decision was actually made if the user specifies). Append the new entry to the end of the chronological section, above the "Anticipated entries" list.

```
## YYYY-MM-DD: [Decision title — short, names the choice]

**Context:** [What problem was I solving? 1–3 sentences. Reference the constraint that made this a decision rather than a default.]
**Considered:** [Named alternatives. Comma-separated or short bullet list. Don't list strawmen — only options actually weighed.]
**Picked:** [The choice, named the same way it appears in code or docs.]
**Why:** [The tradeoff. What you gave up, why it was worth giving up. 2–4 sentences.]
**Would revisit if:** [Concrete trigger. "Corpus exceeds X rows," "we add a second writer instance," "latency budget tightens below Y" — not "if requirements change."]
**Interview talking-point version:** [30-second framing. Should sound natural read aloud. Lead with the constraint, then the choice, then the tradeoff. No filler.]
```

## Quality bar

A good entry passes these checks:

- **Considered** has at least two real alternatives with names. "Considered: nothing else" is a flag — either the decision wasn't actually a decision, or you didn't think hard enough.
- **Why** says what was given up, not just why the choice is good. "Picked Postgres + pgvector. Why: it's great" — bad. "Picked Postgres + pgvector over Pinecone because the corpus fits comfortably in one Postgres instance and operating two stateful systems doubles the on-call surface for a solo project" — good.
- **Would revisit if** is falsifiable. A future reader should be able to look at the system in 6 months and say "yes/no, the trigger fired."
- **Interview talking-point** is the pitch you'd give to an interviewer who asked "why this and not Pinecone?" If reading it aloud feels stilted, rewrite it.

## Voice

The repo's existing planning docs are direct, slightly blunt, no hedging. Match that. Avoid: "we feel that," "it might be worth," "ideally," "in the future." Prefer the active first-person ("I picked X because…") over passive constructions. The reader is the user, six weeks from now, prepping for an interview — write to that person.

## After drafting

Show the user the drafted entry inline before writing to the file. Ask whether the **Would revisit if** trigger is falsifiable enough — that's the most common weak spot. After confirming, append to `build-log/decisions.md` and remove any matching item from the "Anticipated entries" list at the bottom.
