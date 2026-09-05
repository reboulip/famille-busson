import json
from io import StringIO

import pytest
from django.core.management import call_command

from annuaire.management.commands.upgrade_vendored_assets import get_manifest_path, get_vendor_root


@pytest.fixture(autouse=True)
def tmp_base_dir(tmp_path, settings):
    """Redirect manifest/vendor paths to a temp dir so tests never touch the real,
    git-tracked annuaire/static/vendor/."""
    settings.BASE_DIR = tmp_path


def write_manifest(version="1.0.0"):
    manifest = {
        "some-lib": {
            "package": "some-lib",
            "version": version,
            "dir": "some-lib",
            "files": [{"src": "dist/some-lib.min.js", "dest": "some-lib.min.js"}],
        }
    }
    manifest_path = get_manifest_path()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


class _FakeResponse:
    def __init__(self, *, payload=None, content=None):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def run_command(*args):
    out = StringIO()
    call_command("upgrade_vendored_assets", *args, stdout=out)
    return out.getvalue()


class TestUpgradeVendoredAssets:
    def test_reports_up_to_date_when_no_new_version(self, monkeypatch):
        write_manifest(version="1.0.0")

        def fake_get(url, timeout=None):
            assert "registry.npmjs.org" in url
            return _FakeResponse(payload={"version": "1.0.0"})

        monkeypatch.setattr("annuaire.management.commands.upgrade_vendored_assets.requests.get", fake_get)

        output = run_command()

        assert "déjà à jour" in output
        assert json.loads(get_manifest_path().read_text())["some-lib"]["version"] == "1.0.0"

    def test_check_only_lists_without_downloading(self, monkeypatch):
        write_manifest(version="1.0.0")
        download_calls = []

        def fake_get(url, timeout=None):
            if "registry.npmjs.org" in url:
                return _FakeResponse(payload={"version": "2.0.0"})
            download_calls.append(url)
            return _FakeResponse(content=b"new content")

        monkeypatch.setattr("annuaire.management.commands.upgrade_vendored_assets.requests.get", fake_get)

        output = run_command("--check-only")

        assert "1.0.0 -> 2.0.0" in output
        assert download_calls == []
        assert json.loads(get_manifest_path().read_text())["some-lib"]["version"] == "1.0.0"
        assert not (get_vendor_root() / "some-lib" / "some-lib.min.js").exists()

    def test_upgrades_and_downloads_files(self, monkeypatch):
        write_manifest(version="1.0.0")

        def fake_get(url, timeout=None):
            if "registry.npmjs.org" in url:
                return _FakeResponse(payload={"version": "2.0.0"})
            assert url == "https://cdn.jsdelivr.net/npm/some-lib@2.0.0/dist/some-lib.min.js"
            return _FakeResponse(content=b"new content")

        monkeypatch.setattr("annuaire.management.commands.upgrade_vendored_assets.requests.get", fake_get)

        output = run_command()

        assert "some-lib : 1.0.0 -> 2.0.0" in output
        assert json.loads(get_manifest_path().read_text())["some-lib"]["version"] == "2.0.0"
        downloaded = get_vendor_root() / "some-lib" / "some-lib.min.js"
        assert downloaded.read_bytes() == b"new content"

    def test_summary_file_lists_upgraded_packages(self, monkeypatch, tmp_path):
        write_manifest(version="1.0.0")

        def fake_get(url, timeout=None):
            if "registry.npmjs.org" in url:
                return _FakeResponse(payload={"version": "2.0.0"})
            return _FakeResponse(content=b"new content")

        monkeypatch.setattr("annuaire.management.commands.upgrade_vendored_assets.requests.get", fake_get)

        summary_file = tmp_path / "summary.md"
        run_command("--summary-file", str(summary_file))

        assert "`some-lib`: 1.0.0 → 2.0.0" in summary_file.read_text()

    def test_missing_manifest_raises_command_error(self):
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            run_command()

    def test_underscore_keys_are_ignored(self, monkeypatch):
        manifest_path = get_manifest_path()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"_comment": "not a package"}))

        calls = []

        def fake_get(url, timeout=None):
            calls.append(url)
            return _FakeResponse(payload={"version": "1.0.0"})

        monkeypatch.setattr("annuaire.management.commands.upgrade_vendored_assets.requests.get", fake_get)

        output = run_command()

        assert calls == []
        assert "Aucune bibliothèque" in output
