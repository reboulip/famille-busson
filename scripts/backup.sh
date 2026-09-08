#!/usr/bin/env bash
set -euo pipefail

# Automated backup: dumps Postgres, archives media/ and documents_data/, encrypts a
# copy of .env, and syncs the result off-VPS via rclone. Retention: BACKUP_KEEP_DAILY
# most recent runs plus BACKUP_KEEP_WEEKLY older ones kept locally; the off-site copy
# additionally keeps BACKUP_KEEP_MONTHLY older runs still, since off-site storage is
# cheap and disk on the VPS is not.
#
# Usage (see docs/deployment.md's "Sauvegardes" section for the cron entry):
#   cd /srv/bubu && bash scripts/backup.sh [--dry-run]
#
# Reads its configuration from the environment -- when invoked via cron this comes
# from sourcing ENV_FILE (default: ./.env) below, matching how docker compose itself
# reads /srv/bubu/.env.

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

ENV_FILE="${ENV_FILE:-.env}"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

COMPOSE_DIR="${COMPOSE_DIR:-/srv/bubu}"
DATA_DIR="${DATA_DIR:-$COMPOSE_DIR/data}"
BACKUP_DIR="${BACKUP_DIR:-/srv/bubu/backups}"
BACKUP_KEEP_DAILY="${BACKUP_KEEP_DAILY:-7}"
BACKUP_KEEP_WEEKLY="${BACKUP_KEEP_WEEKLY:-4}"
BACKUP_KEEP_MONTHLY="${BACKUP_KEEP_MONTHLY:-6}"
BACKUP_REMOTE="${BACKUP_REMOTE:-}"
BACKUP_PING_URL="${BACKUP_PING_URL:-}"
BACKUP_MIN_DB_BYTES="${BACKUP_MIN_DB_BYTES:-1000}"
BACKUP_MIN_MEDIA_BYTES="${BACKUP_MIN_MEDIA_BYTES:-0}"
BACKUP_MIN_DOCUMENTS_BYTES="${BACKUP_MIN_DOCUMENTS_BYTES:-0}"
# Relative-size checks catch a slow-creeping truncation an absolute floor set once
# would miss (e.g. a dump that silently produces half its expected rows every night,
# each one individually clearing BACKUP_MIN_DB_BYTES). 0 disables a given check; 0.5
# means "this run's artifact must be at least half the size of the previous run's" --
# deliberately loose, since a real family site's day-to-day size swings (someone
# deletes an old document, say) are plausible and shouldn't page anyone.
BACKUP_MIN_DB_RATIO="${BACKUP_MIN_DB_RATIO:-0.5}"
BACKUP_MIN_MEDIA_RATIO="${BACKUP_MIN_MEDIA_RATIO:-0.5}"
BACKUP_MIN_DOCUMENTS_RATIO="${BACKUP_MIN_DOCUMENTS_RATIO:-0}"
BACKUP_AGE_RECIPIENT="${BACKUP_AGE_RECIPIENT:-}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$BACKUP_DIR/$TIMESTAMP"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

ping_backup_monitor() {
    # $1: start|0|fail -- see https://healthchecks.io/docs/http_api/ for the shape.
    if [ -n "$BACKUP_PING_URL" ]; then
        curl -fsS -m 10 --retry 2 "$BACKUP_PING_URL/$1" >/dev/null 2>&1 || true
    fi
}

fail() {
    log "ERROR: $*"
    ping_backup_monitor fail
    exit 1
}

trap 'fail "backup aborted (line $LINENO)"' ERR

size_of() { stat -c%s "$1" 2>/dev/null || stat -f%z "$1"; }
sha256_of() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$1" | cut -d' ' -f1; }

ping_backup_monitor start

