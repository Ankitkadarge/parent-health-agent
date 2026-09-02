import httpx

from app.core.config import settings


class WhatsappGroupCreationError(Exception):
    pass


def _phone_to_jid(phone_e164: str) -> str:
    return f"{phone_e164.lstrip('+')}@s.whatsapp.net"


def create_whatsapp_group(subject: str, member_phones_e164: list[str]) -> str:
    """Create a WhatsApp group via the local bridge. Raises
    WhatsappGroupCreationError on any failure — callers decide whether that's
    fatal (it generally shouldn't be: family creation must not depend on the
    WhatsApp transport being up).
    """
    participants = [_phone_to_jid(phone) for phone in member_phones_e164]

    try:
        response = httpx.post(
            f"{settings.whatsapp_bridge_base_url}/group-create",
            json={"subject": subject, "participants": participants},
            timeout=65.0,
        )
    except httpx.HTTPError as exc:
        raise WhatsappGroupCreationError(f"Could not reach WhatsApp bridge: {exc}") from exc

    if response.status_code != 200:
        detail = response.json().get("error", response.text) if response.content else response.text
        raise WhatsappGroupCreationError(f"Bridge returned {response.status_code}: {detail}")

    body = response.json()
    if not body.get("success") or not body.get("groupId"):
        raise WhatsappGroupCreationError(f"Unexpected bridge response: {body}")

    return body["groupId"]
