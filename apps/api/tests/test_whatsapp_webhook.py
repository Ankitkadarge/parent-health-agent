import hashlib
import hmac
import json
import logging
import uuid

import pytest

import app.services.whatsapp_meta_client as meta_client_module
from app.core.config import settings

APP_SECRET = "unit-test-app-secret"
ACCESS_TOKEN = "unit-test-access-token"
VERIFY_TOKEN = "unit-test-verify-token"


@pytest.fixture(autouse=True)
def meta_configured(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_provider", "meta")
    monkeypatch.setattr(settings, "whatsapp_meta_phone_number_id", "1234567890")
    monkeypatch.setattr(settings, "whatsapp_meta_access_token", ACCESS_TOKEN)
    monkeypatch.setattr(settings, "whatsapp_meta_app_secret", APP_SECRET)
    monkeypatch.setattr(settings, "whatsapp_webhook_verify_token", VERIFY_TOKEN)
    monkeypatch.setattr(settings, "whatsapp_signup_url", "https://example.test/signup")


@pytest.fixture()
def sent_messages(monkeypatch):
    """Replaces the real Meta send call. Returns the list of (to, body) sent."""
    sent: list[tuple[str, str]] = []

    def fake_send(to_phone_e164: str, body: str) -> str:
        sent.append((to_phone_e164, body))
        return "wamid.fake-" + uuid.uuid4().hex

    monkeypatch.setattr("app.routers.whatsapp_webhook.send_text_message", fake_send)
    monkeypatch.setattr("app.services.whatsapp_webhook_service.send_text_message", fake_send)
    return sent


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(APP_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _post_webhook(client, payload: dict, *, signature: str | None = None, no_signature_header: bool = False):
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if not no_signature_header:
        headers["X-Hub-Signature-256"] = signature if signature is not None else _sign(body)
    return client.post("/whatsapp/webhook", content=body, headers=headers)


def _text_message_payload(wa_id: str, text: str, message_id: str | None = None) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": message_id or f"wamid.{uuid.uuid4().hex}",
                                    "from": wa_id,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def _status_event_payload() -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {"id": "wamid.status1", "status": "delivered", "recipient_id": "919876543210"}
                            ]
                        }
                    }
                ]
            }
        ]
    }


# --- Family/onboarding setup helpers -----------------------------------


def _create_family(client, child_phone: str, parent_phone: str):
    payload = {
        "child_name": "Test Child",
        "child_phone": child_phone,
        "parent_name": "Test Parent",
        "parent_phone": parent_phone,
        "parent_preferred_language": "English",
        "consent": True,
    }
    body = client.post("/families", json=payload).json()
    tokens = {invite["role"]: invite["token"] for invite in body["invites"]}
    return body["family_id"], tokens


def _join(client, token: str, phone: str):
    resp = client.post("/whatsapp/join", json={"token": token, "phone": phone})
    assert resp.status_code == 200
    return resp


# --- GET verification handshake -----------------------------------------


def test_verify_webhook_success_returns_challenge(client):
    resp = client.get(
        "/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "challenge-abc"},
    )
    assert resp.status_code == 200
    assert resp.text == "challenge-abc"


def test_verify_webhook_wrong_token_returns_403(client):
    resp = client.get(
        "/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong-token", "hub.challenge": "challenge-abc"},
    )
    assert resp.status_code == 403


