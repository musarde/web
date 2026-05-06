#!/usr/bin/env python3
"""PostToolUse hook: surface drift after edits to ../build-log/decisions.md.

When Claude edits the decisions log, parses the changed decision(s) and
scans consumer docs (CLAUDE.md, musarde-project.md, accountability-plan.md,
decision-checklist.md) for stale references to the rejected alternatives
or `TBD` markers near the decision's topic. Emits findings as
`additionalContext` so Claude's next turn can offer to update the docs.

PostToolUse hooks cannot block — the user's edit always lands. This hook
only adds context for the next turn.

Per CLAUDE.md: "flag mismatches; don't silently fix one without the
other." This script flags candidates only — it never edits.

Hook payload schema (stdin):
    {
      "session_id": "...",
      "cwd": "/abs/path/to/web",
      "hook_event_name": "PostToolUse",
      "tool_name": "Edit" | "Write" | "MultiEdit",
      "tool_input": {"file_path": "/abs/path/to/file", ...}
    }
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Words ignored when extracting topic keywords from a decision title.
TITLE_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "for", "on", "in", "to",
    "vs", "over", "via", "with", "no",
})

CONSUMER_DOC_RELATIVE_PATHS = (
    ("project", "CLAUDE.md"),
    ("build_log", "musarde-project.md"),
    ("build_log", "accountability-plan.md"),
    ("build_log", "decision-checklist.md"),
)


@dataclass
class Decision:
    """A single decision parsed from decisions.md."""

    date: str
    title: str
    topic_keywords: list[str]
    title_picked: str | None
    title_rejected: str | None
    bullet_alternatives: list[str]
    body_start_line: int  # 1-indexed, the H2 heading line
    body_end_line: int    # 1-indexed inclusive, last line of entry body


@dataclass
class DriftCandidate:
    """A line in a consumer doc that may be stale w.r.t. a decision."""

    file: Path
    line_number: int
    line_text: str
    reason: str


# ---------------------------------------------------------------------------
# Parsing decisions.md
# ---------------------------------------------------------------------------


HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2}): (.+)$")
CONSIDERED_RE = re.compile(r"^\*\*Considered:\*\*", re.IGNORECASE)
BOLD_FIELD_RE = re.compile(r"^\*\*[A-Za-z][A-Za-z ]*:\*\*")


def parse_decisions(text: str) -> list[Decision]:
    """Parse all decisions from the decisions.md text. Skips H2 headings
    inside code fences."""
    lines = text.splitlines()
    in_fence = False
    headings: list[tuple[int, str, str]] = []  # (line_idx, date, title)

    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            headings.append((i, m.group(1), m.group(2).strip()))

    decisions: list[Decision] = []
    for idx, (line_idx, date, title) in enumerate(headings):
        if idx + 1 < len(headings):
            end_line_idx = headings[idx + 1][0] - 1
        else:
            end_line_idx = len(lines) - 1
        body = lines[line_idx:end_line_idx + 1]

        topic_keywords = _extract_topic_keywords(title)
        title_picked, title_rejected = _parse_title_x_over_y(title)
        bullet_alternatives = _extract_considered_bullets(body)

        decisions.append(Decision(
            date=date,
            title=title,
            topic_keywords=topic_keywords,
            title_picked=title_picked,
            title_rejected=title_rejected,
            bullet_alternatives=bullet_alternatives,
            body_start_line=line_idx + 1,
            body_end_line=end_line_idx + 1,
        ))
    return decisions


def _extract_topic_keywords(title: str) -> list[str]:
    """Significant words from the part of the title before the em-dash."""
    topic = title.split("—", 1)[0].strip()
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", topic)
    return [w for w in words if w.lower() not in TITLE_STOPWORDS and len(w) > 1]


def _parse_title_x_over_y(title: str) -> tuple[str | None, str | None]:
    """Parse 'Topic — X over Y' (or 'X vs Y') into (X, Y)."""
    parts = title.split("—", 1)
    if len(parts) != 2:
        return (None, None)
    subtitle = parts[1].strip()
    m = re.match(r"(.+?)\s+(?:over|vs\.?)\s+(.+)$", subtitle, re.IGNORECASE)
    if not m:
        return (None, None)
    return (m.group(1).strip(), m.group(2).strip())


def _extract_considered_bullets(body: list[str]) -> list[str]:
    """Short-name alternatives from the **Considered:** bullet list.

    Bullet's "name" is text before the first em-dash or open-paren. Bullets
    without a clear short name (long-form sentences) are skipped.
    """
    in_considered = False
    names: list[str] = []
    for line in body:
        if CONSIDERED_RE.match(line):
            in_considered = True
            continue
        if not in_considered:
            continue
        if BOLD_FIELD_RE.match(line) and not CONSIDERED_RE.match(line):
            break
        if not line.startswith("- "):
            continue
        bullet = line[2:].strip()
        name = re.split(r"\s+—\s+|\s*\(", bullet, maxsplit=1)[0].strip()
        if "," in name or len(name.split()) > 4 or not name:
            continue
        names.append(name)
    return names


# ---------------------------------------------------------------------------
# Detecting which decisions changed (git diff)
# ---------------------------------------------------------------------------


HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def get_changed_line_ranges(file_path: Path) -> list[tuple[int, int]]:
    """Run `git diff HEAD --unified=0 -- <file>` from the file's repo and
    parse new-side line ranges. Returns [] on any failure (untracked file,
    no git, etc.)."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--unified=0", "--", file_path.name],
            cwd=str(file_path.parent),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if result.returncode != 0:
        return []

    ranges: list[tuple[int, int]] = []
    for line in result.stdout.splitlines():
        m = HUNK_RE.match(line)
        if not m:
            continue
        start = int(m.group(1))
        count = int(m.group(2)) if m.group(2) else 1
        if count == 0:
            continue  # pure deletion on the new side
        ranges.append((start, start + count - 1))
    return ranges


