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

# appuser runs the app itself (migrate/collectstatic/gunicorn), but the container
# starts as root (no USER here) -- docker-entrypoint.sh chowns the bind-mounted
# media volume to appuser before dropping to it via runuser, since the volume's
# host-side ownership can't be relied on to match this UID ahead of time.
RUN chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app \
    && command -v runuser

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "famille_busson.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
