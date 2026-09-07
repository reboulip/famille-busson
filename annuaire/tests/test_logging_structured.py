"""Structured JSON logging (9.9) -- annuaire.log_formatters.JsonFormatter."""

import json
import logging

from annuaire.log_formatters import JsonFormatter
from annuaire.middleware import RequestIdLogFilter, _request_id_var


def _make_record(exc_info=None):
    return logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=42,
        msg="hello %s",
        args=("world",),
        exc_info=exc_info,
    )


def test_formats_the_fixed_key_set():
    payload = json.loads(JsonFormatter().format(_make_record()))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["message"] == "hello world"
    assert payload["line"] == 42
    assert payload["timestamp"].endswith("Z")


def test_includes_a_rendered_exception():
    import sys

    try:
        raise ValueError("boom")
    except ValueError:
        record = _make_record(exc_info=sys.exc_info())
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]


def test_omits_exception_key_when_there_is_none():
    payload = json.loads(JsonFormatter().format(_make_record()))
    assert "exception" not in payload


def test_merges_extra_fields_at_the_top_level():
    record = _make_record()
    record.custom_field = 42
    payload = json.loads(JsonFormatter().format(record))
    assert payload["custom_field"] == 42


def test_includes_request_id_when_the_filter_set_one():
    record = _make_record()
    RequestIdLogFilter().filter(record)
    token = _request_id_var.set("req-abc-123")
    try:
        record2 = _make_record()
        RequestIdLogFilter().filter(record2)
        payload = json.loads(JsonFormatter().format(record2))
        assert payload["request_id"] == "req-abc-123"
    finally:
        _request_id_var.reset(token)


def test_omits_request_id_when_none_is_set():
    record = _make_record()
    RequestIdLogFilter().filter(record)
    payload = json.loads(JsonFormatter().format(record))
    assert "request_id" not in payload


def test_a_non_json_serializable_extra_value_falls_back_to_str():
    record = _make_record()
    record.weird = object()
    payload = json.loads(JsonFormatter().format(record))
    assert isinstance(payload["weird"], str)
