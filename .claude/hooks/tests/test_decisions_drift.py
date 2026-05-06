"""Tests for `.claude.hooks.decisions_drift`.

Three layers:
- TestParseDecisions / TestTitleHelpers / TestConsideredBullets — pure
  parser tests against the small fixture in fixtures/decisions_sample.md.
- TestRangeOverlap / TestSelectChangedDecisions — diff-driven selection
  logic, no git involved.
- TestFindDrift / TestRunHook — drift scanner and end-to-end hook
  contract, both against fixtures.

Run from the project root:
    python -m pytest .claude/hooks/tests/ -v
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

# decisions_drift.py lives outside any importable package (it's a hook
# script under .claude/hooks/, and `.claude` isn't a valid module name).
# Load it directly.
HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = HOOKS_DIR / "decisions_drift.py"
spec = importlib.util.spec_from_file_location("decisions_drift", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
decisions_drift = importlib.util.module_from_spec(spec)
sys.modules["decisions_drift"] = decisions_drift
spec.loader.exec_module(decisions_drift)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_DECISIONS = FIXTURES_DIR / "decisions_sample.md"
CLAUDE_DRIFT = FIXTURES_DIR / "CLAUDE_drift.md"
PROJECT_CLEAN = FIXTURES_DIR / "project_clean.md"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestParseDecisions:
    def test_parses_three_entries_skipping_template_in_code_fence(self):
        decisions = decisions_drift.parse_decisions(SAMPLE_DECISIONS.read_text())
        # The template inside the ``` fence at the top must NOT be parsed
        # as a real decision, so we expect exactly the three real entries.
        titles = [d.title for d in decisions]
        assert titles == [
            "Postgres host — Neon over Supabase",
            "Postgres version — 17 over 18",
            "Decision filter — workload over resume",
        ]

    def test_dates_parsed(self):
        decisions = decisions_drift.parse_decisions(SAMPLE_DECISIONS.read_text())
        assert [d.date for d in decisions] == ["2026-04-30", "2026-05-01", "2026-05-02"]

    def test_body_line_ranges_are_contiguous_and_cover_file(self):
        text = SAMPLE_DECISIONS.read_text()
        decisions = decisions_drift.parse_decisions(text)
        for prev, curr in zip(decisions, decisions[1:], strict=False):
            assert prev.body_end_line < curr.body_start_line
        total_lines = len(text.splitlines())
        assert decisions[-1].body_end_line == total_lines

    def test_empty_input_returns_no_decisions(self):
        assert decisions_drift.parse_decisions("") == []

    def test_input_with_no_real_headings_returns_no_decisions(self):
        text = "# Just a doc\n\nNo H2 date headings here.\n"
        assert decisions_drift.parse_decisions(text) == []


class TestTitleHelpers:
    def test_x_over_y_subtitle(self):
        picked, rejected = decisions_drift._parse_title_x_over_y(
            "Postgres host — Neon over Supabase"
        )
        assert picked == "Neon"
        assert rejected == "Supabase"

    def test_x_vs_y_subtitle(self):
        picked, rejected = decisions_drift._parse_title_x_over_y("Foo — A vs B")
        assert picked == "A"
        assert rejected == "B"

    def test_subtitle_without_pattern_returns_none(self):
        picked, rejected = decisions_drift._parse_title_x_over_y(
            "Neon region — AWS us-west-2"
        )
        assert picked is None and rejected is None

    def test_title_with_no_em_dash_returns_none(self):
        picked, rejected = decisions_drift._parse_title_x_over_y(
            "Schema PK strategy and identity columns"
        )
        assert picked is None and rejected is None

    def test_topic_keywords_strip_stopwords_and_subtitle(self):
        kws = decisions_drift._extract_topic_keywords(
            "Postgres host — Neon over Supabase"
        )
        assert "Postgres" in kws
        assert "host" in kws
        assert "Neon" not in kws
        assert "Supabase" not in kws

    def test_topic_keywords_drop_short_and_stopword_tokens(self):
        kws = decisions_drift._extract_topic_keywords("On the database — A over B")
        assert kws == ["database"]


class TestConsideredBullets:
    def test_extracts_short_names_before_em_dash(self):
        decisions = decisions_drift.parse_decisions(SAMPLE_DECISIONS.read_text())
        host = decisions[0]
        assert "Supabase" in host.bullet_alternatives
        assert "Neon" in host.bullet_alternatives

    def test_long_form_bullets_yield_no_short_names(self):
        decisions = decisions_drift.parse_decisions(SAMPLE_DECISIONS.read_text())
        df = decisions[2]
        assert df.bullet_alternatives == []


# ---------------------------------------------------------------------------
# Diff range parsing & selection
# ---------------------------------------------------------------------------


class TestRangeOverlap:
    @pytest.mark.parametrize("span,ranges,expected", [
        ((10, 20), [(15, 18)], True),
        ((10, 20), [(5, 12)], True),
        ((10, 20), [(18, 25)], True),
        ((10, 20), [(5, 25)], True),
        ((10, 20), [(1, 9)], False),
        ((10, 20), [(21, 30)], False),
        ((10, 20), [], False),
        ((10, 20), [(1, 5), (25, 30), (12, 14)], True),
    ])
    def test_overlap(self, span, ranges, expected):
        assert decisions_drift._ranges_overlap(span, ranges) is expected


class TestSelectChangedDecisions:
    def test_changes_overlapping_a_decision_select_only_that_decision(self):
        decisions = decisions_drift.parse_decisions(SAMPLE_DECISIONS.read_text())
        second = decisions[1]
        mid = (second.body_start_line + second.body_end_line) // 2
        result = decisions_drift.select_changed_decisions(decisions, [(mid, mid)])
        assert [d.title for d in result] == [second.title]

    def test_no_overlapping_changes_falls_back_to_most_recent(self):
        decisions = decisions_drift.parse_decisions(SAMPLE_DECISIONS.read_text())
        result = decisions_drift.select_changed_decisions(decisions, [(99999, 99999)])
        assert len(result) == 1
        assert result[0].date == "2026-05-02"

    def test_empty_changes_falls_back_to_most_recent(self):
        decisions = decisions_drift.parse_decisions(SAMPLE_DECISIONS.read_text())
        result = decisions_drift.select_changed_decisions(decisions, [])
        assert len(result) == 1
        assert result[0].date == "2026-05-02"

    def test_no_decisions_returns_empty(self):
        assert decisions_drift.select_changed_decisions([], [(1, 5)]) == []


class TestHunkParsing:
    def test_parses_added_range(self):
        diff = (
            "diff --git a/file b/file\n"
            "@@ -10,0 +11,3 @@\n"
            "+added line 1\n"
            "+added line 2\n"
            "+added line 3\n"
        )
        ranges: list[tuple[int, int]] = []
        for line in diff.splitlines():
            m = decisions_drift.HUNK_RE.match(line)
            if not m:
                continue
            start = int(m.group(1))
            count = int(m.group(2)) if m.group(2) else 1
            if count == 0:
                continue
            ranges.append((start, start + count - 1))
        assert ranges == [(11, 13)]

    def test_pure_deletion_yields_no_range(self):
        diff = "@@ -10,3 +9,0 @@\n"
        for line in diff.splitlines():
            m = decisions_drift.HUNK_RE.match(line)
            assert m is not None
            count = int(m.group(2)) if m.group(2) else 1
            assert count == 0


# ---------------------------------------------------------------------------
# Drift scanner
# ---------------------------------------------------------------------------


class TestFindDrift:
    @pytest.fixture
    def neon_decision(self):
        return decisions_drift.parse_decisions(SAMPLE_DECISIONS.read_text())[0]

    def test_flags_rejected_alt_and_tbd_on_topic_line(self, neon_decision):
        cands = decisions_drift.find_drift(neon_decision, CLAUDE_DRIFT)
        line_numbers = {c.line_number for c in cands}
        assert 5 in line_numbers
        reasons = {(c.line_number, c.reason) for c in cands}
        assert any(ln == 5 and "Supabase" in reason for ln, reason in reasons)
        assert any(ln == 5 and "TBD" in reason for ln, reason in reasons)

    def test_does_not_flag_rejected_alt_without_topic_keyword(self, neon_decision):
        """The 'Supabase auth integration' line in CLAUDE_drift.md has no
        Postgres/host topic keyword — must not be flagged."""
        cands = decisions_drift.find_drift(neon_decision, CLAUDE_DRIFT)
        # Find the Supabase-auth line dynamically so the test isn't tied
        # to a brittle line number.
        for line_idx, line in enumerate(CLAUDE_DRIFT.read_text().splitlines(), 1):
            if "Supabase auth" in line:
                assert line_idx not in {c.line_number for c in cands}
                break
        else:
            pytest.fail("fixture missing expected 'Supabase auth' line")

    def test_does_not_flag_tbd_without_topic_keyword(self, neon_decision):
        """The 'retrieval reranker is TBD' line has TBD but no
        Postgres/host topic keyword — must not be flagged."""
        cands = decisions_drift.find_drift(neon_decision, CLAUDE_DRIFT)
        for line_idx, line in enumerate(CLAUDE_DRIFT.read_text().splitlines(), 1):
            if "retrieval reranker" in line:
                assert line_idx not in {c.line_number for c in cands}
                break
        else:
            pytest.fail("fixture missing expected 'retrieval reranker' line")

    def test_clean_doc_yields_no_candidates(self, neon_decision):
        cands = decisions_drift.find_drift(neon_decision, PROJECT_CLEAN)
        assert cands == []

    def test_missing_doc_yields_no_candidates(self, neon_decision, tmp_path):
        cands = decisions_drift.find_drift(neon_decision, tmp_path / "missing.md")
        assert cands == []


# ---------------------------------------------------------------------------
# End-to-end run_hook
# ---------------------------------------------------------------------------


def _build_layout(tmp_path: Path, *, drift_in_claude: bool = True) -> Path:
    """Build the web/ + build-log/ sibling layout the hook expects.
    Returns the project_root (web/) path."""
    project_root = tmp_path / "web"
    build_log = tmp_path / "build-log"
    project_root.mkdir()
    build_log.mkdir()
    shutil.copy(SAMPLE_DECISIONS, build_log / "decisions.md")
    src_claude = CLAUDE_DRIFT if drift_in_claude else PROJECT_CLEAN
    shutil.copy(src_claude, project_root / "CLAUDE.md")
    return project_root


class TestRunHook:
    def test_non_decisions_edit_returns_none(self, tmp_path):
        project_root = _build_layout(tmp_path)
        payload = {
            "tool_input": {"file_path": str(project_root / "CLAUDE.md")},
            "cwd": str(project_root),
        }
        assert decisions_drift.run_hook(payload) is None

    def test_fallback_on_latest_entry_with_no_drift_returns_none(self, tmp_path):
        """The fixture's most recent entry ('Decision filter — workload
        over resume') has long-form bullets and no rejected alternatives
        matching consumer-doc lines. With no real diff (tmp file isn't in
        git), the fallback selects only that entry → no candidates → None.
        Confirms the hook stays silent on edits that don't introduce drift."""
        project_root = _build_layout(tmp_path)
        decisions_md = project_root.parent / "build-log" / "decisions.md"
        payload = {
            "tool_input": {"file_path": str(decisions_md)},
            "cwd": str(project_root),
        }
        decisions = decisions_drift.parse_decisions(decisions_md.read_text())
        fallback = decisions_drift.select_changed_decisions(decisions, [])
        assert fallback[0].title == "Decision filter — workload over resume"
        assert decisions_drift.run_hook(payload) is None

    def test_targeted_neon_change_emits_drift_for_claude_md(self, tmp_path):
        """Exercise the full drift path by simulating a diff range that
        overlaps the Neon entry. Calls the lower-level pieces directly so
        we don't need a real git repo to drive the diff."""
        project_root = _build_layout(tmp_path, drift_in_claude=True)
        decisions_md = project_root.parent / "build-log" / "decisions.md"
        decisions = decisions_drift.parse_decisions(decisions_md.read_text())
        neon = decisions[0]
        ranges = [(neon.body_start_line, neon.body_end_line)]
        targets = decisions_drift.select_changed_decisions(decisions, ranges)
        assert [d.title for d in targets] == [neon.title]

        consumer_docs = decisions_drift.resolve_consumer_docs(project_root)
        all_cands = []
        for d in targets:
            for doc in consumer_docs:
                all_cands.extend(decisions_drift.find_drift(d, doc))
        assert any(
            "CLAUDE.md" in str(c.file) for c in all_cands
        ), "expected drift candidate in CLAUDE.md"

    def test_missing_build_log_dir_returns_none(self, tmp_path):
        project_root = tmp_path / "web"
        project_root.mkdir()
        (project_root / "CLAUDE.md").write_text("# placeholder\n")
        payload = {
            "tool_input": {
                "file_path": str(tmp_path / "build-log" / "decisions.md"),
            },
            "cwd": str(project_root),
        }
        assert decisions_drift.run_hook(payload) is None

    def test_malformed_payload_returns_none(self):
        assert decisions_drift.run_hook({}) is None
        assert decisions_drift.run_hook({"cwd": "/tmp"}) is None
        assert decisions_drift.run_hook({"tool_input": {}}) is None

    def test_resolves_project_root_from_env_var_overriding_cwd(
        self, tmp_path, monkeypatch,
    ):
        """Regression: when Claude edits a file in build-log/, the hook's
        payload `cwd` may point to build-log, not web/. The hook must still
        resolve the consumer-doc layout correctly via $CLAUDE_PROJECT_DIR
        rather than treating build-log as the project root."""
        project_root = _build_layout(tmp_path)
        decisions_md = project_root.parent / "build-log" / "decisions.md"

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_root))

        # Simulate the misleading cwd Claude Code passes when editing in
        # build-log: cwd is build-log, not web/.
        payload = {
            "tool_input": {"file_path": str(decisions_md)},
            "cwd": str(project_root.parent / "build-log"),
        }
        # Drive the path that exercises drift (target the Neon entry).
        decisions = decisions_drift.parse_decisions(decisions_md.read_text())
        neon = decisions[0]
        consumer_docs = decisions_drift.resolve_consumer_docs(
            decisions_drift.resolve_project_root(payload["cwd"])
        )
        # The web/CLAUDE.md fixture must be in the resolved consumer-doc
        # list (it would NOT be if project_root was mistakenly build-log).
        claude_md_paths = [d for d in consumer_docs if d.name == "CLAUDE.md"]
        assert len(claude_md_paths) == 1
        assert claude_md_paths[0] == project_root / "CLAUDE.md"

        # And drift on the Neon entry hits CLAUDE.md.
        cands = decisions_drift.find_drift(neon, claude_md_paths[0])
        assert any("Supabase" in c.reason for c in cands)
