#!/usr/bin/env bash
set -euo pipefail

# Restore a backup produced by scripts/backup.sh into a compose project. Defaults to a
# throwaway scratch target (docker-compose.restore.yml) -- see docs/restore.md for the
# full runbook. Restoring into the real production stack requires an explicit
# --yes-i-mean-production flag; without it, anything that looks like production is
# refused before touching a single container.
#
# Usage:
#   bash scripts/restore.sh --backup-path /path/to/backups/20260906T030000Z [options]
#
# Options:
#   --backup-path PATH        Directory containing manifest.json (required).
#   --compose-file FILE       Default: docker-compose.restore.yml (the drill target).
#   --project NAME            Default: bubu-restore-drill.
#   --yes-i-mean-production   Required to target docker-compose.prod.yml or a project
#                             name containing "prod" -- refuses to run without it.

COMPOSE_FILE="docker-compose.restore.yml"
PROJECT="bubu-restore-drill"
BACKUP_PATH=""
CONFIRM_PRODUCTION=0

while [ $# -gt 0 ]; do
    case "$1" in
        --backup-path)
            BACKUP_PATH="$2"
            shift 2
            ;;
        --compose-file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --project)
            PROJECT="$2"
            shift 2
            ;;
        --yes-i-mean-production)
            CONFIRM_PRODUCTION=1
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
fail() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $*" >&2
    exit 1
}

[ -n "$BACKUP_PATH" ] || fail "--backup-path is required"
[ -d "$BACKUP_PATH" ] || fail "backup path does not exist: $BACKUP_PATH"

MANIFEST="$BACKUP_PATH/manifest.json"
[ -f "$MANIFEST" ] || fail "no manifest.json in $BACKUP_PATH -- refusing to guess at artifact names"

# Safety gate: anything that looks like production requires an explicit flag. This is
# the load-bearing check the item exists for -- an accidental invocation must not be
# able to wipe the live database. Checked on both the compose file name and the
# project name, and on the compose file's own content (a renamed-but-still-prod file
# would still declare the real prod bind-mount paths).
looks_like_production() {
    case "$COMPOSE_FILE" in
        *prod*) return 0 ;;
    esac
    case "$PROJECT" in
        *prod*) return 0 ;;
    esac
    if [ -f "$COMPOSE_FILE" ] && grep -q '/srv/bubu/data' "$COMPOSE_FILE"; then
        return 0
    fi
    return 1
}

if looks_like_production && [ "$CONFIRM_PRODUCTION" -ne 1 ]; then
    fail "$COMPOSE_FILE / project '$PROJECT' looks like production -- pass --yes-i-mean-production if that is really what you want. The drill target (docker-compose.restore.yml) is the safe default; use it unless you specifically mean to restore over the live stack."
fi

[ -f "$COMPOSE_FILE" ] || fail "compose file not found: $COMPOSE_FILE"

log "verifying manifest checksums in $BACKUP_PATH"
python3 - "$MANIFEST" "$BACKUP_PATH" <<'PYEOF'
import hashlib
import json
import sys

manifest_path, backup_path = sys.argv[1], sys.argv[2]
with open(manifest_path) as f:
    manifest = json.load(f)

version = manifest.get("manifest_version")
if version != 1:
    sys.exit(f"unsupported manifest_version {version!r} -- this restore.sh only understands version 1")

import os

for name, meta in manifest.get("artifacts", {}).items():
    path = os.path.join(backup_path, name)
    if not os.path.isfile(path):
        sys.exit(f"manifest lists {name} but it is missing from {backup_path}")
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    expected = meta.get("sha256")
    if actual != expected:
        sys.exit(f"{name}: checksum mismatch (expected {expected}, got {actual}) -- backup may be corrupt")
    print(f"  {name}: OK ({meta.get('size_bytes')} bytes)")
PYEOF

log "manifest verified -- all artifacts present with matching checksums"

log "bringing up $COMPOSE_FILE (project: $PROJECT)"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d db
log "waiting for the database to become healthy"
for _ in $(seq 1 30); do
    status="$(docker compose -f "$COMPOSE_FILE" -p "$PROJECT" ps db --format json 2>/dev/null | python3 -c 'import json,sys; print(json.loads(sys.stdin.read() or "{}").get("Health",""))' 2>/dev/null || true)"
    [ "$status" = "healthy" ] && break
    sleep 2
done

log "restoring db.dump"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec -T db sh -c \
    'pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    < "$BACKUP_PATH/db.dump"

log "bringing up web"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d web

if [ -f "$BACKUP_PATH/media.tar.gz" ]; then
    log "extracting media.tar.gz into the web container's media volume"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec -T web mkdir -p /app/media
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec -T web tar xzf - -C /app/media --strip-components=1 < "$BACKUP_PATH/media.tar.gz"
fi

if [ -f "$BACKUP_PATH/documents.tar.gz" ]; then
    log "extracting documents.tar.gz into the web container's documents volume"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec -T web mkdir -p /app/documents_data
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec -T web tar xzf - -C /app/documents_data --strip-components=1 < "$BACKUP_PATH/documents.tar.gz"
fi

if [ -f "$BACKUP_PATH/env.age" ]; then
    log "env.age is present but not decrypted automatically -- the drill's own scratch"
    log "environment already drives the scratch containers. To inspect the real .env,"
    log "decrypt it by hand: age -d -i <private-key-file> $BACKUP_PATH/env.age"
fi

log "restore complete. Now run docs/restore.md's verification checklist:"
log "  docker compose -f $COMPOSE_FILE -p $PROJECT exec -T web python manage.py migrate --check"
log "  docker compose -f $COMPOSE_FILE -p $PROJECT exec -T web curl -sf http://localhost:8000/healthz"
log "Tear down when done: docker compose -f $COMPOSE_FILE -p $PROJECT down -v"