# Preflight: enough free space before writing anything -- a full disk here also holds
# Postgres's own data directory, so running it dry mid-dump is a real risk, not a
# hypothetical.
AVAILABLE_KB="$(df --output=avail "$BACKUP_DIR" 2>/dev/null | tail -1 || df --output=avail "$(dirname "$BACKUP_DIR")" | tail -1)"
if [ "${AVAILABLE_KB:-0}" -lt "$((1024 * 1024))" ]; then
    fail "less than 1GiB free near $BACKUP_DIR -- aborting before writing anything"
fi

if [ "$DRY_RUN" = "1" ]; then
    log "dry-run: would create $RUN_DIR, dump the database, archive media/ and documents_data/, encrypt $ENV_FILE, sync to ${BACKUP_REMOTE:-<no BACKUP_REMOTE set>}, and prune old backups (keep $BACKUP_KEEP_DAILY daily / $BACKUP_KEEP_WEEKLY weekly locally, +$BACKUP_KEEP_MONTHLY monthly off-site)"
    exit 0
fi

mkdir -p "$RUN_DIR"
chmod 700 "$BACKUP_DIR" "$RUN_DIR"

START_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

log "dumping database to $RUN_DIR/db.dump"
(cd "$COMPOSE_DIR" && docker compose exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"') > "$RUN_DIR/db.dump"

DB_SIZE="$(size_of "$RUN_DIR/db.dump")"
if [ "$DB_SIZE" -lt "$BACKUP_MIN_DB_BYTES" ]; then
    fail "db.dump is only $DB_SIZE bytes (< BACKUP_MIN_DB_BYTES=$BACKUP_MIN_DB_BYTES) -- looks truncated"
fi
check_relative_size db.dump "$DB_SIZE" "$BACKUP_MIN_DB_RATIO"

POSTGRES_VERSION="$(cd "$COMPOSE_DIR" && docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT version();"' | tr -d '\r' || echo unknown)"
APP_VERSION="$(cd "$COMPOSE_DIR" && docker compose exec -T web python manage.py shell -c 'from django.conf import settings; print(settings.APP_VERSION)' 2>/dev/null | tr -d '\r' || echo unknown)"

archive_tree() {
    # $1: source dir name under DATA_DIR, $2: destination tar.gz path.
    local src="$1" dest="$2" tar_exit=0
    tar czf "$dest" -C "$DATA_DIR" "$src" || tar_exit=$?
    if [ "$tar_exit" -ge 2 ]; then
        fail "tar failed archiving $src (exit $tar_exit)"
    elif [ "$tar_exit" -eq 1 ]; then
        # "file changed as we read it" -- near-certain on a live media/ tree under
        # traffic. The archive is still usable; only exit codes >= 2 are real failures.
        log "WARNING: tar reported changed files while archiving $src (exit 1) -- archive still usable"
    fi
}

# Relative-size checks: compare this run's artifact against the immediately preceding
# run's manifest.json, catching a slow-creeping truncation an absolute floor (set once,
# in bytes) would miss. Reads manifest.json with grep/sed rather than a JSON parser --
# the format is one we control ourselves (see the manifest-writing block below), so a
# plain pattern match is enough and keeps this script's only dependencies bash+coreutils.
previous_manifest() {
    local -a runs
    mapfile -t runs < <(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '????????T??????Z' | sort)
    local prev=""
    local run
    for run in "${runs[@]}"; do
        [ "$run" = "$RUN_DIR" ] && continue
        prev="$run"
    done
    if [ -n "$prev" ] && [ -f "$prev/manifest.json" ]; then
        echo "$prev/manifest.json"
    fi
}

previous_artifact_size() {
    local manifest="$1" artifact="$2"
    grep -o "\"${artifact}\": {\"size_bytes\": [0-9]*" "$manifest" 2>/dev/null | grep -o '[0-9]*$' || true
}

check_relative_size() {
    # $1: artifact filename, $2: this run's size in bytes, $3: minimum ratio of the
    # previous run's size (0 disables the check).
    local artifact="$1" current_size="$2" ratio="$3"
    [ "$ratio" = "0" ] && return 0

    local manifest
    manifest="$(previous_manifest)"
    if [ -z "$manifest" ]; then
        log "no previous backup to compare $artifact against -- skipping relative-size check"
        return 0
    fi

    local previous_size
    previous_size="$(previous_artifact_size "$manifest" "$artifact")"
    if [ -z "$previous_size" ]; then
        log "previous manifest has no size recorded for $artifact -- skipping relative-size check"
        return 0
    fi

    local threshold
    threshold="$(awk -v p="$previous_size" -v r="$ratio" 'BEGIN { printf "%d", p * r }')"
    if [ "$current_size" -lt "$threshold" ]; then
        fail "$artifact is only $current_size bytes, less than ${ratio}x the previous run's $previous_size bytes (threshold ~$threshold) -- looks like a regression, not normal variance"
    fi
}

log "archiving media/ to $RUN_DIR/media.tar.gz"
archive_tree media "$RUN_DIR/media.tar.gz"

log "archiving documents/ to $RUN_DIR/documents.tar.gz"
archive_tree documents "$RUN_DIR/documents.tar.gz"

MEDIA_SIZE="$(size_of "$RUN_DIR/media.tar.gz")"
if [ "$MEDIA_SIZE" -lt "$BACKUP_MIN_MEDIA_BYTES" ]; then
    fail "media.tar.gz is only $MEDIA_SIZE bytes (< BACKUP_MIN_MEDIA_BYTES=$BACKUP_MIN_MEDIA_BYTES)"
fi
check_relative_size media.tar.gz "$MEDIA_SIZE" "$BACKUP_MIN_MEDIA_RATIO"

DOCUMENTS_SIZE="$(size_of "$RUN_DIR/documents.tar.gz")"
if [ "$DOCUMENTS_SIZE" -lt "$BACKUP_MIN_DOCUMENTS_BYTES" ]; then
    fail "documents.tar.gz is only $DOCUMENTS_SIZE bytes (< BACKUP_MIN_DOCUMENTS_BYTES=$BACKUP_MIN_DOCUMENTS_BYTES)"
fi
check_relative_size documents.tar.gz "$DOCUMENTS_SIZE" "$BACKUP_MIN_DOCUMENTS_RATIO"

if [ -n "$BACKUP_AGE_RECIPIENT" ] && [ -f "$ENV_FILE" ]; then
    log "encrypting $ENV_FILE to $RUN_DIR/env.age"
    age -r "$BACKUP_AGE_RECIPIENT" -o "$RUN_DIR/env.age" < "$ENV_FILE"
else
    log "WARNING: BACKUP_AGE_RECIPIENT not set or $ENV_FILE missing -- .env not included in this backup"
fi

END_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# manifest.json is a contract read by scripts/restore.sh (9.3) and the backup
# monitoring thresholds (9.4) -- keep its shape in sync with docs/deployment.md if it
# ever changes, and bump manifest_version when it does.
{
    printf '{\n'
    printf '  "manifest_version": 1,\n'
    printf '  "app_version": "%s",\n' "$APP_VERSION"
    printf '  "postgres_version": "%s",\n' "$POSTGRES_VERSION"
    printf '  "backup_start": "%s",\n' "$START_TIME"
    printf '  "backup_end": "%s",\n' "$END_TIME"
    printf '  "backup_exit_status": 0,\n'
    printf '  "artifacts": {\n'
    first=1
    for artifact in db.dump media.tar.gz documents.tar.gz env.age; do
        [ -f "$RUN_DIR/$artifact" ] || continue
        [ "$first" = 1 ] || printf ',\n'
        first=0
        printf '    "%s": {"size_bytes": %s, "sha256": "%s"}' \
            "$artifact" "$(size_of "$RUN_DIR/$artifact")" "$(sha256_of "$RUN_DIR/$artifact")"
    done
    printf '\n  }\n'
    printf '}\n'
} > "$RUN_DIR/manifest.json"

log "wrote $RUN_DIR/manifest.json"

# Off-site copy: `rclone copy` (never `sync`) so a local bug can never delete the
# off-site copy -- pruning off-site is a separate, explicit step below.
if [ -n "$BACKUP_REMOTE" ]; then
    log "copying $RUN_DIR to $BACKUP_REMOTE/$TIMESTAMP"
    rclone copy "$RUN_DIR" "$BACKUP_REMOTE/$TIMESTAMP" || fail "rclone copy to $BACKUP_REMOTE failed"
fi

# Retention: keep the most recent $keep_daily run directories outright, then thin the
# rest to at most $keep_extra older ones, evenly spaced (every 7th, most-recent-first).
# Grandfather-style rather than a fixed lookback window, so a script that misses a few
# days (VPS down) doesn't lose more history than it has to.
thin_retention() {
    local dir="$1" keep_daily="$2" keep_extra="$3" delete="$4"
    local -a runs
    mapfile -t runs < <(find "$dir" -mindepth 1 -maxdepth 1 -type d -name '????????T??????Z' | sort)
    local total="${#runs[@]}"
    [ "$total" -eq 0 ] && return 0

    local daily_start=$((total - keep_daily))
    [ "$daily_start" -lt 0 ] && daily_start=0

    declare -A keep
    local i
    for ((i = daily_start; i < total; i++)); do
        keep["${runs[$i]}"]=1
    done

    local extra_kept=0
    for ((i = daily_start - 1; i >= 0 && extra_kept < keep_extra; i -= 7)); do
        keep["${runs[$i]}"]=1
        extra_kept=$((extra_kept + 1))
    done

    for run in "${runs[@]}"; do
        if [ -z "${keep[$run]:-}" ]; then
            log "pruning old backup $run"
            "$delete" "$run"
        fi
    done
}

rm_local() { rm -rf "$1"; }

log "pruning local backups older than $BACKUP_KEEP_DAILY daily / $BACKUP_KEEP_WEEKLY weekly"
thin_retention "$BACKUP_DIR" "$BACKUP_KEEP_DAILY" "$BACKUP_KEEP_WEEKLY" rm_local

if [ -n "$BACKUP_REMOTE" ]; then
    log "pruning off-site backups older than $BACKUP_KEEP_DAILY daily / $((BACKUP_KEEP_WEEKLY + BACKUP_KEEP_MONTHLY)) extra"
    # A plain directory listing, one per run -- rclone lsf's --dirs-only mirrors the
    # local run-directory naming exactly, so the same thin_retention logic applies.
    remote_thin_retention() {
        local -a remote_runs
        mapfile -t remote_runs < <(rclone lsf --dirs-only "$BACKUP_REMOTE" 2>/dev/null | sed 's#/$##' | sort)
        local total="${#remote_runs[@]}"
        [ "$total" -eq 0 ] && return 0
        local daily_start=$((total - BACKUP_KEEP_DAILY))
        [ "$daily_start" -lt 0 ] && daily_start=0
        declare -A keep
        local i
        for ((i = daily_start; i < total; i++)); do keep["${remote_runs[$i]}"]=1; done
        local extra_kept=0
        local keep_extra=$((BACKUP_KEEP_WEEKLY + BACKUP_KEEP_MONTHLY))
        for ((i = daily_start - 1; i >= 0 && extra_kept < keep_extra; i -= 7)); do
            keep["${remote_runs[$i]}"]=1
            extra_kept=$((extra_kept + 1))
        done
        for run in "${remote_runs[@]}"; do
            if [ -z "${keep[$run]:-}" ]; then
                log "pruning old off-site backup $run"
                rclone purge "$BACKUP_REMOTE/$run" || log "WARNING: failed to purge off-site $run"
            fi
        done
    }
    remote_thin_retention
fi

ping_backup_monitor 0
log "backup complete: $RUN_DIR"
