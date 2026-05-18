"""Tests for SYNAPSE CLI entry point and commands.

Verifies convergence criteria for TASK-008:
- All subcommands register and --help works
- init creates workspace dirs
- research/decision/review/workspace commands are callable
"""

import pytest

from synapse.cli.main import build_parser, main


class TestBuildParser:
    def test_parser_creates_successfully(self):
        parser = build_parser()
        assert parser.prog == "synapse"

    def test_no_command_shows_help(self):
        """No command → help text, returns 0."""
        code, _ = run_cli()
        assert code == 0


def run_cli(*args_str: str) -> tuple[int, str]:
    """Run CLI and capture output. Returns (exit_code, stdout)."""
    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        result = main(list(args_str))
    except SystemExit as e:
        result = e.code
    finally:
        sys.stdout = old_stdout
    return result, buffer.getvalue()


class TestInitHelp:
    def test_init_help(self):
        """synapse init --help should succeed."""
        code, out = run_cli("init", "--help")
        assert code == 0
        assert "Create a new SYNAPSE workspace with standard directories" in out

    def test_init_creates_workspace(self, tmp_path):
        """synapse init <path> creates workspace dirs."""
        ws_path = tmp_path / "test-ws"
        code, out = run_cli("init", str(ws_path))
        assert code == 0
        assert ws_path.exists()
        assert (ws_path / "synapse.yaml").exists()
        assert (ws_path / "decisions").is_dir()
        assert (ws_path / "watchlists").is_dir()


class TestResearchHelp:
    def test_research_help(self):
        """synapse research --help should succeed."""
        code, out = run_cli("research", "--help")
        assert code == 0
        assert "Research workflows" in out

    def test_research_daily_help(self):
        """synapse research daily --help should succeed."""
        code, out = run_cli("research", "daily", "--help")
        assert code == 0
        assert "Generate a fresh daily watchlist" in out

    def test_research_daily_runs(self):
        """synapse research daily runs with empty data."""
        code, out = run_cli("research", "daily")
        assert code == 0
        assert "Daily research for" in out


class TestDecisionHelp:
    def test_decision_help(self):
        """synapse decision --help should succeed."""
        code, out = run_cli("decision", "--help")
        assert code == 0
        assert "Record and manage buy/sell decisions" in out

    def test_decision_record_help(self):
        """synapse decision record --help should succeed."""
        code, out = run_cli("decision", "record", "--help")
        assert code == 0
        assert "Record a buy or sell decision with thesis and risk" in out

    def test_decision_record_runs(self):
        """synapse decision record runs with required args."""
        code, out = run_cli("decision", "record", "--symbol", "600519", "--type", "buy", "--thesis", "Test thesis")
        assert code == 0
        assert "Recorded buy decision for 600519" in out


class TestReviewHelp:
    def test_review_help(self):
        """synapse review --help should succeed."""
        code, out = run_cli("review", "--help")
        assert code == 0
        assert "Submit decision post-mortem reviews" in out

    def test_review_submit_help(self):
        """synapse review submit --help should succeed."""
        code, out = run_cli("review", "submit", "--help")
        assert code == 0
        assert "Submit a post-mortem review for a recorded decision" in out

    def test_review_submit_runs(self):
        """synapse review submit runs with required args."""
        code, out = run_cli("review", "submit", "--decision-id", "dec_test123", "--outcome", "thesis_confirmed")
        assert code == 0
        assert "Submitted review for dec_test123" in out


class TestWorkspaceHelp:
    def test_workspace_help(self):
        """synapse workspace --help should succeed."""
        code, out = run_cli("workspace", "--help")
        assert code == 0
        assert "List and switch between SYNAPSE workspaces" in out

    def test_workspace_list_help(self):
        """synapse workspace list --help should succeed."""
        code, out = run_cli("workspace", "list", "--help")
        assert code == 0
        assert "Show all workspaces found" in out

    def test_workspace_list_runs(self):
        """synapse workspace list runs (may be empty)."""
        code, out = run_cli("workspace", "list")
        assert code == 0
        assert "Workspaces" in out or "No workspaces found" in out

    def test_workspace_switch_help(self):
        """synapse workspace switch --help should succeed."""
        code, out = run_cli("workspace", "switch", "--help")
        assert code == 0
        assert "Set the active workspace by name" in out

    def test_workspace_switch_nonexistent(self):
        """synapse workspace switch with nonexistent name returns error."""
        code, out = run_cli("workspace", "switch", "nonexistent")
        assert code == 1