def test_verify_webhook_wrong_mode_returns_403(client):
    resp = client.get(
        "/whatsapp/webhook",
        params={"hub.mode": "unsubscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "challenge-abc"},
    )
    assert resp.status_code == 403


# --- POST signature verification -----------------------------------------


def test_post_webhook_valid_signature_accepted(client, sent_messages):
    payload = _text_message_payload("14155550100", "Hi")
    resp = _post_webhook(client, payload)
    assert resp.status_code == 200


def test_post_webhook_invalid_signature_rejected(client, sent_messages):
    payload = _text_message_payload("14155550101", "Hi")
    resp = _post_webhook(client, payload, signature="sha256=" + "0" * 64)
    assert resp.status_code == 403
    assert sent_messages == []


def test_post_webhook_missing_signature_rejected(client, sent_messages):
    payload = _text_message_payload("14155550102", "Hi")
    resp = _post_webhook(client, payload, no_signature_header=True)
    assert resp.status_code == 403
    assert sent_messages == []


def test_post_webhook_status_event_ignored_safely(client, sent_messages):
    resp = _post_webhook(client, _status_event_payload())
    assert resp.status_code == 200
    assert sent_messages == []


# --- Deduplication ---------------------------------------------------------


def test_duplicate_provider_message_id_not_reprocessed(client, sent_messages):
    message_id = "wamid.duplicate-test-1"
    payload = _text_message_payload("14155550103", "Hi", message_id=message_id)

    resp1 = _post_webhook(client, payload)
    assert resp1.status_code == 200
    assert len(sent_messages) == 1

    resp2 = _post_webhook(client, payload)
    assert resp2.status_code == 200
    assert len(sent_messages) == 1  # not sent again


# --- Routing states ---------------------------------------------------------


def test_unknown_sender_gets_signup_url_and_no_family_info(client, sent_messages):
    resp = _post_webhook(client, _text_message_payload("14155559999", "Hi"))
    assert resp.status_code == 200
    assert len(sent_messages) == 1
    _, reply_body = sent_messages[0]
    assert settings.whatsapp_signup_url in reply_body


def test_registered_unverified_sender_told_to_verify(client, sent_messages):
    _, tokens = _create_family(client, "9876543001", "9876543002")
    resp = _post_webhook(client, _text_message_payload("919876543001", "Hi"))
    assert resp.status_code == 200
    assert len(sent_messages) == 1
    _, reply_body = sent_messages[0]
    assert "verif" in reply_body.lower()


def test_waiting_for_other_member_does_not_reveal_identity(client, sent_messages):
    _, tokens = _create_family(client, "9876543003", "9876543004")
    _join(client, tokens["child"], "+919876543003")

    resp = _post_webhook(client, _text_message_payload("919876543003", "Hi"))
    assert resp.status_code == 200
    _, reply_body = sent_messages[0]
    assert "parent" in reply_body.lower()
    assert "9876543004" not in reply_body
    assert "Test Parent" not in reply_body


# --- Full onboarding flow via webhook --------------------------------------


def test_onboarding_flow_through_webhook(client, sent_messages, db_session):
    child_phone, parent_phone = "9876543010", "9876543011"
    family_id, tokens = _create_family(client, child_phone, parent_phone)
    _join(client, tokens["child"], f"+91{child_phone}")
    _join(client, tokens["parent"], f"+91{parent_phone}")

    # Child says Hi first — question targets the parent, so the child should
    # just get a short acknowledgement and the parent gets messaged directly.
    _post_webhook(client, _text_message_payload(f"91{child_phone}", "Hi"))
    assert len(sent_messages) == 2
    # The proactive notify to the parent happens before the router sends the
    # child's own acknowledgement reply, so the parent's message is first.
    parent_reply = sent_messages[0][1]
    child_reply = sent_messages[1][1]
    assert sent_messages[0][0] == f"+91{parent_phone}"
    assert "diagnosed" in parent_reply.lower()
    assert "parent" in child_reply.lower()

    # Parent answers Yes to diagnosis
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Yes"))
    assert "medication" in sent_messages[-1][1].lower()

    # Parent answers Yes to medication -> medicine-time question follows
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "yes"))
    assert "time" in sent_messages[-1][1].lower()

    # Parent gives a concise medicine time -> onboarding completes
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "7 PM"))
    final_reply = sent_messages[-1][1]
    assert "complete" in final_reply.lower()
    assert "medical advice" in final_reply.lower() or "medication guidance" in final_reply.lower()

    # A further message now hits the completed-family (health_assistant) path
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Hi again"))
    assert "medical advice" in sent_messages[-1][1].lower() or "medication guidance" in sent_messages[-1][1].lower()


def test_medication_no_skips_medicine_time(client, sent_messages):
    child_phone, parent_phone = "9876543020", "9876543021"
    _, tokens = _create_family(client, child_phone, parent_phone)
    _join(client, tokens["child"], f"+91{child_phone}")
    _join(client, tokens["parent"], f"+91{parent_phone}")

    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Hi"))
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Yes"))  # diagnosed
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "No"))  # not taking medication

    final_reply = sent_messages[-1][1]
    assert "complete" in final_reply.lower()
    assert "time" not in final_reply.lower()


