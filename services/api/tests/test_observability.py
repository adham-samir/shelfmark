"""Structured logging: one line per request, with no credentials in it."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from smart_ecommerce_api import observability
from smart_ecommerce_api.main import create_app
from smart_ecommerce_api.observability import (
    ACCESS_EVENT,
    JsonFormatter,
    TextFormatter,
    request_id_var,
)


def _record(**fields) -> logging.LogRecord:
    record = logging.LogRecord(
        name="smart_ecommerce.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=fields.pop("event", ACCESS_EVENT),
        args=(),
        exc_info=None,
    )
    for key, value in fields.items():
        setattr(record, key, value)
    return record


# ----------------------------------------------------------------- formatters
def test_json_formatter_emits_the_documented_fields():
    record = _record(
        method="GET",
        path="/v1/orders",
        status=200,
        duration_ms=7,
        request_id="11111111-1111-4111-8111-111111111111",
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["level"] == "INFO"
    assert payload["event"] == ACCESS_EVENT
    assert payload["method"] == "GET"
    assert payload["path"] == "/v1/orders"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 7
    assert payload["request_id"] == "11111111-1111-4111-8111-111111111111"
    assert payload["ts"].endswith("Z")


def test_json_formatter_falls_back_to_the_context_request_id():
    record = _record(method="GET", path="/", status=200, duration_ms=1)
    token = request_id_var.set("22222222-2222-4222-8222-222222222222")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert payload["request_id"] == "22222222-2222-4222-8222-222222222222"


def test_json_formatter_includes_a_traceback_when_present():
    import sys

    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="smart_ecommerce.error",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="http_error",
            args=(),
            exc_info=sys.exc_info(),
        )
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]


def test_text_formatter_is_readable_and_keeps_the_request_id():
    record = _record(
        method="POST",
        path="/v1/checkout",
        status=202,
        duration_ms=31,
        request_id="33333333-3333-4333-8333-333333333333",
    )
    line = TextFormatter().format(record)
    assert "method=POST" in line
    assert "path=/v1/checkout" in line
    assert "status=202" in line
    assert "request_id=33333333-3333-4333-8333-333333333333" in line


# -------------------------------------------------------------- live requests
@pytest.fixture()
def client() -> TestClient:
    # A bare TestClient does not run lifespan, so configure_logging is not
    # applied and caplog can capture the records this test asserts on.
    return TestClient(create_app(), raise_server_exceptions=False)


def _access_records(caplog) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name.endswith(".access")]


def test_one_access_line_per_request_with_the_request_id(client, caplog):
    caplog.set_level(logging.INFO, logger="smart_ecommerce.access")
    response = client.get("/health/live", headers={"x-request-id": "44444444-4444-4444-8444-444444444444"})
    assert response.status_code == 200

    records = _access_records(caplog)
    assert len(records) == 1
    record = records[0]
    assert record.event == ACCESS_EVENT
    assert record.method == "GET"
    assert record.path == "/health/live"
    assert record.status == 200
    assert isinstance(record.duration_ms, int)
    # The header and the log line agree, which is what makes a quoted ID useful.
    assert record.request_id == response.headers["x-request-id"]


def test_an_invalid_request_id_is_replaced_with_a_fresh_one(client, caplog):
    caplog.set_level(logging.INFO, logger="smart_ecommerce.access")
    response = client.get("/health/live", headers={"x-request-id": "not-a-uuid"})
    record = _access_records(caplog)[0]
    assert record.request_id == response.headers["x-request-id"]
    assert record.request_id != "not-a-uuid"


def test_a_client_error_is_logged_at_warning_without_a_traceback(client, caplog):
    caplog.set_level(logging.INFO, logger="smart_ecommerce.error")
    response = client.get("/v1/orders")
    assert response.status_code == 401

    errors = [r for r in caplog.records if r.name.endswith(".error")]
    assert len(errors) == 1
    assert errors[0].levelno == logging.WARNING
    assert errors[0].code == "unauthorized"
    assert errors[0].status == 401
    assert errors[0].exc_info is None


def test_the_access_line_never_contains_a_credential_or_contact_detail(client, caplog):
    caplog.set_level(logging.DEBUG, logger="smart_ecommerce")
    token = "customer-token-should-never-be-logged"
    client.get(
        "/v1/account",
        headers={
            "authorization": f"Bearer {token}",
            "cookie": "smart_customer_session=also-secret",
            "x-request-id": "55555555-5555-4555-8555-555555555555",
        },
    )
    rendered = "\n".join(
        json.loads(JsonFormatter().format(record)) and JsonFormatter().format(record)
        for record in caplog.records
    )
    assert token not in rendered
    assert "also-secret" not in rendered
    assert "Bearer" not in rendered


def test_configure_logging_is_idempotent_and_silences_uvicorn_access(monkeypatch):
    monkeypatch.setattr(observability, "_configured", False)
    monkeypatch.setenv("SMART_ECOMMERCE_LOG_FORMAT", "json")
    observability.configure_logging()
    logger = logging.getLogger("smart_ecommerce")
    first_handlers = list(logger.handlers)
    observability.configure_logging()
    assert logger.handlers == first_handlers
    assert len(first_handlers) == 1
    assert isinstance(first_handlers[0].formatter, JsonFormatter)
    assert logging.getLogger("uvicorn.access").level == logging.WARNING
    # Startup and crash messages must still be visible.
    assert logging.getLogger("uvicorn.error").level == logging.NOTSET


def test_text_format_is_selectable(monkeypatch):
    monkeypatch.setattr(observability, "_configured", False)
    monkeypatch.setenv("SMART_ECOMMERCE_LOG_FORMAT", "text")
    observability.configure_logging()
    handler = logging.getLogger("smart_ecommerce").handlers[0]
    assert isinstance(handler.formatter, TextFormatter)
