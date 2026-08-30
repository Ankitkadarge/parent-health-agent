import uuid

from app.models.member import Member, MemberRole
from app.models.onboarding_answer import OnboardingAnswer
from app.models.onboarding_session import OnboardingSessionStatus
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

    r1 = answer(client, family_id, "parent", "preferred_language", "Hindi")
    assert r1.status_code == 200
    assert r1.json()["current_step"] == "conditions"

    r2 = answer(client, family_id, "child", "conditions", ["Diabetes", "Thyroid"])
    assert r2.status_code == 200
    assert r2.json()["current_step"] == "medications"

    r3 = answer(client, family_id, "child", "medications", "Metformin every morning")
    assert r3.status_code == 200
    assert r3.json()["current_step"] == "dietary_preferences"

    r4 = answer(client, family_id, "child", "dietary_preferences", "No sugar")
    assert r4.status_code == 200
    assert r4.json()["current_step"] == "activity_level"

    r5 = answer(client, family_id, "parent", "activity_level", "Light activity")
    assert r5.status_code == 200
    assert r5.json()["current_step"] == "reminder_preferences"

    r6 = answer(
        client,
        family_id,
        "child",
        "reminder_preferences",
        ["Medication reminders", "Daily summary"],
    )
    assert r6.status_code == 200
    body = r6.json()
    assert body["status"] == "completed"
    assert body["current_step"] is None
    assert body["question"] is None

    fid = uuid.UUID(family_id)
    parent = (
        db_session.query(Member)
        .filter(Member.family_id == fid, Member.role == MemberRole.parent)
        .one()
    )
    assert parent.preferred_language == "Hindi"

    profile = (
        db_session.query(ParentHealthProfile)
        .filter(ParentHealthProfile.parent_member_id == parent.id)
        .one()
    )
    assert profile.conditions == ["Diabetes", "Thyroid"]
    assert profile.medications == "Metformin every morning"
    assert profile.dietary_preferences == "No sugar"
    assert profile.activity_level == "Light activity"
    assert profile.reminder_preferences == ["Daily summary", "Medication reminders"]

    answers = db_session.query(OnboardingAnswer).filter(OnboardingAnswer.family_id == fid).all()
    assert len(answers) == 6


def test_answer_rejects_wrong_target_role(client):
    family_id = create_started_family(client)
    response = answer(client, family_id, "child", "preferred_language", "Hindi")
    assert response.status_code == 422


def test_answer_rejects_invalid_choice(client):
    family_id = create_started_family(client)
    response = answer(client, family_id, "parent", "preferred_language", "Klingon")
    assert response.status_code == 422


def test_answer_rejects_invalid_multi_choice_option(client):
    family_id = create_started_family(client)
    answer(client, family_id, "parent", "preferred_language", "English")
    response = answer(client, family_id, "child", "conditions", ["Diabetes", "Not a real thing"])
    assert response.status_code == 422


def test_answer_rejects_empty_free_text(client):
    family_id = create_started_family(client)
    answer(client, family_id, "parent", "preferred_language", "English")
    answer(client, family_id, "child", "conditions", ["None"])
    response = answer(client, family_id, "child", "medications", "   ")
    assert response.status_code == 422


def test_answer_out_of_order_unanswered_key_is_conflict(client):
    family_id = create_started_family(client)
    response = answer(client, family_id, "child", "conditions", ["None"])
    assert response.status_code == 409


def test_replaying_identical_answer_returns_current_state(client):
    family_id = create_started_family(client)
    first = answer(client, family_id, "parent", "preferred_language", "Hindi")
    assert first.status_code == 200

    replay = answer(client, family_id, "parent", "preferred_language", "Hindi")
    assert replay.status_code == 200
    body = replay.json()
    assert body["status"] == "in_progress"
    assert body["current_step"] == "conditions"


def test_replaying_different_answer_for_answered_step_is_conflict(client):
    family_id = create_started_family(client)
    answer(client, family_id, "parent", "preferred_language", "Hindi")

    response = answer(client, family_id, "parent", "preferred_language", "Marathi")
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

    response = answer(client, family_id, "parent", "preferred_language", "Hindi")
    assert response.status_code == 409


def test_answer_after_completion_is_conflict(client, db_session):
    family_id = create_started_family(client)
    answer(client, family_id, "parent", "preferred_language", "English")
    answer(client, family_id, "child", "conditions", ["None"])
    answer(client, family_id, "child", "medications", "later")
    answer(client, family_id, "child", "dietary_preferences", "none")
    answer(client, family_id, "parent", "activity_level", "Moderate activity")
    last = answer(client, family_id, "child", "reminder_preferences", ["Daily summary"])
    assert last.json()["status"] == "completed"

    response = answer(client, family_id, "child", "reminder_preferences", ["Daily summary"])
    assert response.status_code == 409


def test_answer_404_for_unknown_family(client):
    response = answer(client, str(uuid.uuid4()), "parent", "preferred_language", "Hindi")
    assert response.status_code == 404
