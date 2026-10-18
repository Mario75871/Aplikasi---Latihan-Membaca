"""Test logging terstruktur (integrasi #5, D5)."""
from __future__ import annotations

import json
import logging

from logging_config import JsonFormatter, redact


def test_json_formatter_emits_valid_json():
    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="access", level=logging.INFO, pathname="", lineno=0,
        msg="request", args=(), exc_info=None,
    )
    record.request_id = "rid-1"
    record.method = "GET"
    record.path = "/health"
    record.status = 200
    out = fmt.format(record)
    data = json.loads(out)  # valid JSON
    assert data["level"] == "INFO"
    assert data["msg"] == "request"
    assert data["request_id"] == "rid-1"
    assert data["status"] == 200


def test_redact_hides_most_of_value():
    r = redact("supersecrettoken")
    assert r.startswith("supe")
    assert "****" in r
    assert "secrettoken" not in r
    assert redact("") == ""
