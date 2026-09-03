import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.config import WhatsappMetaMisconfiguredError, settings
from app.core.db import get_db
from app.services.whatsapp_meta_client import WhatsappMetaSendError, send_text_message
from app.services.whatsapp_webhook_service import (
    hash_phone,
    meta_wa_id_to_e164,
    process_inbound_text_message,
    record_outbound_result,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhook"])


def _require_meta_configured() -> None:
    try:
        settings.assert_whatsapp_meta_configured()
    except WhatsappMetaMisconfiguredError as exc:
        # Safe to log: this is our own config-key names, never a secret value.
        logger.error("WhatsApp webhook called while misconfigured: %s", exc)
        raise HTTPException(status_code=503, detail="WhatsApp hosted onboarding is not configured.")


@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
) -> Response:
    _require_meta_configured()

    expected_token = settings.whatsapp_webhook_verify_token or ""
    token_matches = hmac.compare_digest(hub_verify_token.encode("utf-8"), expected_token.encode("utf-8"))

    if hub_mode != "subscribe" or not token_matches:
        # Deliberately no detail about *why* it failed, and the token itself
        # is never logged.
        raise HTTPException(status_code=403, detail="Verification failed.")

    return Response(content=hub_challenge, media_type="text/plain")


@router.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_meta_configured()

    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256", "")

    app_secret = settings.whatsapp_meta_app_secret or ""
    expected_signature = "sha256=" + hmac.new(
        app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()

    if not signature_header or not hmac.compare_digest(signature_header, expected_signature):
        logger.warning("WhatsApp webhook rejected: invalid or missing signature")
        raise HTTPException(status_code=403, detail="Invalid signature.")

    payload = await request.json()
    _dispatch_payload(db, payload)

    # Always 200 once the signature is valid — Meta retries aggressively on
    # non-200s, and per-message failures are handled (and logged) inside
    # _dispatch_payload instead.
    return {"status": "ok"}


def _dispatch_payload(db: Session, payload: dict) -> None:
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}

            for message in value.get("messages", []) or []:
                _handle_inbound_message(db, message)

            # Delivery/read status callbacks — nothing to do, must not error.
            for _status in value.get("statuses", []) or []:
                continue


def _handle_inbound_message(db: Session, message: dict) -> None:
    message_type = message.get("type")
    provider_message_id = str(message.get("id") or "")
    sender_wa_id = str(message.get("from") or "")

    if message_type != "text":
        # Non-text inbound (image, audio, location, ...) — safely ignored.
        return

    body_text = str((message.get("text") or {}).get("body") or "")
    if not body_text or not sender_wa_id or not provider_message_id:
        return

    reply_text = process_inbound_text_message(
        db,
        sender_wa_id=sender_wa_id,
        body_text=body_text,
        provider_message_id=provider_message_id,
    )
    if reply_text is None:
        return

    try:
        sender_e164 = meta_wa_id_to_e164(sender_wa_id)
    except Exception:
        return

    try:
        send_text_message(sender_e164, reply_text)
    except WhatsappMetaSendError as exc:
        # Never expose the provider error to the user — just log a safe,
        # internal error code and move on. The user simply won't get a reply
        # this round; Meta's own retry (or their next message) will recover.
        logger.error("Outbound WhatsApp send failed: %s", exc.error_code)
        record_outbound_result(
            db, sender_hash=hash_phone(sender_e164), status="send_failed", error_code=exc.error_code
        )
        return

    record_outbound_result(db, sender_hash=hash_phone(sender_e164), status="sent")
