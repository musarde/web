---
name: sunday-checkin
description: Populate the weekly Sunday check-in entry for the Musarde build log by aggregating the week's commits, new entries in build-log/decisions.md, daily build-log files, and current resume-bullet status against the sunday-checkin-template structure. Use this skill when the user says "sunday checkin," "weekly review," "fill in the sunday checkin," "weekly buildlog," or asks for a status summary of the past week's Musarde work. The output is saved to build-log/sunday-YYYY-MM-DD.md and covers what shipped, what slipped, decisions logged, mock-interview status, the continue/scale-back/pause read for the week, and next week's first task. Trigger only for Musarde weekly-review requests — not for general status updates or other repos.
---

# sunday-checkin

Generate a draft Sunday check-in for the Musarde build log. The check-in is for the user, not for an audience — the brief explicitly says "be honest with yourself; this file is for you, not a performance." Drafts that read like LinkedIn posts have failed.

## Inputs to gather

Run these in parallel before writing anything. Don't ask the user to feed you the data — pull it yourself.

1. **The week's commits.**
   ```
   git log --since="7 days ago" --pretty=format:"%h %ad %s" --date=short
   ```
   Group by day. Note any day with zero commits.

2. **New `build-log/decisions.md` entries from this week.**
   ```
   git log --since="7 days ago" -p -- build-log/decisions.md
   ```
   Extract the headings of any entries added in the last 7 days. Zero entries this week is itself a signal — call it out explicitly.

3. **Daily build-log files from the week.**
   List and read `build-log/YYYY-MM-DD.md` for each day in the past 7 days that exists. Missing days are also signal.

4. **Last week's "Next week's primary deliverable" and "Monday's first task."**
   Find the previous `build-log/sunday-*.md` file. Read sections 12 and 14. The current week's check-in audits against last week's commitments — without them you're writing in a vacuum.

5. **Current resume-bullet status.**
   Read `accountability-plan.md` §"Resume-bullet readiness." Note which v0.6 bullets are claimed-ready vs. in-progress. Cross-reference against what the commits and daily logs actually demonstrate.

6. **Mock-interview file from this week.**
   Look for `build-log/mock-interview-YYYY-MM-DD.md` dated within the past 7 days. If absent, the section 5 answer is "skipped" — note it.

## Output

Copy `build-log/sunday-checkin-template.md` to `build-log/sunday-YYYY-MM-DD.md` (today's date), then fill in what you can from the gathered inputs. **Leave fields you can't determine empty** rather than guessing — the user will fill them in.

You can fill these reliably:
- §2 "This week's primary deliverable was" — pull from last Sunday's section 12.
- §4 "What got added to `/build-log/decisions.md` this week" — list headings of entries added in the last 7 days. If zero, write "Zero entries this week — flag." (Per the template: zero is a flag.)
- §8 "What broke or surprised me" — pull from daily build-log "What broke or surprised me" sections.
- §10 "Resume-bullet readiness" — list bullets currently marked ready vs. in-progress in the accountability plan. Add a flag if a bullet claimed "ready" doesn't have demonstrable code/data behind it from the week's commits.
- §14 "Monday's first task" — leave empty unless the user has stated it; this is theirs to write.

You **cannot** fill these — leave blank with a `_[fill in]_` marker:
- §0 goal-stack honesty (Y/N self-assessment)
- §1 job-search numbers (only the user knows)
- §2 status (hit/partial/missed) — show evidence, let user judge
- §3 architecture defensibility check (the user has to whiteboard)
- §5 mock-interview reflection prose (read the mock-interview file if present and pull facts, but the "what I fumbled" is theirs)
- §6 hellointerview deep-dive
- §7 what I learned
- §9 risk pulse
- §11 decision queue
- §12 next week's primary deliverable
- §13 next week's interview-prep commitments

For §2 (status hit/partial/missed), provide **evidence** — the commits and daily logs that bear on whether the deliverable shipped — and let the user grade. Do not grade for them.

## Failure-mode signals (Part 2 of the template)

After filling, evaluate the Part 2 checkboxes against what you actually found:

- "Two consecutive Sundays of partial/missed" — read the previous Sunday file. If both this week and last show partial/missed, check the box.
- "Zero decisions-log entries when there should have been some" — if the week had substantial commits but zero decisions entries, flag it. "Should have been some" is a judgment call; raise it as a question if borderline.
- "Skipped mock interview without travel/illness" — if no mock-interview file and the user hasn't mentioned travel/illness, surface the question.
- The job-apps and gap-recurrence checks require user input; leave with the marker.

If two or more of the auto-detectable signals fire, **lead the response** with that flag, not with the routine summary. The template's whole point is to catch failure modes — surfacing them is the skill's job.

## Week 6 ship-or-pause checkpoint (Part 3)

Only fill out on Sun Jun 14 (Week 6) or any subsequent Sunday where the previous decision is being re-evaluated (re-evaluations no earlier than 2 weeks after the prior decision). Otherwise leave Part 3 entirely untouched. Check today's date against Jun 14 before deciding whether to expand this section.

## Voice and tone

The template is brutal on purpose. Match it: terse, no softening, no "great progress this week!" framing. If something slipped, say it slipped. If decisions log is empty, that's a flag — don't bury it in encouragement. The user's note in the template says this file is for them, not a performance, and "the discomfort is the point" appears multiple times. Lean into that.

## After drafting

Show the draft inline, then write it to `build-log/sunday-YYYY-MM-DD.md`. Tell the user which fields you left blank and which auto-detected signals (if any) fired. Don't commit — let the user edit and commit themselves.
