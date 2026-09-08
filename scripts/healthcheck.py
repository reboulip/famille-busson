"""Compose healthcheck probe for the `web` service (9.10).

Not `curl`/`wget` because the `python:3.13-slim` base image ships neither. Sends an
explicit Host header matching ALLOWED_HOSTS's first entry, since SECURE_SSL_REDIRECT
and Django's own host validation would otherwise turn a plain in-container request
into a redirect or a DisallowedHost 400 -- neither of which reaches the actual view.
Exits non-zero (via the propagating exception) on anything but HTTP 200: urlopen
raises HTTPError for a 5xx response, which is exactly what a critical check failing
(database/media_storage/documents_storage -- see annuaire/health.py) returns.
"""

import os
import urllib.request

host = (os.environ.get("ALLOWED_HOSTS") or "localhost").split(",")[0].strip()
request = urllib.request.Request("http://localhost:8000/healthz", headers={"Host": host})
urllib.request.urlopen(request, timeout=5)
