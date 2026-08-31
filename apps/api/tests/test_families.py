import uuid

from app.models.family import Family, FamilyStatus
from app.models.family_invite import FamilyInvite
from app.models.member import Member, MemberRole


def valid_payload(**overrides):
    payload = {
        "child_name": "Aarav Shah",
        "child_phone": "9876543210",
        "parent_name": "Ramesh Shah",
        "parent_phone": "9876500000",
        "parent_preferred_language": "Hindi",
        "consent": True,
    }
    payload.update(overrides)
    return payload


def test_create_family_success(client, db_session):
    response = client.post("/families", json=valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert "family_id" in body

    family_id = uuid.UUID(body["family_id"])
    family = db_session.get(Family, family_id)
    assert family is not None
    assert family.status == FamilyStatus.pending_verification

    assert len(body["invites"]) == 2
    roles = {invite["role"] for invite in body["invites"]}
    assert roles == {"child", "parent"}
    for invite in body["invites"]:
        assert invite["token"] in invite["invite_url"]

    invites = db_session.query(FamilyInvite).filter(FamilyInvite.family_id == family_id).all()
    assert len(invites) == 2
    assert all(invite.used_at is None for invite in invites)

    members = db_session.query(Member).filter(Member.family_id == family.id).all()
    assert len(members) == 2

    child = next(m for m in members if m.role == MemberRole.child)
    parent = next(m for m in members if m.role == MemberRole.parent)

    assert child.name == "Aarav Shah"
    assert child.phone_e164 == "+919876543210"
    assert child.preferred_language is None

    assert parent.name == "Ramesh Shah"
    assert parent.phone_e164 == "+919876500000"
    assert parent.preferred_language == "Hindi"


def test_create_family_without_consent_is_rejected(client):
    response = client.post("/families", json=valid_payload(consent=False))
    assert response.status_code == 422


def test_create_family_with_invalid_phone_is_rejected(client):
    response = client.post("/families", json=valid_payload(child_phone="not-a-number"))
    assert response.status_code == 422


def test_create_family_with_already_e164_phone(client, db_session):
    response = client.post(
        "/families",
        json=valid_payload(parent_phone="+14155552671", child_phone="+14155552672"),
    )
    assert response.status_code == 201
    body = response.json()
    family_id = uuid.UUID(body["family_id"])

    members = db_session.query(Member).filter(Member.family_id == family_id).all()
    phones = {m.phone_e164 for m in members}
    assert phones == {"+14155552671", "+14155552672"}


def test_create_family_with_new_unique_numbers_returns_201(client):
    response = client.post(
        "/families",
        json=valid_payload(child_phone="+14155553001", parent_phone="+14155553002"),
    )
    assert response.status_code == 201
    assert "family_id" in response.json()


def test_duplicate_child_phone_returns_409_not_500(client, db_session):
    first = client.post(
        "/families",
        json=valid_payload(child_phone="+14155553010", parent_phone="+14155553011"),
    )
    assert first.status_code == 201

    second = client.post(
        "/families",
        json=valid_payload(child_phone="+14155553010", parent_phone="+14155553099"),
    )
    assert second.status_code == 409
    assert second.json() == {"detail": "This WhatsApp number is already connected to a family."}

    # No trace of SQL/exception internals leaked to the client.
    body_text = second.text.lower()
    assert "sqlalchemy" not in body_text
    assert "integrityerror" not in body_text
    assert "unique constraint" not in body_text

    # The rejected attempt left no partial data behind.
    families = db_session.query(Family).all()
    assert len(families) == 1


def test_duplicate_parent_phone_returns_409_not_500(client, db_session):
    first = client.post(
        "/families",
        json=valid_payload(child_phone="+14155553020", parent_phone="+14155553021"),
    )
    assert first.status_code == 201

    second = client.post(
        "/families",
        json=valid_payload(child_phone="+14155553098", parent_phone="+14155553021"),
    )
    assert second.status_code == 409
    assert second.json() == {"detail": "This WhatsApp number is already connected to a family."}

    families = db_session.query(Family).all()
    assert len(families) == 1


def test_submitting_the_same_family_twice_returns_409_on_second_attempt(client, db_session):
    payload = valid_payload(child_phone="+14155553030", parent_phone="+14155553031")

    first = client.post("/families", json=payload)
    assert first.status_code == 201

    second = client.post("/families", json=payload)
    assert second.status_code == 409
    assert second.json() == {"detail": "This WhatsApp number is already connected to a family."}

    families = db_session.query(Family).all()
    assert len(families) == 1
    members = db_session.query(Member).all()
    assert len(members) == 2
