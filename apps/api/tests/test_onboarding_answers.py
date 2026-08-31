import uuid

from app.models.family import Family, FamilyStatus
from app.models.member import Member, MemberRole
from app.models.onboarding_answer import OnboardingAnswer
from app.models.parent_health_profile import ParentHealthProfile


def create_started_family(client):
    payload = {
        "child_name": "Aarav Shah",
        "child_phone": "9876543210",
        "parent_name": "Ramesh Shah",
        "parent_phone": "9876500000",
        "parent_preferred_language": "English",
        "consent": True,
    }
    family_id = client.post("/families", json=payload).json()["family_id"]
    client.post(f"/families/{family_id}/onboarding/start")
    return family_id


def answer(client, family_id, member_role, key, value):
    return client.post(
        f"/families/{family_id}/onboarding/answer",
        json={"member_role": member_role, "key": key, "value": value},
    )


def test_full_onboarding_flow_completes_and_populates_profile(client, db_session):
    family_id = create_started_family(client)

    r1 = answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")
    assert r1.status_code == 200
    assert r1.json()["current_step"] == "taking_medication"

    r2 = answer(client, family_id, "parent", "taking_medication", "Yes")
    assert r2.status_code == 200
    assert r2.json()["current_step"] == "medicine_time"

    r3 = answer(client, family_id, "parent", "medicine_time", "7 PM")
    assert r3.status_code == 200
    body = r3.json()
    assert body["status"] == "completed"
    assert body["current_step"] is None
    assert body["question"] is None

    fid = uuid.UUID(family_id)
    parent = (
        db_session.query(Member)
        .filter(Member.family_id == fid, Member.role == MemberRole.parent)
        .one()
    )
    profile = (
        db_session.query(ParentHealthProfile)
        .filter(ParentHealthProfile.parent_member_id == parent.id)
        .one()
    )
    assert profile.diagnosed_with_diabetes is True
    assert profile.taking_medication is True
    assert profile.medicine_time == "7 PM"

    family = db_session.get(Family, fid)
    assert family.status == FamilyStatus.active

    answers = db_session.query(OnboardingAnswer).filter(OnboardingAnswer.family_id == fid).all()
    assert len(answers) == 3


def test_no_medication_skips_medicine_time_and_completes(client, db_session):
    family_id = create_started_family(client)

    answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")
    response = answer(client, family_id, "parent", "taking_medication", "No")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["current_step"] is None
    assert body["question"] is None

    fid = uuid.UUID(family_id)
    parent = (
        db_session.query(Member)
        .filter(Member.family_id == fid, Member.role == MemberRole.parent)
        .one()
    )
    profile = (
        db_session.query(ParentHealthProfile)
        .filter(ParentHealthProfile.parent_member_id == parent.id)
        .one()
    )
    assert profile.diagnosed_with_diabetes is True
    assert profile.taking_medication is False
    assert profile.medicine_time is None

    answers = db_session.query(OnboardingAnswer).filter(OnboardingAnswer.family_id == fid).all()
    assert len(answers) == 2


def test_answer_rejects_wrong_target_role(client):
    family_id = create_started_family(client)
    response = answer(client, family_id, "child", "diagnosed_with_diabetes", "Yes")
    assert response.status_code == 422


def test_answer_rejects_invalid_yes_no_choice(client):
    family_id = create_started_family(client)
    response = answer(client, family_id, "parent", "diagnosed_with_diabetes", "Maybe")
    assert response.status_code == 422


def test_answer_rejects_empty_medicine_time(client):
    family_id = create_started_family(client)
    answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")
    answer(client, family_id, "parent", "taking_medication", "Yes")
    response = answer(client, family_id, "parent", "medicine_time", "   ")
    assert response.status_code == 422


def test_answer_out_of_order_unanswered_key_is_conflict(client):
    family_id = create_started_family(client)
    response = answer(client, family_id, "parent", "taking_medication", "Yes")
    assert response.status_code == 409


def test_replaying_identical_answer_returns_current_state(client):
    family_id = create_started_family(client)
    first = answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")
    assert first.status_code == 200

    replay = answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")
    assert replay.status_code == 200
    body = replay.json()
    assert body["status"] == "in_progress"
    assert body["current_step"] == "taking_medication"


def test_replaying_different_answer_for_answered_step_is_conflict(client):
    family_id = create_started_family(client)
    answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")

    response = answer(client, family_id, "parent", "diagnosed_with_diabetes", "No")
    assert response.status_code == 409


def test_answer_before_start_is_conflict(client):
    payload = {
        "child_name": "A",
        "child_phone": "9876543210",
        "parent_name": "B",
        "parent_phone": "9876500000",
        "parent_preferred_language": "English",
        "consent": True,
    }
    family_id = client.post("/families", json=payload).json()["family_id"]

    response = answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")
    assert response.status_code == 409


def test_answer_after_completion_is_conflict(client):
    family_id = create_started_family(client)
    answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")
    answer(client, family_id, "parent", "taking_medication", "Yes")
    last = answer(client, family_id, "parent", "medicine_time", "7 PM")
    assert last.json()["status"] == "completed"

    response = answer(client, family_id, "parent", "medicine_time", "7 PM")
    assert response.status_code == 409


def test_answer_404_for_unknown_family(client):
    response = answer(
        client,
        str(uuid.uuid4()),
        "parent",
        "diagnosed_with_diabetes",
        "Yes",
    )
    assert response.status_code == 404
