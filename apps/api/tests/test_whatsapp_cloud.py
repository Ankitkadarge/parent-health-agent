import hashlib
import hmac
import json
import uuid

from app.core.config import settings
from app.models.family import Family, FamilyStatus
from app.models.onboarding_answer import OnboardingAnswer
from app.models.parent_health_profile import ParentHealthProfile
from app.models.whatsapp_cloud_event import (
    WhatsappCloudEvent,
    WhatsappCloudEventStatus,
)
from app.services.whatsapp_cloud_service import (
    WhatsappCloudInboundMessage,
    process_inbound_message,
)


def create_family(client):
    response = client.post(
        "/families",
        json={
            "child_name": "Aarav Shah",
            "child_phone": "+14155553001",
            "parent_name": "Ramesh Shah",
            "parent_phone": "+14155553002",
            "parent_preferred_language": "English",
            "consent": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    tokens = {invite["role"]: invite["token"] for invite in body["invites"]}
    return body["family_id"], tokens


def verify_both(client, tokens):
    child = client.post(
        "/whatsapp/join",
        json={
            "token": tokens["child"],
            "phone": "+14155553001",
        },
    )
    parent = client.post(
        "/whatsapp/join",
        json={
            "token": tokens["parent"],
            "phone": "+14155553002",
        },
    )
    assert child.status_code == 200
    assert parent.status_code == 200


def signed_payload(raw_body: bytes, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def sample_webhook_payload(
    *,
    message_id: str = "wamid.test-1",
    sender: str = "14155553002",
    text: str = "Hi",
):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-test",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "phone-number-id",
                            },
                            "messages": [
                                {
                                    "from": sender,
                                    "id": message_id,
                                    "timestamp": "1788450000",
                                    "text": {"body": text},
                                    "type": "text",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def enable_cloud(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_cloud_enabled", True)
    monkeypatch.setattr(
        settings,
        "whatsapp_cloud_verify_token",
        "verify-test-token",
    )
    monkeypatch.setattr(
        settings,
        "whatsapp_cloud_app_secret",
        "app-test-secret",
    )
    monkeypatch.setattr(
        settings,
        "whatsapp_cloud_access_token",
        "access-test-token",
    )
    monkeypatch.setattr(
        settings,
        "whatsapp_cloud_phone_number_id",
        "phone-number-id",
    )


def test_cloud_webhook_verification_returns_raw_challenge(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "whatsapp_cloud_verify_token",
        "verify-test-token",
    )

    response = client.get(
        "/whatsapp/cloud/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-test-token",
            "hub.challenge": "123456",
        },
    )

    assert response.status_code == 200
    assert response.text == "123456"
    assert response.headers["content-type"].startswith("text/plain")


def test_cloud_webhook_verification_rejects_wrong_token(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "whatsapp_cloud_verify_token",
        "verify-test-token",
    )

    response = client.get(
        "/whatsapp/cloud/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "123456",
        },
    )

    assert response.status_code == 403


def test_cloud_webhook_rejects_unsigned_payload(
    client,
    monkeypatch,
):
    enable_cloud(monkeypatch)
    raw = json.dumps(sample_webhook_payload()).encode("utf-8")

    response = client.post(
        "/whatsapp/cloud/webhook",
        content=raw,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 401


def test_cloud_webhook_accepts_signed_payload_and_queues_message(
    client,
    monkeypatch,
):
    enable_cloud(monkeypatch)
    captured = []

    def fake_background_processor(message):
        captured.append(message)

    monkeypatch.setattr(
        "app.routers.whatsapp.process_inbound_message_background",
        fake_background_processor,
    )

    raw = json.dumps(
        sample_webhook_payload(),
        separators=(",", ":"),
    ).encode("utf-8")
    response = client.post(
        "/whatsapp/cloud/webhook",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-hub-signature-256": signed_payload(
                raw,
                "app-test-secret",
            ),
        },
    )

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].provider_message_id == "wamid.test-1"
    assert captured[0].sender_wa_id == "14155553002"
    assert captured[0].text == "Hi"


def test_cloud_status_never_exposes_secrets(client):
    response = client.get("/whatsapp/cloud/status")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "meta_whatsapp_cloud_api"
    assert body["configured"] is False
    assert body["processed_events"] == 0
    serialized = response.text.lower()
    assert "access_token" not in serialized
    assert "app_secret" not in serialized
    assert "verify_token" not in serialized


def test_unknown_sender_receives_registration_link(db_session):
    sent = []

    def fake_send(to, body):
        sent.append((to, body))
        return "wamid.out-1"

    process_inbound_message(
        db_session,
        WhatsappCloudInboundMessage(
            provider_message_id="wamid.in-unknown",
            sender_wa_id="14155552671",
            message_type="text",
            text="Hi",
            phone_number_id="phone-number-id",
        ),
        send_text=fake_send,
    )

    assert len(sent) == 1
    assert "not registered" in sent[0][1].lower()
    assert "parent-health-agent.vercel.app" in sent[0][1]

    event = db_session.query(WhatsappCloudEvent).one()
    assert event.status == WhatsappCloudEventStatus.processed
    assert event.action == "unregistered"
    assert event.sender_hash != "14155552671"


def test_parent_completes_onboarding_through_cloud_messages(
    client,
    db_session,
):
    family_id, tokens = create_family(client)
    verify_both(client, tokens)

    sent = []

    def fake_send(to, body):
        sent.append((to, body))
        return f"wamid.out-{len(sent)}"

    inbound_messages = [
        WhatsappCloudInboundMessage(
            provider_message_id="wamid.in-start",
            sender_wa_id="14155553002",
            message_type="text",
            text="Hi",
            phone_number_id="phone-number-id",
        ),
        WhatsappCloudInboundMessage(
            provider_message_id="wamid.in-diabetes",
            sender_wa_id="14155553002",
            message_type="text",
            text="haan",
            phone_number_id="phone-number-id",
        ),
        WhatsappCloudInboundMessage(
            provider_message_id="wamid.in-medicine",
            sender_wa_id="14155553002",
            message_type="text",
            text="nahi",
            phone_number_id="phone-number-id",
        ),
    ]

    for message in inbound_messages:
        process_inbound_message(
            db_session,
            message,
            send_text=fake_send,
        )

    assert len(sent) == 3
    assert "diagnosed with diabetes" in sent[0][1].lower()
    assert "currently taking any medication" in sent[1][1].lower()
    assert "setup is complete" in sent[2][1].lower()

    family_uuid = uuid.UUID(family_id)
    family = db_session.get(Family, family_uuid)
    assert family.status == FamilyStatus.active

    answers = (
        db_session.query(OnboardingAnswer)
        .filter(OnboardingAnswer.family_id == family_uuid)
        .order_by(OnboardingAnswer.answered_at)
        .all()
    )
    assert [answer.value for answer in answers] == ["Yes", "No"]

    profile = (
        db_session.query(ParentHealthProfile)
        .filter(ParentHealthProfile.family_id == family_uuid)
        .one()
    )
    assert profile.diagnosed_with_diabetes is True
    assert profile.taking_medication is False
    assert profile.medicine_time is None

    events = db_session.query(WhatsappCloudEvent).all()
    assert len(events) == 3
    assert all(
        event.status == WhatsappCloudEventStatus.processed
        for event in events
    )

    # Meta can retry the same webhook. A duplicate provider message ID must not
    # submit a second answer or send a second response.
    process_inbound_message(
        db_session,
        inbound_messages[-1],
        send_text=fake_send,
    )
    assert len(sent) == 3
    assert db_session.query(WhatsappCloudEvent).count() == 3
