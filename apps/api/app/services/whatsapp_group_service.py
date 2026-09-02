import httpx

from app.core.config import settings


class WhatsappGroupCreationError(Exception):
    pass


def _phone_to_jid(phone_e164: str) -> str:
    return f"{phone_e164.lstrip('+')}@s.whatsapp.net"


def create_whatsapp_group(subject: str, member_phones_e164: list[str]) -> str:
    """Create a WhatsApp group through the optional external bridge."""
    base_url = settings.normalized_bridge_base_url
    if not base_url:
        raise WhatsappGroupCreationError("WhatsApp bridge is not configured.")

    clean_subject = subject.strip()[:100]
    participants = list(
        dict.fromkeys(_phone_to_jid(phone) for phone in member_phones_e164)
    )

    if not clean_subject:
        raise WhatsappGroupCreationError("WhatsApp group subject is empty.")
    if len(participants) < 2:
        raise WhatsappGroupCreationError(
            "At least two distinct participants are required."
        )

    total_timeout = settings.whatsapp_group_timeout_seconds
    timeout = httpx.Timeout(
        total_timeout,
        connect=min(5.0, total_timeout),
    )

    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.post(
                f"{base_url}/group-create",
                json={"subject": clean_subject, "participants": participants},
            )
    except httpx.TimeoutException as exc:
        raise WhatsappGroupCreationError("WhatsApp bridge timed out.") from exc
    except httpx.HTTPError as exc:
        raise WhatsappGroupCreationError(
            "Could not reach the WhatsApp bridge."
        ) from exc

    if response.status_code != 200:
        raise WhatsappGroupCreationError(
            f"WhatsApp bridge returned HTTP {response.status_code}."
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise WhatsappGroupCreationError(
            "WhatsApp bridge returned invalid JSON."
        ) from exc

    if not isinstance(body, dict) or not body.get("success") or not body.get("groupId"):
        raise WhatsappGroupCreationError(
            "WhatsApp bridge returned an unexpected response."
        )

    return str(body["groupId"])
