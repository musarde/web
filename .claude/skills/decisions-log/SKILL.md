---
name: decisions-log
description: Draft entries for ../build-log/decisions.md in the Musarde architectural decision log format (Context / Considered / Picked / Why / Would-revisit-if / Interview-talking-point). Use this skill when the user explicitly asks to "log a decision," "add an ADR," "write this up for the decisions log," or when the user has just resolved an architectural tradeoff in conversation (e.g., picked Postgres pgvector over a dedicated vector DB, decided on an embedding model, settled a schema question, picked one ingestion shape over another) and is ready to capture it. Do not trigger on routine code edits, bug fixes, or implementation details — only on choices that compare named alternatives and shape system architecture.
---

# decisions-log

Draft a new entry for `../build-log/decisions.md`. The decisions log is interview substrate, not a changelog — every entry has to be defensible cold in 2 minutes to a system-design interviewer. Skip flavor text. Match the existing voice (terse, opinionated, no hedge words like "we feel" or "it seems").

## Before drafting

1. **Read `../build-log/decisions.md`.** Check whether the decision is already logged or is on the "anticipated entries" list at the bottom. If it's anticipated, you are turning a placeholder into a real entry — remove it from the anticipated list as part of the edit.
2. **Check `../build-log/decision-checklist.md`.** This file surfaces decisions expected by week. If the current decision matches one on the checklist for the active or recent week, note that connection in the entry's framing — the checklist is the "what's coming up" view, the decisions log is the "what got resolved" view.
3. **Read the most recent ~5 commits** (`git log --oneline -20`) to ground the Context section in what just shipped or got built. The decision usually corresponds to code that exists or is about to exist.
4. **Skim `../build-log/accountability-plan.md` §"Decisions log — tracked artifact"** if the format below feels ambiguous — the canonical spec lives there.
5. **Skim `../build-log/glossary.md`** so the entry uses the project's preferred terms (e.g., the names this project uses for sources, schemas, retrieval shapes). Drift between the entry and the glossary is a signal you're inventing terminology.
6. **Confirm the choice is actually architectural.** Library version bumps, lint rules, file naming — not architectural. Schema shape, vendor selection, ingestion shape, embedding model, retrieval pipeline shape, agent framework — architectural. If unclear, ask the user before drafting.

## Format

Use this exact template. The heading date is today (or the date the decision was actually made if the user specifies). Append the new entry to the end of the chronological section, above the "Anticipated entries" list.

```
## YYYY-MM-DD: [Decision title — short, names the choice]

**Context:** [What problem was I solving? 1–3 sentences. Reference the constraint that made this a decision rather than a default.]
**Considered:** [Named alternatives. Comma-separated or short bullet list. Don't list strawmen — only options actually weighed.]
**Picked:** [The choice, named the same way it appears in code or docs.]
**Why:** [The tradeoff. What you gave up, why it was worth giving up. 2–4 sentences.]
**Would revisit if:** [Concrete trigger. "Corpus exceeds X rows," "we add a second writer instance," "latency budget tightens below Y" — not "if requirements change."]
**Interview talking-point version:** [30-second framing — ≤ 80 words, ≤ 5 sentences. Should sound natural read aloud. Lead with the constraint, then the choice, then the tradeoff. No filler. Don't redefine the options Considered already lists.]
```

## Quality bar

A good entry passes these checks:

- **Considered** has at least two real alternatives with names. "Considered: nothing else" is a flag — either the decision wasn't actually a decision, or you didn't think hard enough.
- **Why** says what was given up, not just why the choice is good. "Picked Postgres + pgvector. Why: it's great" — bad. "Picked Postgres + pgvector over Pinecone because the corpus fits comfortably in one Postgres instance and operating two stateful systems doubles the on-call surface for a solo project" — good.
- **Would revisit if** is falsifiable. A future reader should be able to look at the system in 6 months and say "yes/no, the trigger fired."
- **Interview talking-point** is the pitch you'd give to an interviewer who asked "why this and not Pinecone?" If reading it aloud feels stilted, rewrite it.

## Voice

The repo's existing planning docs are direct, slightly blunt, no hedging. Match that. Avoid: "we feel that," "it might be worth," "ideally," "in the future." Prefer the active first-person ("I picked X because…") over passive constructions. The reader is the user, six weeks from now, prepping for an interview — write to that person.

## Length and trim

The log skews verbose by default. After drafting, do a trim pass:

- **No throat-clearing before lists.** Cut "Three observations made X indefensible:" → "Three reasons:" (or just the list).
- **Why introduces new info; it doesn't restate Context.** If the Why paragraph repeats the constraint or the alternatives from earlier sections, cut the restatement.
- **Picked describes the choice; Why explains it. Don't describe the choice twice.** If a numbered Picked item already explains its own tradeoff, the Why section shouldn't repeat that argument item-by-item.
- **Talking-point hard cap: 80 words, 5 sentences.** It names the choice and the tradeoff, not the options. Considered already lists them.
- **One em-dash per sentence, max.** Em-dash chains are a tell that the thought has more than one part — break into two sentences.

Vocabulary to swap:

| Avoid | Prefer |
|---|---|
| indefensible | wasn't worth it |
| post-hoc | after the fact |
| structurally novel | novel |
| symmetric failure mode | opposite failure |
| ecosystem tax | paying for what I won't use |
| operational layer | name the layer (queue, scheduler, worker tier) |
| load-bearing | important / critical (use sparingly) |
| tipping argument | decided it |
| untenable | breaks / doesn't work |
| meaningfully X-er than Y | name the magnitude or the comparison directly |
| rhyme but don't share bodies | look similar but share no code |

## After drafting

Show the user the drafted entry inline before writing to the file. Ask whether the **Would revisit if** trigger is falsifiable enough — that's the most common weak spot. After confirming, append to `../build-log/decisions.md` and remove any matching item from the "Anticipated entries" list at the bottom. If the decision corresponded to an item on `../build-log/decision-checklist.md`, mention that to the user so they can update the checklist too.
