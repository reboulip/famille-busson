# Restore procedure

"A backup nobody has restored is not a backup." This page is the runbook for
restoring a backup produced by `scripts/backup.sh` (see
[`deployment.md`'s "Sauvegardes" section](deployment.md#sauvegardes)), and
`scripts/restore.sh` is the tool it walks through.

**Status:** the tooling below is written and its logic reviewed, but has never
been executed — this dev environment has no Docker/Postgres to run it against.
The [drill log](#drill-log) at the bottom is empty until someone actually runs
a drill on the VPS; until then, treat this as documented but unverified.

## Prerequisites

- `docker compose` (same as everywhere else this project uses it).
- `python3` on the host running the script — `restore.sh` uses it to parse and
  checksum-verify `manifest.json` before touching anything. Present on
  essentially every Debian/Ubuntu VPS by default; if it's ever missing,
  `apt install python3` is enough (no packages beyond the standard library are
  used).
- [`age`](https://github.com/FiloSottile/age) — to decrypt `env.age`, if the
  backup includes one. You need the **private** key matching the
  `BACKUP_AGE_RECIPIENT` public key the backup was encrypted with (see
  `deployment.md` — this key is deliberately never stored on the VPS itself).
- A backup run directory to restore from — either a local one under
  `$BACKUP_DIR` on the VPS, or one pulled down from the off-site `rclone`
  remote (`rclone copy <remote>/<timestamp> ./restore-input`).

## The drill vs. a real restore

`scripts/restore.sh` defaults to a **scratch, throwaway target**
(`docker-compose.restore.yml`, project name `bubu-restore-drill`) — this is
the safe, ergonomic default path, meant to be run any time to rehearse the
procedure and prove a given backup is actually restorable, without touching
anything real.

Restoring into the **real** production stack (`docker-compose.prod.yml`) is a
separate, deliberately awkward path: it requires `--yes-i-mean-production`
and will refuse to run without it. Never pass that flag as a matter of habit —
it exists so restoring over the live database is a decision, not an accident.

## Step-by-step (drill)

1. Identify the backup to restore: a directory containing `manifest.json`,
   `db.dump`, `media.tar.gz`, `documents.tar.gz`, and optionally `env.age`.
2. Run the script against the scratch target (the default):
   ```
   bash scripts/restore.sh --backup-path /path/to/backups/20260906T030000Z
   ```
   This verifies every artifact's checksum against `manifest.json` before
   touching anything, then brings up `docker-compose.restore.yml`'s scratch
   `db`/`web` containers, restores the dump, and extracts the archives.
3. **Verify** (see below) before considering the drill successful.
4. Tear the scratch stack down: `docker compose -f docker-compose.restore.yml -p bubu-restore-drill down -v`.
5. Record the result in the [drill log](#drill-log) below.

## Verification checklist

After `restore.sh` reports it has finished:

1. **Schema matches the shipped code**:
   ```
   docker compose -f docker-compose.restore.yml -p bubu-restore-drill exec -T web python manage.py migrate --check
   ```
   A restored dump from an older app version failing this check is expected
   and informative, not a bug in the restore — it means the app image running
   against it also needs to match the backup's `app_version` (from
   `manifest.json`) to test a truly historical state.
2. **Postgres actually has data**:
   ```
   docker compose -f docker-compose.restore.yml -p bubu-restore-drill exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\dt'
   ```
   should list the app's tables, non-empty.
3. **Files referenced in the database exist on disk** — spot-check a handful
   of `DocumentFile`/`Attachment`/`Person.profile_photo`/`Photo` rows against the
   restored `media`/`documents_data` trees (`Photo` lives under
   `documents_data/photos`, nested inside the same archive — see
   `settings.PHOTOS_ROOT`):
   ```
   docker compose -f docker-compose.restore.yml -p bubu-restore-drill exec -T web python manage.py shell -c "
   from documents.models import DocumentFile
   from photos.models import Photo
   for f in DocumentFile.objects.exclude(file='')[:5]:
       print(f.file.name, f.file.storage.exists(f.file.name))
   for p in Photo.objects.exclude(file='')[:5]:
       print(p.file.name, p.file.storage.exists(p.file.name))
   "
   ```
4. **The app actually serves**:
   ```
   docker compose -f docker-compose.restore.yml -p bubu-restore-drill exec -T web curl -sf http://localhost:8000/healthz
   ```

## Manifest contract

`restore.sh` reads `manifest.json` from the backup directory before doing
anything else, and refuses to proceed if a listed artifact's sha256 doesn't
match. See `scripts/backup.sh` for the authoritative field list
(`manifest_version`, `app_version`, `postgres_version`, `backup_start`,
`backup_end`, `backup_exit_status`, `artifacts`). A restore against a
`manifest_version` newer than what `restore.sh` understands aborts with an
explicit error rather than guessing.

## Drill log

| Date | Version | Taille | Durée | Résultat | Opérateur |
|------|---------|--------|-------|----------|-----------|
| _(none yet — the first drill has not been run)_ | | | | | |
