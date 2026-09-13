"""Guards for the restore drill infrastructure (9.3).

Same constraint as test_backup_script.py -- no docker/postgres available in CI
or the dev sandbox, so a real end-to-end restore cannot be executed here. Most
guards below are source-text checks. The production guard is the exception:
looks_like_production() runs -- and, when it trips, fails the script -- before
any docker command, so it CAN be exercised as a real subprocess without
docker/postgres. That's strictly stronger evidence than a regex against the
script text, so prefer it for anything touching this specific safety check.
"""

import re
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESTORE_SCRIPT = REPO_ROOT / "scripts" / "restore.sh"
RESTORE_COMPOSE = REPO_ROOT / "docker-compose.restore.yml"
RESTORE_DOC = REPO_ROOT / "docs" / "restore.md"


def _script_text() -> str:
    return RESTORE_SCRIPT.read_text(encoding="utf-8")


def test_the_script_exists_and_is_executable():
    assert RESTORE_SCRIPT.exists()
    assert RESTORE_SCRIPT.stat().st_mode & 0o111, "restore.sh must be executable (chmod +x)"


def test_the_script_uses_strict_mode():
    content = _script_text()
    assert content.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in content


def test_required_flags_are_supported():
    content = _script_text()
    for flag in ("--backup-path", "--compose-file", "--project", "--yes-i-mean-production"):
        assert flag in content


def test_the_drill_compose_file_is_the_default_target():
    content = _script_text()
    assert 'COMPOSE_FILE="docker-compose.restore.yml"' in content


def test_a_production_looking_target_is_refused_without_the_confirmation_flag():
    content = _script_text()
    assert "looks_like_production" in content
    assert "CONFIRM_PRODUCTION" in content
    # The refusal must actually gate execution -- not just exist as a dead function.
    assert re.search(r"if\s+looks_like_production.*CONFIRM_PRODUCTION", content)


def test_manifest_is_verified_before_touching_any_container():
    content = _script_text()
    verify_index = content.index("verifying manifest checksums")
    up_index = content.index("docker compose")
    assert verify_index < up_index, "manifest verification must happen before bringing up any container"


def test_pg_restore_uses_the_safe_flags():
    content = _script_text()
    assert "pg_restore" in content
    for flag in ("--clean", "--if-exists", "--no-owner", "--no-privileges"):
        assert flag in content


def test_the_restore_compose_file_uses_no_host_bind_mounts():
    content = RESTORE_COMPOSE.read_text(encoding="utf-8")
    assert "/srv/bubu" not in content, "the drill compose file must never mount real production data paths"


def test_the_restore_compose_file_matches_prods_postgres_version():
    content = RESTORE_COMPOSE.read_text(encoding="utf-8")
    assert "postgres:16-alpine" in content


def test_the_runbook_has_an_empty_drill_log_pending_a_real_run():
    content = RESTORE_DOC.read_text(encoding="utf-8")
    assert "Drill log" in content
    assert "none yet" in content


def _run_restore(compose_file: Path, project: str = "bubu-restore-drill") -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp:
        backup_path = Path(tmp)
        (backup_path / "manifest.json").write_text('{"manifest_version": 1, "artifacts": {}}')
        return subprocess.run(
            [
                "bash",
                str(RESTORE_SCRIPT),
                "--backup-path",
                str(backup_path),
                "--compose-file",
                str(compose_file),
                "--project",
                project,
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )


def test_guard_still_trips_against_a_templated_compose_body(tmp_path):
    # 16.6 parameterizes docker-compose.prod.yml's bind mounts as
    # ${DATA_ROOT:-/srv/bubu/data} -- the guard must still catch this shape, not
    # just the old bare literal.
    fixture = tmp_path / "templated-compose.yml"
    fixture.write_text(
        "services:\n  db:\n    volumes:\n      - ${DATA_ROOT:-/srv/bubu/data}/postgres:/var/lib/postgresql/data\n"
    )
    result = _run_restore(fixture)
    assert result.returncode != 0
    assert "looks like production" in result.stderr


def test_guard_does_not_trip_on_a_non_production_shaped_compose_file(tmp_path):
    fixture = tmp_path / "scratch-compose.yml"
    fixture.write_text("services:\n  db:\n    volumes:\n      - restore_scratch_data:/var/lib/postgresql/data\n")
    result = _run_restore(fixture, project="bubu-restore-drill")
    # Fails later for lack of docker/the compose file's other assumptions -- the
    # point here is only that it is NOT refused as looking like production.
    assert "looks like production" not in result.stderr
