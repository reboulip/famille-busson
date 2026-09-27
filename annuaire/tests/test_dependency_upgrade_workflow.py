"""Regression guards for the weekly dependency-upgrade workflow (#149). The workflow
was going red on every run: ruff (bumped past the develop-pinned version by `uv lock
--upgrade`) started flagging new style violations with no auto-fix step to clear them,
and separately the test step never installed gettext or compiled the translation
catalogs, so any translation-dependent test would fail once ruff was fixed. No YAML
test runner in this project for workflow files -- assert on source text, mirroring
test_carte_marker_cluster.py's approach for JS."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "dependency-upgrade.yml"
PRE_COMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"


def _workflow_content() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_ruff_auto_fix_runs_before_the_check_gates():
    content = _workflow_content()
    fix_pos = content.index("Ruff auto-fix")
    format_pos = content.index("- name: Ruff format\n")
    check_pos = content.index("- name: Ruff check\n")
    format_check_pos = content.index("Ruff format check")
    assert fix_pos < check_pos, "the auto-fix step must run before the check-only ruff gate"
    assert format_pos < format_check_pos, "ruff format must run before the format --check gate"


def test_unsafe_fixes_flag_is_never_used():
    content = _workflow_content()
    assert "unsafe-fixes" not in content
    assert "unsafe_fixes" not in content


def test_gettext_is_installed():
    content = _workflow_content()
    install_line = next(line for line in content.splitlines() if "tesseract-ocr-fra" in line)
    assert "gettext" in install_line


def test_compilemessages_runs_before_the_test_suite():
    content = _workflow_content()
    compile_pos = content.index("Compile message catalogs")
    pytest_pos = content.index("Run tests with coverage")
    assert compile_pos < pytest_pos


def test_pre_commit_ruff_hooks_run_through_uv_not_a_pinned_external_rev():
    content = PRE_COMMIT_CONFIG.read_text(encoding="utf-8")
    assert "ruff-pre-commit" not in content
    assert "uv run ruff check --fix" in content
    assert "uv run ruff format" in content
    # migrations must stay excluded from lint/format, same as pyproject.toml's
    # extend-exclude -- a bare `uv run ruff ...` entry (no --force-exclude) would
    # silently start linting/formatting migration files pre-commit passes explicitly.
    assert "--force-exclude" in content
