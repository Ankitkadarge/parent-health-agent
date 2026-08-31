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


def verify_both(client, tokens, child_phone, parent_phone):
    assert join(client, tokens["child"], child_phone).status_code == 200
    assert join(client, tokens["parent"], parent_phone).status_code == 200


def answer(client, family_id, member_role, key, value):
    return client.post(
        f"/families/{family_id}/onboarding/answer",
        json={"member_role": member_role, "key": key, "value": value},
    )


def complete_onboarding(client, family_id):
    client.post(f"/families/{family_id}/onboarding/start")
    answer(client, family_id, "parent", "diagnosed_with_diabetes", "Yes")
    answer(client, family_id, "parent", "taking_medication", "Yes")
    answer(client, family_id, "parent", "medicine_time", "7 PM")


def test_resolve_known_child(client):
    family_id, child_phone, _, _ = create_family(client)

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
    family_id, _, parent_phone, _ = create_family(client)

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


def test_context_unverified_sender_gets_verify_or_join(client):
    family_id, child_phone, _, _ = create_family(client)

    response = client.get("/whatsapp/context", params={"phone": child_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "verify_or_join"
    assert body["family_id"] == family_id
    assert body["role"] == "child"


def test_context_waiting_for_verification_after_one_member_joins(client):
    family_id, child_phone, parent_phone, tokens = create_family(client)
    join(client, tokens["child"], child_phone)

    child_context = client.get("/whatsapp/context", params={"phone": child_phone}).json()
    assert child_context["action"] == "waiting_for_verification"
    assert child_context["waiting_on_role"] == "parent"

    parent_context = client.get("/whatsapp/context", params={"phone": parent_phone}).json()
    assert parent_context["action"] == "verify_or_join"


def test_context_start_onboarding_after_both_verified(client):
    family_id, child_phone, parent_phone, tokens = create_family(client)
    verify_both(client, tokens, child_phone, parent_phone)

    response = client.get("/whatsapp/context", params={"phone": child_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "start_onboarding"
    assert body["family_id"] == family_id
    assert body["role"] == "child"


def test_context_in_progress_question_targeted_to_sender(client):
    family_id, child_phone, parent_phone, tokens = create_family(client)
    verify_both(client, tokens, child_phone, parent_phone)
    client.post(f"/families/{family_id}/onboarding/start")

    response = client.get("/whatsapp/context", params={"phone": parent_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "ask_question"
    assert body["family_id"] == family_id
    assert body["role"] == "parent"
    assert body["question"]["key"] == "diagnosed_with_diabetes"
    assert "target_role" not in body
    assert "current_step" not in body


def test_context_in_progress_question_targeted_to_other_member(client):
    family_id, child_phone, parent_phone, tokens = create_family(client)
    verify_both(client, tokens, child_phone, parent_phone)
    client.post(f"/families/{family_id}/onboarding/start")

    response = client.get("/whatsapp/context", params={"phone": child_phone})
    assert response.status_code == 200
    body = response.json()

    assert body["action"] == "waiting_for_other_member"
    assert body["target_role"] == "parent"
    assert body["current_step"] == "diagnosed_with_diabetes"
    assert body["question"]["key"] == "diagnosed_with_diabetes"
    assert "family_id" not in body
    assert "member_id" not in body


def test_context_completed_onboarding(client):
    family_id, child_phone, parent_phone, tokens = create_family(client)
    verify_both(client, tokens, child_phone, parent_phone)
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
