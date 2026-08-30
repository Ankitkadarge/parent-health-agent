import uuid
from datetime import datetime, timedelta, timezone

from app.models.family import Family, FamilyStatus
from app.models.family_invite import FamilyInvite
from app.models.whatsapp_identity import WhatsappIdentity


def create_family(client, child_phone="9876543210", parent_phone="9876500000"):
    payload = {
        "child_name": "Aarav Shah",
        "child_phone": child_phone,
        "parent_name": "Ramesh Shah",
        "parent_phone": parent_phone,
        "parent_preferred_language": "English",
        "consent": True,
    }
    body = client.post("/families", json=payload).json()
    tokens = {invite["role"]: invite["token"] for invite in body["invites"]}
    return body["family_id"], "+919876543210", "+919876500000", tokens


def join(client, token, phone):
    return client.post("/whatsapp/join", json={"token": token, "phone": phone})


def test_join_verifies_one_member_family_stays_pending_verification(client, db_session):
    family_id, child_phone, _, tokens = create_family(client)

    response = join(client, tokens["child"], child_phone)
    assert response.status_code == 200
    body = response.json()

    assert body["family_id"] == family_id
    assert body["role"] == "child"
    assert body["verified_at"] is not None
    assert body["family_status"] == "pending_verification"

    fid = uuid.UUID(family_id)
    identity = (
        db_session.query(WhatsappIdentity)
        .filter(WhatsappIdentity.family_id == fid, WhatsappIdentity.phone_e164 == child_phone)
        .one()
    )
    assert identity.verified_at is not None

    family = db_session.get(Family, fid)
    assert family.status == FamilyStatus.pending_verification


def test_join_both_members_transitions_family_to_onboarding(client, db_session):
    family_id, child_phone, parent_phone, tokens = create_family(client)

    join(client, tokens["child"], child_phone)
    response = join(client, tokens["parent"], parent_phone)

    assert response.status_code == 200
    assert response.json()["family_status"] == "onboarding"

    family = db_session.get(Family, uuid.UUID(family_id))
    assert family.status == FamilyStatus.onboarding


def test_join_with_unknown_token_is_404(client):
    _, child_phone, _, _ = create_family(client)
    response = join(client, "not-a-real-token", child_phone)
    assert response.status_code == 404


def test_join_with_wrong_phone_is_403(client):
    _, _, parent_phone, tokens = create_family(client)
    response = join(client, tokens["child"], parent_phone)
    assert response.status_code == 403


def test_join_twice_with_same_token_is_409(client):
    _, child_phone, _, tokens = create_family(client)
    first = join(client, tokens["child"], child_phone)
    assert first.status_code == 200

    second = join(client, tokens["child"], child_phone)
    assert second.status_code == 409


def test_join_with_expired_token_is_410(client, db_session):
    _, child_phone, _, tokens = create_family(client)

    invite = db_session.query(FamilyInvite).filter(FamilyInvite.token == tokens["child"]).one()
    invite.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    db_session.commit()

    response = join(client, tokens["child"], child_phone)
    assert response.status_code == 410


def test_join_rejects_invalid_phone(client):
    _, _, _, tokens = create_family(client)
    response = join(client, tokens["child"], "not-a-number")
    assert response.status_code == 422
