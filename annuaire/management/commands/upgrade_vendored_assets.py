"""Upgrade vendored front-end assets (annuaire/static/vendor/) to their latest
stable npm-published version.

Usage (from the repo root):
    uv run python manage.py upgrade_vendored_assets
    uv run python manage.py upgrade_vendored_assets --check-only
    uv run python manage.py upgrade_vendored_assets --summary-file /tmp/summary.md

Reads annuaire/static/vendor/manifest.json, which lists each vendored library's npm
package name, currently-pinned version, and which files (npm package path -> local
file) make up the vendored copy. For each library: looks up the latest version on the
public npm registry, and if newer than the pinned one, downloads every mapped file from
jsdelivr (https://cdn.jsdelivr.net/npm/<pkg>@<version>/<path>, which mirrors any
published npm package's files without needing node/npm installed) and rewrites the
manifest's pinned version.

Run weekly by .github/workflows/dependency-upgrade.yml, ahead of the test suite --
"latest from npm" is not vetted against this project before download, so a green test
run afterwards is what actually gates whether the upgrade ships, same as any other
dependency bump.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

HELP_TEXT = __doc__ or ""

NPM_REGISTRY_LATEST = "https://registry.npmjs.org/{package}/latest"
JSDELIVR_FILE = "https://cdn.jsdelivr.net/npm/{package}@{version}/{src}"
REQUEST_TIMEOUT_SECONDS = 30


def get_manifest_path() -> Path:
    # Resolved at call time (not import time) so tests can override settings.BASE_DIR.
    return Path(settings.BASE_DIR) / "annuaire" / "static" / "vendor" / "manifest.json"


def get_vendor_root() -> Path:
    return Path(settings.BASE_DIR) / "annuaire" / "static" / "vendor"


def fetch_latest_version(package: str) -> str:
    response = requests.get(NPM_REGISTRY_LATEST.format(package=package), timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()["version"]


def fetch_file(package: str, version: str, src: str) -> bytes:
    url = JSDELIVR_FILE.format(package=package, version=version, src=src)
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.content


class Command(BaseCommand):
    help = HELP_TEXT

    def add_arguments(self, parser):
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="Ne rien télécharger : seulement lister les bibliothèques dont une nouvelle version est disponible.",
        )
        parser.add_argument(
            "--summary-file",
            type=str,
            default=None,
            help="Écrit un résumé Markdown des mises à jour effectuées dans ce fichier "
            "(utilisé par la CI pour le corps de la pull request).",
        )

    def handle(self, *args, **options):
        manifest_path = get_manifest_path()
        try:
            manifest = json.loads(manifest_path.read_text())
        except FileNotFoundError as exc:
            raise CommandError(f"Manifeste introuvable : {manifest_path}") from exc

        check_only = options["check_only"]
        upgraded = []

        for key, entry in manifest.items():
            if key.startswith("_"):
                continue

            package = entry["package"]
            current_version = entry["version"]
            latest_version = fetch_latest_version(package)

            if latest_version == current_version:
                self.stdout.write(f"{package} : déjà à jour ({current_version}).")
                continue

            if check_only:
                self.stdout.write(f"{package} : {current_version} -> {latest_version} disponible.")
                upgraded.append((package, current_version, latest_version))
                continue

            self.stdout.write(f"{package} : {current_version} -> {latest_version}, téléchargement...")
            dest_dir = get_vendor_root() / entry["dir"]
            for file_entry in entry["files"]:
                content = fetch_file(package, latest_version, file_entry["src"])
                dest_path = dest_dir / file_entry["dest"]
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(content)

            entry["version"] = latest_version
            upgraded.append((package, current_version, latest_version))

        if not check_only and upgraded:
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

        if not upgraded:
            self.stdout.write("Aucune bibliothèque vendorisée à mettre à jour.")

        summary_file = options["summary_file"]
        if summary_file:
            lines = [f"- `{package}`: {old} → {new}" for package, old, new in upgraded]
            Path(summary_file).write_text("\n".join(lines) + ("\n" if lines else ""))
