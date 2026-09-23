# Restore procedure

A backup is only useful if you can restore it. This page explains how to restore a
backup made by `scripts/backup.sh` (see [Sauvegardes](deployment.md#sauvegardes)),
using `scripts/restore.sh`.

**Status:** the restore script is written and reviewed, but it has never been run. The
[drill log](#drill-log) below stays empty until someone runs a test restore on the
server. Until then, treat this procedure as unverified.

## Prerequisites

- `docker compose`.
- `python3` on the server. The script uses it to check `manifest.json`. It is installed
  on almost every Debian or Ubuntu server. If not, run `apt install python3`.
- [`age`](https://github.com/FiloSottile/age), to decrypt `env.age`. You need the
  **private** key that matches `BACKUP_AGE_RECIPIENT`. This key is never stored on the
  server.
- The backup folder to restore. It can be on the server (in `$BACKUP_DIR`), or you can
  download it from off-site storage:
  `rclone copy <remote>/<timestamp> ./restore-input`.

## The drill vs. a real restore

By default, `scripts/restore.sh` restores into a **separate, temporary copy** of the
site (`docker-compose.restore.yml`). This is a "drill". It does not touch the real site.
You can run it at any time to check that a backup works.

To restore into the **real** site, you must add `--yes-i-mean-production`. Without this
option, the script refuses. Never add it out of habit: restoring over the live database
must be a conscious choice.

## Step-by-step (drill)

1. Choose the backup. It is a folder with `manifest.json`, `db.dump`, `media.tar.gz`,
   `documents.tar.gz`, and maybe `env.age`.
2. Run the script:
   ```
   bash scripts/restore.sh --backup-path /path/to/backups/20260906T030000Z
   ```
   It first checks every file against `manifest.json`. Then it starts the temporary
   containers, restores the database and extracts the files.
3. **Check** the result (see below).
4. Remove the temporary copy:
   `docker compose -f docker-compose.restore.yml -p bubu-restore-drill down -v`.
5. Write the result in the [drill log](#drill-log) below.

## Verification checklist

When `restore.sh` has finished:

1. **The database matches the code:**
   ```
   docker compose -f docker-compose.restore.yml -p bubu-restore-drill exec -T web python manage.py migrate --check
   ```
   If the backup comes from an older version of the app, this check can fail. That is
   normal. To test an old backup fully, run the app version written in `manifest.json`
   (`app_version`).
2. **The database contains data:**
   ```
   docker compose -f docker-compose.restore.yml -p bubu-restore-drill exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\dt'
   ```
   You should see the app's tables, with data in them.
3. **The files exist on disk.** Check a few documents and photos:
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
   Every line should end with `True`.
4. **The app responds:**
   ```
   docker compose -f docker-compose.restore.yml -p bubu-restore-drill exec -T web curl -sf http://localhost:8000/healthz
   ```

## Manifest contract

`restore.sh` reads `manifest.json` first. If a file's checksum does not match, it
stops. The list of fields is in `scripts/backup.sh`. If the manifest's
`manifest_version` is newer than the script knows, the script stops with an error
instead of guessing.

## Drill log

| Date | Version | Taille | Durée | Résultat | Opérateur |
|------|---------|--------|-------|----------|-----------|
| _(none yet — no drill has been run)_ | | | | | |
