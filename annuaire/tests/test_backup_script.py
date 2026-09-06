"""Guards for the automated backup script (9.2).

There is no docker/postgres/rclone available in CI or the dev sandbox, so
scripts/backup.sh cannot be executed here -- these are source-text checks only,
same approach as test_carte_marker_cluster.py for JS. They guard against the
kind of drift that's easy to introduce without noticing: a var read by the
script but never documented in .env.example, or vice versa.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKUP_SCRIPT = REPO_ROOT / "scripts" / "backup.sh"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
DEPLOYMENT_DOC = REPO_ROOT / "docs" / "deployment.md"


def _script_text() -> str:
    return BACKUP_SCRIPT.read_text(encoding="utf-8")


def _env_example_vars() -> set[str]:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    return {match.group(1) for match in re.finditer(r"^([A-Z_][A-Z0-9_]*)=", text, re.MULTILINE)}


def test_the_script_exists_and_is_executable():
    assert BACKUP_SCRIPT.exists()
    assert BACKUP_SCRIPT.stat().st_mode & 0o111, "backup.sh must be executable (chmod +x)"


def test_the_script_uses_strict_mode():
    content = _script_text()
    assert content.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in content


def test_every_backup_var_the_script_reads_is_declared_in_env_example():
    content = _script_text()
    referenced = {match.group(1) for match in re.finditer(r"\$\{?(BACKUP_[A-Z0-9_]*)(?::-[^}]*)?\}?", content)}
    declared = _env_example_vars()
    missing = referenced - declared
    assert not missing, f"scripts/backup.sh reads {missing} but .env.example never declares them"


def test_every_backup_var_in_env_example_is_referenced_by_the_script():
    content = _script_text()
    declared = {var for var in _env_example_vars() if var.startswith("BACKUP_")}
    referenced = {match.group(1) for match in re.finditer(r"\$\{?(BACKUP_[A-Z0-9_]*)(?::-[^}]*)?\}?", content)}
    unused = declared - referenced
    assert not unused, f".env.example declares {unused} but scripts/backup.sh never reads them"


def test_tar_failure_handling_treats_exit_1_as_a_warning_not_fatal():
    # "file changed as we read it" (tar exit 1) is near-certain on a live media/
    # tree and must not abort the whole backup -- only exit codes >= 2 are fatal.
    content = _script_text()
    assert '"$tar_exit" -ge 2' in content
    assert '"$tar_exit" -eq 1' in content


def test_preflight_checks_free_space_before_writing_anything():
    content = _script_text()
    dry_run_index = content.index("DRY_RUN")
    preflight_index = content.index("AVAILABLE_KB")
    dump_index = content.index("pg_dump")
    assert preflight_index < dump_index, "the free-space check must run before the database dump"
    assert dry_run_index < preflight_index


def test_off_site_sync_never_deletes_the_remote_copy():
    # A plain `rclone sync` mirrors the local tree onto the remote -- a local bug
    # or an aggressive local prune would then delete the off-site copy too. Only
    # `rclone copy`/`rclone purge` (an explicit, separately-gated prune step) are
    # allowed here.
    content = _script_text()
    assert "rclone sync" not in content
    assert "rclone copy" in content


def test_manifest_has_a_version_field_for_future_schema_changes():
    content = _script_text()
    assert '"manifest_version": 1' in content


def test_the_documented_cron_entry_points_at_the_shipped_script_path():
    content = DEPLOYMENT_DOC.read_text(encoding="utf-8")
    assert "bash scripts/backup.sh" in content


def test_the_deploy_workflow_ships_the_scripts_directory():
    workflow = (REPO_ROOT / ".github" / "workflows" / "build-and-deploy.yml").read_text(encoding="utf-8")
    assert "scripts" in workflow
