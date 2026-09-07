"""Structured JSON logging (9.9).

Stdlib-only -- no structlog/python-json-logger dependency for what's really a
~40-line formatter. Selected via LOG_FORMAT (see famille_busson/settings.py's
LOGGING); referenced there by dotted string so settings.py carries no import-time
coupling to this module.
"""

from __future__ import annotations

import datetime
import json
import logging

# Fixed key set, deliberately -- a log search over JSON output stays stable only if
# every record has the same shape. Anything passed via logger.info(..., extra={...})
# is merged in at the top level, alongside these.
_BASE_KEYS = ("timestamp", "level", "logger", "message", "module", "line")

# Every attribute a plain LogRecord carries by default -- computed once so
# distinguishing "standard" from "extra=" attributes doesn't allocate a throwaway
# LogRecord on every single formatted call.
_STANDARD_RECORD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None)))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.datetime.fromtimestamp(record.created, tz=datetime.UTC)
        payload = {
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{timestamp.microsecond // 1000:03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Anything passed via extra= that isn't one of LogRecord's own standard
        # attributes (or already handled above) merges in at the top level.
        for key, value in record.__dict__.items():
            if key in _BASE_KEYS or key == "request_id" or key in _STANDARD_RECORD_ATTRS:
                continue
            payload[key] = value

        return json.dumps(payload, default=str)
