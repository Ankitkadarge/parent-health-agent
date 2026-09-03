"""End-to-end (mocked) hosted WhatsApp onboarding: signup -> verify both
members -> inbound webhook "Hi" -> Q1 -> Yes/No -> Q2 -> medicine-time (or
skip) -> completed family. Nothing here touches Swagger, a terminal, local
Hermes, or the database directly — only the public HTTP surface a real
website + Meta webhook would use.
"""

import hashlib
import hmac
import json
import uuid

import pytest

from app.core.config import settings
from app.models.family import Family, FamilyStatus

APP_SECRET = "e2e-test-app-secret"


@pytest.fixture(autouse=True)
def meta_configured(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_provider", "meta")
    monkeypatch.setattr(settings, "whatsapp_meta_phone_number_id", "1234567890")
    monkeypatch.setattr(settings, "whatsapp_meta_access_token", "e2e-access-token")
    monkeypatch.setattr(settings, "whatsapp_meta_app_secret", APP_SECRET)
    monkeypatch.setattr(settings, "whatsapp_webhook_verify_token", "e2e-verify-token")


@pytest.fixture()
def sent_messages(monkeypatch):
    sent: list[tuple[str, str]] = []

    def fake_send(to_phone_e164: str, body: str) -> str:
        sent.append((to_phone_e164, body))
        return "wamid.e2e-" + uuid.uuid4().hex

    monkeypatch.setattr("app.routers.whatsapp_webhook.send_text_message", fake_send)
    monkeypatch.setattr("app.services.whatsapp_webhook_service.send_text_message", fake_send)
    return sent


def _post_webhook(client, wa_id: str, text: str):
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": f"wamid.{uuid.uuid4().hex}",
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
    body = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(APP_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/whatsapp/webhook",
        content=body,
        headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    return resp


def test_full_onboarding_e2e_through_hosted_webhook_only(client, sent_messages, db_session):
    child_phone, parent_phone = "9123450010", "9123450011"

    # 1. Signup (the public website flow)
    signup = client.post(
        "/families",
        json={
            "child_name": "E2E Child",
            "child_phone": child_phone,
            "parent_name": "E2E Parent",
            "parent_phone": parent_phone,
            "parent_preferred_language": "English",
            "consent": True,
        },
    )
    assert signup.status_code == 201
    body = signup.json()
    family_id = body["family_id"]
    tokens = {invite["role"]: invite["token"] for invite in body["invites"]}

    # 2. Verify both members via their invite links
    assert client.post(
        "/whatsapp/join", json={"token": tokens["child"], "phone": f"+91{child_phone}"}
    ).status_code == 200
    assert client.post(
        "/whatsapp/join", json={"token": tokens["parent"], "phone": f"+91{parent_phone}"}
    ).status_code == 200

    # 3. Inbound "Hi" from the parent over the hosted webhook — no LLM, no
    #    Hermes, no terminal involved from here on.
    _post_webhook(client, f"91{parent_phone}", "Hi")
    assert "diagnosed" in sent_messages[-1][1].lower()

    # 4. Question 1
    _post_webhook(client, f"91{parent_phone}", "Yes")
    assert "medication" in sent_messages[-1][1].lower()

    # 5. Question 2 -> Yes leads into the medicine-time question
    _post_webhook(client, f"91{parent_phone}", "Yes")
    assert "time" in sent_messages[-1][1].lower()

    # 6. Medicine-time answer -> completion
    _post_webhook(client, f"91{parent_phone}", "7 PM")
    assert "complete" in sent_messages[-1][1].lower()

    # 7. Assert the family is genuinely active in the database — the only
    #    database touch in this whole test is this read-only assertion.
    family = db_session.get(Family, uuid.UUID(family_id))
    assert family.status == FamilyStatus.active


def test_full_onboarding_e2e_medication_no_skips_time_question(client, sent_messages, db_session):
    child_phone, parent_phone = "9123450020", "9123450021"

    signup = client.post(
        "/families",
        json={
            "child_name": "E2E Child 2",
            "child_phone": child_phone,
            "parent_name": "E2E Parent 2",
            "parent_phone": parent_phone,
            "parent_preferred_language": "English",
            "consent": True,
        },
    )
    body = signup.json()
    family_id = body["family_id"]
    tokens = {invite["role"]: invite["token"] for invite in body["invites"]}

    client.post("/whatsapp/join", json={"token": tokens["child"], "phone": f"+91{child_phone}"})
    client.post("/whatsapp/join", json={"token": tokens["parent"], "phone": f"+91{parent_phone}"})

    _post_webhook(client, f"91{parent_phone}", "Hi")
    _post_webhook(client, f"91{parent_phone}", "Yes")  # diagnosed
    _post_webhook(client, f"91{parent_phone}", "No")  # not taking medication -> skip time question

    assert "complete" in sent_messages[-1][1].lower()
    assert "time" not in sent_messages[-1][1].lower()

    family = db_session.get(Family, uuid.UUID(family_id))
    assert family.status == FamilyStatus.active
