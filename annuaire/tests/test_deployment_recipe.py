"""Guards for the templated deployment recipe (16.6)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.prod.yml"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# The only vars docker-compose.prod.yml itself interpolates via ${...} -- everything
# else in .env.example is Django-only, passed through unparsed via env_file:.
KNOWN_COMPOSE_VARS = {
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "CACHE_URL",
    "QUEUE_URL",
    "DATA_ROOT",
    "APP_IMAGE",
    "WEB_PORT",
}


def _compose_referenced_vars() -> set[str]:
    content = COMPOSE_FILE.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"\$\{([A-Z_][A-Z0-9_]*)(?::-[^}]*)?\}", content)}


def _env_example_vars() -> set[str]:
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"^([A-Z_][A-Z0-9_]*)=", content, re.MULTILINE)}


def test_every_var_the_compose_file_references_is_declared_in_env_example():
    referenced = _compose_referenced_vars()
    declared = _env_example_vars()
    missing = referenced - declared
    assert not missing, f"docker-compose.prod.yml reads {missing} but .env.example never declares them"


def test_every_known_compose_var_in_env_example_is_referenced_by_the_compose_file():
    declared = _env_example_vars() & KNOWN_COMPOSE_VARS
    referenced = _compose_referenced_vars()
    unused = declared - referenced
    assert not unused, f".env.example declares {unused} but docker-compose.prod.yml never reads them"


def test_data_root_default_stays_the_current_production_value():
    # The literal /srv/bubu/data must survive inside the ${DATA_ROOT:-...} default --
    # scripts/restore.sh's production guard greps for a /srv/ path (see
    # test_restore_script.py), and losing this default silently defeats that guard.
    content = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "${DATA_ROOT:-/srv/bubu/data}" in content