def select_changed_decisions(
    decisions: list[Decision],
    changed_ranges: list[tuple[int, int]],
) -> list[Decision]:
    """Decisions whose body line range overlaps a changed range. Falls back
    to [most recent by date] if there are no overlaps and we have changes,
    or if changes are unavailable but decisions exist."""
    if not decisions:
        return []
    matched = [
        d for d in decisions
        if _ranges_overlap((d.body_start_line, d.body_end_line), changed_ranges)
    ]
    if matched:
        return matched
    return [max(decisions, key=lambda d: d.date)]


def _ranges_overlap(
    span: tuple[int, int],
    ranges: list[tuple[int, int]],
) -> bool:
    s_start, s_end = span
    return any(r_start <= s_end and r_end >= s_start for r_start, r_end in ranges)


# ---------------------------------------------------------------------------
# Scanning consumer docs for drift
# ---------------------------------------------------------------------------


def find_drift(decision: Decision, doc_path: Path) -> list[DriftCandidate]:
    """Lines in doc_path that pair a topic keyword with either a rejected
    alternative or a TBD marker."""
    if not doc_path.exists():
        return []

    rejected_names = list(decision.bullet_alternatives)
    if decision.title_rejected:
        rejected_names.append(decision.title_rejected)
    picked_lower = {decision.title_picked.lower()} if decision.title_picked else set()
    rejected_names = [n for n in rejected_names if n.lower() not in picked_lower]
    # De-dupe preserving order.
    seen: set[str] = set()
    rejected_names = [n for n in rejected_names if not (n.lower() in seen or seen.add(n.lower()))]

    rejected_patterns = [
        re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
        for name in rejected_names
    ]
    topic_patterns = [
        re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        for kw in decision.topic_keywords
    ]
    tbd_pattern = re.compile(r"\bTBD\b", re.IGNORECASE)

    candidates: list[DriftCandidate] = []
    for line_idx, line in enumerate(doc_path.read_text().splitlines(), start=1):
        if not any(p.search(line) for p in topic_patterns):
            continue
        for pattern, name in zip(rejected_patterns, rejected_names, strict=True):
            if pattern.search(line):
                candidates.append(DriftCandidate(
                    file=doc_path,
                    line_number=line_idx,
                    line_text=line,
                    reason=f"rejected alternative '{name}' appears near topic",
                ))
        if tbd_pattern.search(line):
            candidates.append(DriftCandidate(
                file=doc_path,
                line_number=line_idx,
                line_text=line,
                reason="TBD marker near decision topic",
            ))
    return candidates


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------


