"""Guard against Busson/bubu/reboulip branding literals leaking into code a fresh,
differently-branded deployment would actually run or see (16.7). Source-text check,
same approach as test_carte_marker_cluster.py/test_backup_script.py.

This is NOT a "no such string anywhere in the repo" check -- that would also flag
harmless things like a test fixture person named "Busson" (this codebase's shared
`person`/`other_person` fixtures use it as an ordinary, realistic surname; a live
site's actual data is never affected by that choice) or a static design mockup.
The allowlist below is deliberately reviewed and commented, not a blanket exclusion.
"""

import re
from pathlib import Path

from django.conf import settings

BANNED = re.compile(r"busson|bubu|reboulip", re.IGNORECASE)

# Exact repo-relative paths, individually justified -- see comments.
ALLOWLISTED_FILES = {
    # Frozen historical record of already-shipped work; never rewritten.
    "docs/ROADMAP_ARCHIVE.md",
    # References this project's own history/conventions by name (e.g. "Famille
    # Busson" as the worked example throughout Phase 15/16's own commit history);
    # not code a deployment runs.
    "CLAUDE.md",
    "ROADMAP.md",
    # Docs-site metadata (title, repo link) -- only matters if a forking family
    # also republishes the mkdocs site under this same config; a real fork edits
    # this file directly, same as it edits pyproject.toml's own name.
    "mkdocs.yml",
    # .env.example doubles as this deployment's actual VPS .env checklist (see its
    # own header comment) -- it deliberately keeps real current values, not
    # placeholders, matching every other var in the file (ALLOWED_HOSTS,
    # POSTGRES_DB, etc.). A fork copies and edits it, same as any other var.
    ".env.example",
    # Inherently deployment-specific CI/CD wiring (SSH targets, GHCR image name)
    # -- cannot be env-templated (GitHub Actions secrets/config, not runtime
    # settings). A fork edits this workflow file directly; documented as a
    # required manual step in docs/installation.md.
    ".github/workflows/build-and-deploy.yml",
    # Scratch/drill compose target for the restore runbook (docs/restore.md) --
    # its POSTGRES_DB/USER already fall through the same env vars
    # docker-compose.prod.yml uses; the bubu_* values are just its own literal
    # defaults, matching .env.example's convention.
    "docker-compose.restore.yml",
    # Historical migration: seeds "Famille Busson" ONLY when Account rows already
    # exist (i.e. only on this deployment's own pre-existing database) --
    # deliberately guarded, see the migration's own docstring. A fresh checkout's
    # test/dev database never runs this branch.
    "annuaire/migrations/0023_siteconfig_seed.py",
    # This session's own dev tooling skill directory name.
    ".gitignore",
    # Repo identity (title, GitHub Pages URL) -- deliberately not renamed, same as
    # 16.4's decision to rename the Python package but not the git repo itself. A
    # fork renames its own repo and this file follows.
    "README.md",
    # docker-compose.prod.yml's ${APP_IMAGE:-ghcr.io/reboulip/famille-busson:latest}
    # keeps a real current default, same convention as .env.example.
    "docker-compose.prod.yml",
    # Comments illustrating the real VPS path convention, matching .env.example.
    "scripts/backup.sh",
    "scripts/restore.sh",
    # Dev-only sample data: an example person surname and a sample preview
    # location string, matching the test-fixture convention above -- never
    # reaches a real deployment's data.
    "annuaire/management/commands/populate_dev_data.py",
    "annuaire/management/commands/preview_emails.py",
    # Docstring example demonstrating GEDCOM name-parsing syntax ("Jean /Busson/"
    # -> ...), an arbitrary example surname like the test fixtures above.
    "genealogy/gedcom/importer.py",
}

# Path prefixes, same rationale grouped together.
ALLOWLISTED_PREFIXES = (
    # Test fixtures across every app use "Busson" as an ordinary example person
    # surname (from annuaire/tests/conftest.py's shared `person`/`other_person`
    # fixtures) or as arbitrary search/tag test data -- not branding.
    "annuaire/tests/",
    "publications/tests/",
    "documents/tests/",
    "photos/tests/",
    "events/tests/",
    "genealogy/tests/",
    # Static design-reference mockups -- never imported/rendered by the app, no
    # test reads them (see CLAUDE.md's Documentation section).
    "design/",
    # This session's own dev tooling config -- not part of the shipped app.
    ".claude/",
    # Historical migrations are frozen; the data they migrate (e.g. an existing
    # "Busson connection" Tag row's name) is real prior content, not a hardcoded
    # default a fresh install would inherit.
    "publications/migrations/",
    "annuaire/migrations/",
    # Developer/operator-facing docs describe this deployment's own real setup
    # (VPS paths, GitHub Pages URL, etc.), matching .env.example's convention --
    # not runtime app behaviour an end user of a live deployment sees. A fork
    # edits these same pages to describe their own instance. docs/installation.md
    # (16.6's actual reusability deliverable) is itself already fully generic.
    "docs/",
)

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "staticfiles",
    "media",
    "site",
    "htmlcov",
    ".pytest_cache",
}
# Top-level only (collectstatic's gitignored output dir) -- annuaire/static/,
# publications/static/ etc. are real source and must still be scanned.
EXCLUDE_TOP_LEVEL_DIRS = {"static"}
# Gitignored build/test artifacts.
EXCLUDE_FILES = {"test-report.html"}
EXCLUDE_SUFFIXES = {".mo", ".pyc", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".sqlite3"}


def test_no_residual_branding_outside_the_allowlist():
    base = Path(settings.BASE_DIR)
    offenders = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(base).parts
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        if rel_parts[0] in EXCLUDE_TOP_LEVEL_DIRS:
            continue
        if path.suffix in EXCLUDE_SUFFIXES:
            continue
        if path.name in EXCLUDE_FILES:
            continue
        rel = path.relative_to(base).as_posix()
        if rel in ALLOWLISTED_FILES or rel.startswith(ALLOWLISTED_PREFIXES):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if BANNED.search(text):
            offenders.append(rel)

    assert not offenders, (
        "residual branding literal ('busson'/'bubu'/'reboulip') found outside the "
        f"reviewed allowlist: {sorted(offenders)}"
    )
