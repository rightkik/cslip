import base64
import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

import app.main as main_module
from app.line_client import format_receipt_summary
from app.main import app
from app.ocr.base import ReceiptData
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import FileMessageContent, ImageMessageContent, MessageEvent

client = TestClient(app)


def _sig(body: bytes, secret: str = "test-secret") -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


# --- format_receipt_summary (pure, no I/O) ---

def test_format_summary_shows_all_fields():
    data = ReceiptData(
        vendor_name="Starbucks TH",
        vendor_tax_id="1234567890123",
        issue_date="2025-03-15",
        document_type="receipt",
        document_number="SB-001",
        category="ค่าอาหาร",
        subtotal=Decimal("172.90"),
        vat_amount=Decimal("12.10"),
        total_amount=Decimal("185.00"),
        confidence=0.95,
    )
    text = format_receipt_summary(data)
    assert "Starbucks TH" in text
    assert "1234567890123" in text
    assert "172.90" in text
    assert "12.10" in text
    assert "185.00" in text
    assert "95%" in text


def test_format_summary_minimal_no_crash():
    text = format_receipt_summary(ReceiptData())
    assert "📄" in text
    assert "-" in text  # None fields render as "-"


def test_format_summary_no_optional_lines_when_none():
    data = ReceiptData(vendor_name="Shop", total_amount=Decimal("100"))
    text = format_receipt_summary(data)
    assert "VAT" not in text
    assert "WHT" not in text
    assert "เลขที่" not in text


# --- webhook endpoint ---

def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_webhook_rejects_missing_signature():
    body = b'{"events": []}'
    resp = client.post("/webhook", content=body)
    assert resp.status_code == 400


def test_webhook_rejects_wrong_signature():
    body = b'{"destination":"x","events":[]}'
    resp = client.post("/webhook", content=body, headers={"x-line-signature": "bad=="})
    assert resp.status_code == 400


def test_webhook_accepts_empty_events():
    body = json.dumps({"destination": "test", "events": []}).encode()
    resp = client.post("/webhook", content=body, headers={"x-line-signature": _sig(body)})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def _webhook_with_event(mock_event, body: bytes):
    """Helper: POST webhook with a mocked parsed event, returns (response, add_task mock)."""
    with patch("app.main.WebhookParser") as MockParser:
        MockParser.return_value.parse.return_value = [mock_event]
        with patch.object(BackgroundTasks, "add_task") as mock_add:
            resp = client.post(
                "/webhook",
                content=body,
                headers={"x-line-signature": _sig(body)},
            )
    return resp, mock_add


def test_webhook_image_message_queues_background_task():
    body = json.dumps({"destination": "test", "events": []}).encode()

    mock_msg = MagicMock(spec=ImageMessageContent)
    mock_msg.id = "msg-789"

    mock_event = MagicMock(spec=MessageEvent)
    mock_event.message = mock_msg
    mock_event.reply_token = "reply-token-abc"

    resp, mock_add = _webhook_with_event(mock_event, body)

    assert resp.status_code == 200
    mock_add.assert_called_once()
    assert mock_add.call_args[0][0] is main_module._process_receipt
    assert mock_add.call_args[1] == {"message_id": "msg-789", "reply_token": "reply-token-abc"}


def test_webhook_file_message_queues_background_task():
    body = json.dumps({"destination": "test", "events": []}).encode()

    mock_msg = MagicMock(spec=FileMessageContent)
    mock_msg.id = "file-001"

    mock_event = MagicMock(spec=MessageEvent)
    mock_event.message = mock_msg
    mock_event.reply_token = "reply-token-xyz"

    resp, mock_add = _webhook_with_event(mock_event, body)

    assert resp.status_code == 200
    mock_add.assert_called_once()
    assert mock_add.call_args[0][0] is main_module._process_receipt
    assert mock_add.call_args[1] == {"message_id": "file-001", "reply_token": "reply-token-xyz"}


def test_webhook_non_image_message_skips():
    body = json.dumps({"destination": "test", "events": []}).encode()

    mock_msg = MagicMock()  # not Image/File, no __class__ override
    mock_event = MagicMock()
    mock_event.__class__ = MessageEvent
    mock_event.message = mock_msg

    with patch("app.main.WebhookParser") as MockParser:
        MockParser.return_value.parse.return_value = [mock_event]
        with patch("app.main._process_receipt", new_callable=AsyncMock) as mock_proc:
            resp = client.post(
                "/webhook",
                content=body,
                headers={"x-line-signature": _sig(body)},
            )

    assert resp.status_code == 200
    mock_proc.assert_not_awaited()