def render_report(
    decisions: list[Decision],
    candidates_by_decision: dict[str, list[DriftCandidate]],
    project_root: Path,
) -> str:
    sections: list[str] = []
    sections.append(
        "Decisions-log drift check fired after edit to "
        "../build-log/decisions.md.\n"
    )
    for decision in decisions:
        cands = candidates_by_decision.get(decision.title, [])
        if not cands:
            continue
        sections.append(f"\n### Decision: {decision.title}\n")
        for c in cands:
            rel = _relative_for_display(c.file, project_root)
            sections.append(
                f"- {rel}:{c.line_number} — {c.reason}\n"
                f"  > {c.line_text.strip()}\n"
            )
    sections.append(
        "\nOffer the user to update these. Do not silently edit — show "
        "proposed diffs first, per the CLAUDE.md guardrail "
        '"flag mismatches; don\'t silently fix one without the other."'
    )
    return "".join(sections)


def _relative_for_display(file: Path, project_root: Path) -> str:
    try:
        return str(file.relative_to(project_root))
    except ValueError:
        try:
            return "../" + str(file.relative_to(project_root.parent))
        except ValueError:
            return str(file)


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def resolve_consumer_docs(project_root: Path) -> list[Path]:
    build_log = project_root.parent / "build-log"
    out: list[Path] = []
    for kind, name in CONSUMER_DOC_RELATIVE_PATHS:
        if kind == "project":
            out.append(project_root / name)
        else:
            out.append(build_log / name)
    return out


def resolve_project_root(payload_cwd: str | None) -> Path:
    """Resolve the Musarde web/ project root.

    Priority:
    1. $CLAUDE_PROJECT_DIR env var (set by Claude Code, points at the
       project regardless of which working dir an edit happened in).
    2. Script-relative: this file lives at <project_root>/.claude/hooks/...
    3. payload `cwd` as a last resort (unreliable when the edited file is
       in an additional working directory like ../build-log).
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    script_root = Path(__file__).resolve().parents[2]
    if (script_root / "CLAUDE.md").exists():
        return script_root
    if payload_cwd:
        return Path(payload_cwd).resolve()
    return script_root


def run_hook(payload: dict) -> str | None:
    """Pure-function core. Returns the additionalContext string, or None
    if no report should be emitted."""
    file_path = payload.get("tool_input", {}).get("file_path")
    if not file_path:
        return None

    project_root = resolve_project_root(payload.get("cwd"))
    edited = Path(file_path).resolve()
    decisions_md = (project_root.parent / "build-log" / "decisions.md").resolve()

    if edited != decisions_md or not decisions_md.exists():
        return None

    decisions = parse_decisions(decisions_md.read_text())
    if not decisions:
        return None

    changed_ranges = get_changed_line_ranges(decisions_md)
    targets = select_changed_decisions(decisions, changed_ranges)
    if not targets:
        return None

    consumer_docs = resolve_consumer_docs(project_root)
    candidates_by_decision: dict[str, list[DriftCandidate]] = {}
    for decision in targets:
        cands: list[DriftCandidate] = []
        for doc in consumer_docs:
            cands.extend(find_drift(decision, doc))
        if cands:
            candidates_by_decision[decision.title] = cands

    if not candidates_by_decision:
        return None

    return render_report(targets, candidates_by_decision, project_root)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    try:
        report = run_hook(payload)
    except Exception as exc:
        # PostToolUse can't block, but a hook crash surfaces a noisy error
        # in the transcript on every unrelated edit. Swallow + log to stderr.
        print(f"decisions-drift hook error: {exc}", file=sys.stderr)
        return 0

    if report is None:
        return 0

    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": report,
        }
    }, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
