---
name: sunday-checkin
description: Populate the weekly Sunday check-in entry for the Musarde build log by aggregating the week's commits, new entries in ../build-log/decisions.md, daily build-log files in ../build-log/daily/, and current resume-bullet status against the sunday-checkin-template structure. Use this skill when the user says "sunday checkin," "weekly review," "fill in the sunday checkin," "weekly buildlog," or asks for a status summary of the past week's Musarde work. The output is saved to ../build-log/weekly/sunday-YYYY-MM-DD.md and covers what shipped, what slipped, decisions logged, architecture defensibility, resume-bullet readiness, project risk pulse, and next week's first task. Job-search status, mock-interview reflections, and HelloInterview / system-design study live in the Sabbatical Strategy project — this skill does not pull or fill them in. Trigger only for Musarde weekly-review requests — not for general status updates or other repos.
---

# sunday-checkin

Generate a draft Sunday check-in for the Musarde build log. The check-in is for the user, not for an audience — the brief explicitly says "be honest with yourself; this file is for you, not a performance." Drafts that read like LinkedIn posts have failed.

This check-in covers Musarde build state only. Do not pull or fill job-search status, mock-interview reflections, or HelloInterview / system-design study — those live in the Sabbatical Strategy project.

## Inputs to gather

Run these in parallel before writing anything. Don't ask the user to feed you the data — pull it yourself.

The build-log is a sibling private repo at `../build-log/`, not in the code repo. Daily entries live under `../build-log/daily/`; Sunday check-ins (including this skill's output and `sunday-checkin-template.md`) live under `../build-log/weekly/`. Use `git -C ../build-log <cmd>` for git operations against it; use plain `git <cmd>` from the working directory for code-repo commits.

1. **The week's commits in the code repo.**
   ```
   git log --since="7 days ago" --pretty=format:"%h %ad %s" --date=short
   ```
   Group by day. Note any day with zero commits.

2. **New `../build-log/decisions.md` entries from this week.**
   ```
   git -C ../build-log log --since="7 days ago" -p -- decisions.md
   ```
   Extract the headings of any entries added in the last 7 days. Zero entries this week is itself a signal — call it out explicitly. Cross-check against `../build-log/decision-checklist.md`: if the checklist anticipated decisions for this week and none were logged, flag the gap.

3. **Daily build-log files from the week.**
   List and read `../build-log/daily/YYYY-MM-DD.md` for each day in the past 7 days that exists. Missing days are also signal.

4. **Last week's "Next week's primary deliverable" and "Monday's first task."**
   Find the previous `../build-log/weekly/sunday-*.md` file. Read sections 9 and 10. The current week's check-in audits against last week's commitments — without them you're writing in a vacuum.

5. **Current resume-bullet status.**
   Read `../build-log/accountability-plan.md` §"Resume-bullet readiness." Note which v0.6 bullets are claimed-ready vs. in-progress. Cross-reference against what the commits and daily logs actually demonstrate.

6. **Glossary check.**
   Skim `../build-log/glossary.md` so the draft uses the project's preferred terms (sources, schemas, retrieval shapes). Drift from the glossary is a quiet signal you're inventing terminology.

## Output

Copy `../build-log/weekly/sunday-checkin-template.md` to `../build-log/weekly/sunday-YYYY-MM-DD.md` (today's date), then fill in what you can from the gathered inputs. **Leave fields you can't determine empty** rather than guessing — the user will fill them in.

The template has 10 numbered sections in Part 1 (project deliverable check, architecture defensibility, decisions log, what I learned, what broke or surprised me, risk pulse, resume-bullet readiness, decision queue, next week's primary deliverable, Monday's first task), plus Part 2 failure-mode signals and Part 3 (Week 6 only).

You can fill these reliably:
- §1 "This week's primary deliverable was" — pull from last Sunday's section 9.
- §3 "What got added to `../build-log/decisions.md` this week" — list headings of entries added in the last 7 days. If zero, write "Zero entries this week — flag." (Per the template: zero is a flag.) If `../build-log/decision-checklist.md` listed expected decisions for this week that weren't logged, name them.
- §5 "What broke or surprised me" — pull from daily build-log "What broke or surprised me" sections.
- §7 "Resume-bullet readiness" — list bullets currently marked ready vs. in-progress in the accountability plan. Add a flag if a bullet claimed "ready" doesn't have demonstrable code/data behind it from the week's commits.

You **cannot** fill these — leave blank with a `_[fill in]_` marker:
- §1 status (hit/partial/missed) — show evidence, let user judge
- §2 architecture defensibility check — the user has to whiteboard
- §4 what I learned
- §6 risk pulse
- §8 decision queue
- §9 next week's primary deliverable
- §10 Monday's first task

For §1 (status hit/partial/missed), provide **evidence** — the commits and daily logs that bear on whether the deliverable shipped — and let the user grade. Do not grade for them.

## Failure-mode signals (Part 2 of the template)

After filling, evaluate the Part 2 checkboxes against what you actually found:

- **"Two consecutive Sundays of partial/missed."** Read the previous Sunday file. If both this week and last show partial/missed on the primary deliverable, check the box.
- **"Zero decisions-log entries when there should have been some."** If the week had substantial commits but zero decisions entries, flag it. Cross-check `decision-checklist.md` for the active week — if expected decisions are listed and none were logged, the box checks. "Should have been some" can be a judgment call; raise it as a question if borderline.
- **"Architecture defensibility checks failing on the same decision two weeks running."** Read the previous Sunday file's §2. If a decision marked "no" or "partially" defensible last week is also marked the same way this week (or not addressed), check the box. The user has to fill the current week's §2 first, so this may need to surface as a question after the user completes §2.
- **"Week 6 ship-or-pause decision deferred."** Only relevant on or after Week 6 (Sun Jun 14). If the user is at Week 6 or later and Part 3 hasn't been filled, flag it.

If two or more of these signals fire, **lead the response** with that flag, not with the routine summary. The template's whole point is to catch failure modes — surfacing them is the skill's job.

(Cross-project failure modes — mock interviews skipped, applications stalling, gaps recurring in mocks — are tracked in the Sabbatical Strategy project. Don't pull or surface them here.)

## Week 6 ship-or-pause checkpoint (Part 3)

Only fill out on Sun Jun 14 (Week 6) or any subsequent Sunday where the previous decision is being re-evaluated (re-evaluations no earlier than 2 weeks after the prior decision). Otherwise leave Part 3 entirely untouched. Check today's date against Jun 14 before deciding whether to expand this section.

When Part 3 applies, the project-side audit is fully fillable from build state and the user's whiteboard self-test. The job-search-side inputs come from the Sabbatical Strategy project — leave them blank with a `_[pull from Sabbatical Strategy]_` marker; do not invent or guess.

## Voice and tone

The template is brutal on purpose. Match it: terse, no softening, no "great progress this week!" framing. If something slipped, say it slipped. If decisions log is empty, that's a flag — don't bury it in encouragement. The user's note in the template says this file is for them, not a performance, and "the discomfort is the point" appears multiple times. Lean into that.

The Length-and-trim rules from the decisions-log skill (one em-dash per sentence, no throat-clearing, vocabulary swaps) apply here too — especially in §4 (what I learned) and §6 (risk pulse), where prose is the easiest place to soften.

## After drafting

Show the draft inline, then write it to `../build-log/weekly/sunday-YYYY-MM-DD.md`. Tell the user which fields you left blank and which auto-detected signals (if any) fired. Don't commit — let the user edit and commit themselves (and remember the build-log is a separate repo, so a commit there doesn't touch the code repo).
