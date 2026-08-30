import uuid


def create_family(client, child_phone="9876543210", parent_phone="9876500000"):
    payload = {
        "child_name": "Aarav Shah",
        "child_phone": child_phone,
        "parent_name": "Ramesh Shah",
        "parent_phone": parent_phone,
        "parent_preferred_language": "English",
        "consent": True,
    }
    family_id = client.post("/families", json=payload).json()["family_id"]
    return family_id, "+919876543210", "+919876500000"


def answer(client, family_id, member_role, key, value):
    return client.post(
        f"/families/{family_id}/onboarding/answer",
        json={"member_role": member_role, "key": key, "value": value},
    )


def complete_onboarding(client, family_id):
    client.post(f"/families/{family_id}/onboarding/start")
    answer(client, family_id, "parent", "preferred_language", "English")
    answer(client, family_id, "child", "conditions", ["None"])
    answer(client, family_id, "child", "medications", "later")
    answer(client, family_id, "child", "dietary_preferences", "none")
    answer(client, family_id, "parent", "activity_level", "Moderate activity")
    answer(client, family_id, "child", "reminder_preferences", ["Daily summary"])


def test_resolve_known_child(client):
    family_id, child_phone, _ = create_family(client)

    response = client.get("/whatsapp/resolve", params={"phone": child_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["family_id"] == family_id
    assert body["role"] == "child"
    assert body["phone_e164"] == child_phone
    assert body["verified"] is False
    assert body["onboarding"]["status"] == "pending"
    assert body["onboarding"]["current_step"] is None


def test_resolve_known_parent(client):
    family_id, _, parent_phone = create_family(client)

    response = client.get("/whatsapp/resolve", params={"phone": parent_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["family_id"] == family_id
    assert body["role"] == "parent"
    assert body["phone_e164"] == parent_phone


def test_resolve_unknown_phone_is_404(client):
    response = client.get("/whatsapp/resolve", params={"phone": "+14155552671"})
    assert response.status_code == 404


def test_context_unknown_phone_is_404(client):
    response = client.get("/whatsapp/context", params={"phone": "+14155552671"})
    assert response.status_code == 404


def test_context_pending_onboarding(client):
    family_id, child_phone, _ = create_family(client)

    response = client.get("/whatsapp/context", params={"phone": child_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "start_onboarding"
    assert body["family_id"] == family_id
    assert body["role"] == "child"


def test_context_in_progress_question_targeted_to_sender(client):
    family_id, _, parent_phone = create_family(client)
    client.post(f"/families/{family_id}/onboarding/start")

    response = client.get("/whatsapp/context", params={"phone": parent_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "ask_question"
    assert body["family_id"] == family_id
    assert body["role"] == "parent"
    assert body["question"]["key"] == "preferred_language"
    assert "target_role" not in body
    assert "current_step" not in body


def test_context_in_progress_question_targeted_to_other_member(client):
    family_id, child_phone, _ = create_family(client)
    client.post(f"/families/{family_id}/onboarding/start")

    response = client.get("/whatsapp/context", params={"phone": child_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "waiting_for_other_member"
    assert body["target_role"] == "parent"
    assert body["current_step"] == "preferred_language"
    assert body["question"]["key"] == "preferred_language"
    assert "family_id" not in body
    assert "member_id" not in body


def test_context_completed_onboarding(client):
    family_id, child_phone, parent_phone = create_family(client)
    complete_onboarding(client, family_id)

    child_response = client.get("/whatsapp/context", params={"phone": child_phone})
    assert child_response.status_code == 200
    child_body = child_response.json()
    assert child_body["action"] == "health_assistant"
    assert child_body["role"] == "child"

    parent_response = client.get("/whatsapp/context", params={"phone": parent_phone})
    parent_body = parent_response.json()
    assert parent_body["action"] == "health_assistant"
    assert parent_body["role"] == "parent"


def test_resolve_rejects_invalid_phone(client):
    response = client.get("/whatsapp/resolve", params={"phone": "not-a-number"})
    assert response.status_code == 422
