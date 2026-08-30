import uuid

from app.models.onboarding_session import OnboardingSession, OnboardingSessionStatus
from app.models.whatsapp_identity import WhatsappIdentity


def create_family(client):
    payload = {
        "child_name": "Aarav Shah",
        "child_phone": "9876543210",
        "parent_name": "Ramesh Shah",
        "parent_phone": "9876500000",
        "parent_preferred_language": "Hindi",
        "consent": True,
    }
    response = client.post("/families", json=payload)
    assert response.status_code == 201
    return response.json()["family_id"]


def test_create_family_creates_whatsapp_identities_and_pending_session(client, db_session):
    family_id = uuid.UUID(create_family(client))

    identities = (
        db_session.query(WhatsappIdentity)
        .filter(WhatsappIdentity.family_id == family_id)
        .all()
    )
    assert len(identities) == 2
    phones = {i.phone_e164 for i in identities}
    assert phones == {"+919876543210", "+919876500000"}
    assert all(i.verified_at is None for i in identities)
    assert all(i.platform_user_id is None for i in identities)

    session = (
        db_session.query(OnboardingSession)
        .filter(OnboardingSession.family_id == family_id)
        .one()
    )
    assert session.status == OnboardingSessionStatus.pending
    assert session.current_step is None
    assert session.started_at is None


def test_get_onboarding_returns_pending_state(client):
    family_id = create_family(client)

    response = client.get(f"/families/{family_id}/onboarding")
    assert response.status_code == 200
    body = response.json()

    assert body["family_id"] == family_id
    assert body["status"] == "pending"
    assert body["current_step"] is None
    assert len(body["members"]) == 2
    roles = {m["role"] for m in body["members"]}
    assert roles == {"child", "parent"}


def test_get_onboarding_404_for_unknown_family(client):
    response = client.get(f"/families/{uuid.uuid4()}/onboarding")
    assert response.status_code == 404


def test_start_onboarding_transitions_to_in_progress_and_returns_question(client):
    family_id = create_family(client)

    response = client.post(f"/families/{family_id}/onboarding/start")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "in_progress"
    assert body["current_step"] == "preferred_language"
    assert body["question"]["key"] == "preferred_language"
    assert body["question"]["target"] == "parent"
    assert body["question"]["type"] == "choice"
    assert "English" in body["question"]["options"]
    assert "Other" in body["question"]["options"]

    state = client.get(f"/families/{family_id}/onboarding").json()
    assert state["status"] == "in_progress"
    assert state["current_step"] == "preferred_language"


def test_start_onboarding_twice_replays_same_question(client, db_session):
    family_id = create_family(client)

    first = client.post(f"/families/{family_id}/onboarding/start").json()
    session = (
        db_session.query(OnboardingSession)
        .filter(OnboardingSession.family_id == uuid.UUID(family_id))
        .one()
    )
    first_started_at = session.started_at

    second = client.post(f"/families/{family_id}/onboarding/start").json()

    assert second["status"] == "in_progress"
    assert second["current_step"] == first["current_step"]
    assert second["question"] == first["question"]

    db_session.refresh(session)
    assert session.started_at == first_started_at


def test_start_onboarding_404_for_unknown_family(client):
    response = client.post(f"/families/{uuid.uuid4()}/onboarding/start")
    assert response.status_code == 404
