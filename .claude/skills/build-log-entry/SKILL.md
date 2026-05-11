---
name: build-log-entry
description: Draft a daily Musarde build-log entry at ../build-log/daily/YYYY-MM-DD.md by reading today's commits and recent file changes, formatted as What I worked on / What worked / What broke or surprised me / Decisions made today / Open questions / Tomorrow's first task. Use this skill when the user says "log today," "build log entry," "EOD log," "daily log," "wrap up today," or asks to capture the day's Musarde work. The skill produces a draft the user edits before committing. Do not trigger for retrospectives that span multiple days (use sunday-checkin for the weekly review) or for repos other than Musarde.
---

# build-log-entry

Draft today's build-log entry at `../build-log/daily/YYYY-MM-DD.md`. The goal is to lower friction — the user is tired at end of day and the entry needs to take 5 minutes, not 20. Pre-fill what you can read from the repo, leave judgment calls blank.

Note: the build-log lives in a sibling private repo at `../build-log/`, not in this code repo. Daily entries live under `../build-log/daily/`; Sunday check-ins live under `../build-log/weekly/`. Run git commands against that repo (e.g., `git -C ../build-log log ...`) when reading prior entries; run code-repo git commands from the working directory as usual.

## Inputs to gather

Run these in parallel.

1. **Today's commits.**
   ```
   git log --since="midnight" --pretty=format:"%h %ad %s%n%b" --date=iso
   ```
   If empty, also try `--since="24 hours ago"` to catch late-night work crossing midnight. Note which it was; the user may want today's date or yesterday's.

2. **Today's file changes (including uncommitted).**
   ```
   git status --short
   git diff --stat HEAD
   ```
   Uncommitted work counts toward "what I worked on" even if not pushed.

3. **Yesterday's build-log entry**, if it exists.
   Read `../build-log/daily/<yesterday>.md` and pull the "Tomorrow's first task" line. That's the audit anchor: did today's work actually start with that task? If not, that's worth flagging — drift is interesting data.

## Output format

Use this exact template. Match the existing build-log voice if entries already exist (read one or two recent files); otherwise default to terse first-person, no headers beyond the section heads.

The Length-and-trim rules from the decisions-log skill (one em-dash per sentence, no throat-clearing, vocabulary swaps like "indefensible" → "wasn't worth it") apply to bullets here too. Build-log bullets skew short anyway, but if a bullet is running long, trim the same way.

```
# YYYY-MM-DD

## What I worked on
- [bullet per coherent chunk of work, not per commit; collapse "fix typo" + "fix typo again" into one line]
- ...

## What worked
- [things that came together faster than expected, patterns that clicked, tools/libraries that lived up to the docs]
- ...

## What broke or surprised me
- [bugs that took longer than they should have, library behavior that surprised you, integrations that didn't go to plan; small surprises count — they feed Sunday §5 and the eventual stress-test material]
- ...

## Decisions made today
- [architectural calls worth pinning. If a call is meaty enough (compares named alternatives, shapes system architecture), it also belongs in `../build-log/decisions.md` via the decisions-log skill — flag candidates here, write the formal entry separately.]
- ...

## Open questions
- [things you couldn't decide, places where you punted, "is this the right shape?" doubts]
- ...

## Tomorrow's first task
[one sentence, concrete enough to execute on autopilot before coffee finishes]
```

## What to pre-fill vs. leave blank

**Pre-fill from repo state:**
- "What I worked on" — translate commits and uncommitted diffs into chunks. Don't list raw commit messages; group related commits ("Wired up the Met adapter's transform layer and tests" beats "Add transform.py" + "Fix transform" + "Add fixture"). One bullet per coherent chunk.
- "Decisions made today" — if commits or daily-log notes suggest a clear architectural call, list it as a candidate. Don't write the full ADR here; the decisions-log skill is for that.
- Audit note against yesterday's "Tomorrow's first task" — if yesterday said "wire up CLIP embeddings" and today's commits are all about queue retries, surface that as an "Open questions" candidate ("punted on CLIP embeddings — why?").

**Leave blank with a `_[fill in]_` marker:**
- "What worked" — judgment call. Code diffs don't tell you what felt good.
- "What broke or surprised me" — usually undocumented in commits. The user has to write this.
- "Open questions" — seed with the audit note above if applicable, otherwise blank.
- "Tomorrow's first task" — only the user knows.

It's tempting to fill everything from commit messages and look helpful. Don't. A pre-filled "What broke" section that's actually invented from thin air is worse than an empty one — it makes the user delete and rewrite.

## Edge cases

- **No commits today.** Don't write "took the day off" or invent activity. Surface it: "No commits today. Want to log a no-code day (reading, museum visit, planning) or skip the entry?" The build log isn't a streak; missing days are fine.
- **Lots of commits, all small fixes.** Group them. "Various adapter cleanups" is a fine bullet for 8 small commits on the same area. Don't pad.
- **The file already exists.** Likely — morning check-in proactively stubs `YYYY-MM-DD.md` per the file-maintenance protocol in `musarde-project.md`. Read what's there, treat existing pre-fill (yesterday's task, this week's deliverable, calendar items) as scaffolding, and fill in around it. Don't overwrite without showing the user.
- **It's after midnight but the user means "yesterday's work."** Confirm the date before writing. The filename is the date the work happened, not the wallclock at write time.

## After drafting

Show the draft inline. Tell the user explicitly which sections you pre-filled vs. left blank. Don't commit — the user edits, then commits themselves. If they ask you to commit, it's a separate, explicit action.
