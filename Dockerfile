FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies first so this layer is cached unless pyproject.toml/uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Pinned (not auto-assigned) so the UID is deterministic across builds -- the media
# volume is a host bind mount (/srv/bubu/data/media), and this UID must be able to
# write to it. If it doesn't match the VPS's `deploy` user's UID, uploads silently
# fail (PermissionError) since the host directory is owner-only (go-rwx). Verify with
# `id deploy` on the VPS and `chown -R 1000:1000 /srv/bubu/data/media` if they differ.
RUN chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "famille_busson.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