def test_unclear_answer_is_never_guessed(client, sent_messages):
    child_phone, parent_phone = "9876543030", "9876543031"
    _, tokens = _create_family(client, child_phone, parent_phone)
    _join(client, tokens["child"], f"+91{child_phone}")
    _join(client, tokens["parent"], f"+91{parent_phone}")

    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Hi"))
    before = len(sent_messages)
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "maybe idk"))
    after_reply = sent_messages[-1][1]
    assert len(sent_messages) == before + 1
    assert "diagnosed" in after_reply.lower()  # re-asked the same question, not guessed


def test_completed_family_reply_states_no_medical_advice(client, sent_messages):
    child_phone, parent_phone = "9876543040", "9876543041"
    _, tokens = _create_family(client, child_phone, parent_phone)
    _join(client, tokens["child"], f"+91{child_phone}")
    _join(client, tokens["parent"], f"+91{parent_phone}")
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Hi"))
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Yes"))
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "No"))

    sent_messages.clear()
    _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Hello again"))
    reply = sent_messages[-1][1]
    assert "complete" in reply.lower()
    assert "medical advice" in reply.lower() or "medication guidance" in reply.lower()


# --- Outbound Meta client failures -----------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None):
        self.status_code = status_code
        self._json_body = json_body or {"error": {"message": "redacted"}}
        self.text = "response body redacted for test"

    def json(self):
        return self._json_body


def test_meta_send_temporary_failure_retries_then_raises(monkeypatch):
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return _FakeResponse(500)

    monkeypatch.setattr(meta_client_module.httpx, "post", fake_post)
    monkeypatch.setattr(meta_client_module.time, "sleep", lambda _seconds: None)

    with pytest.raises(meta_client_module.WhatsappMetaSendError) as exc_info:
        meta_client_module.send_text_message("+919876543099", "hi")

    assert calls["count"] == meta_client_module.MAX_ATTEMPTS  # retried
    assert exc_info.value.error_code == "meta_send_provider_error"


def test_meta_send_permanent_failure_does_not_retry(monkeypatch):
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return _FakeResponse(400)

    monkeypatch.setattr(meta_client_module.httpx, "post", fake_post)
    monkeypatch.setattr(meta_client_module.time, "sleep", lambda _seconds: None)

    with pytest.raises(meta_client_module.WhatsappMetaSendError) as exc_info:
        meta_client_module.send_text_message("+919876543098", "hi")

    assert calls["count"] == 1  # no retry on a permanent 4xx
    assert exc_info.value.error_code == "meta_send_permanent_failure"


def test_meta_send_success_returns_provider_message_id(monkeypatch):
    def fake_post(*args, **kwargs):
        return _FakeResponse(200, {"messages": [{"id": "wamid.success123"}]})

    monkeypatch.setattr(meta_client_module.httpx, "post", fake_post)

    result = meta_client_module.send_text_message("+919876543097", "hi")
    assert result == "wamid.success123"


# --- Log redaction -----------------------------------------------------------


def test_no_sensitive_values_appear_in_logs(client, sent_messages, caplog):
    child_phone, parent_phone = "9876543050", "9876543051"
    _, tokens = _create_family(client, child_phone, parent_phone)
    _join(client, tokens["child"], f"+91{child_phone}")
    _join(client, tokens["parent"], f"+91{parent_phone}")

    with caplog.at_level(logging.DEBUG):
        _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Hi"))
        _post_webhook(client, _text_message_payload(f"91{parent_phone}", "Yes"))
        _post_webhook(client, _text_message_payload(f"91{parent_phone}", "No"))
        # A bad-signature attempt too, to make sure the token isn't logged either.
        _post_webhook(client, _text_message_payload(f"91{parent_phone}", "hi"), signature="sha256=bad")

    log_text = caplog.text
    assert VERIFY_TOKEN not in log_text
    assert ACCESS_TOKEN not in log_text
    assert APP_SECRET not in log_text
    assert parent_phone not in log_text
    assert child_phone not in log_text
    assert "diagnosed with diabetes" not in log_text.lower()
