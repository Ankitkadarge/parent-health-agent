"""Deterministic routing for inbound hosted (Meta Cloud API) WhatsApp
messages. No LLM in this path — every decision is a direct lookup against
existing onboarding/verification state via the same services the rest of
the backend already uses.

Privacy note: this module and whatsapp_webhook_event.py are the only places
that touch raw phone numbers on the webhook path. Everything persisted to
whatsapp_webhook_events uses a one-way SHA-256 hash of the E.164 number
instead, and no message body is ever stored.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.member import MemberRole
from app.models.whatsapp_webhook_event import WhatsappEventDirection, WhatsappWebhookEvent
from app.services.onboarding_questions import OnboardingQuestion
from app.services.onboarding_service import (
    OnboardingAlreadyCompletedError,
    OnboardingAnswerConflictError,
    OnboardingAnswerValidationError,
    start_onboarding,
    submit_onboarding_answer,
)
from app.models.whatsapp_identity import WhatsappIdentity
from app.services.whatsapp_meta_client import WhatsappMetaSendError, send_text_message
from app.services.whatsapp_resolution_service import (
    WhatsappIdentityNotFoundError,
    resolve_whatsapp_context,
)
from app.utils.phone import InvalidPhoneNumberError, to_e164

RATE_LIMIT_WINDOW = timedelta(seconds=60)
RATE_LIMIT_MAX_MESSAGES = 10

MEDICAL_DISCLAIMER = (
    "A reminder: I can't give medical advice, diagnoses, or medication guidance."
)

YES_WORDS = {"yes", "y", "yeah", "yep", "haan", "ha", "han", "sure", "ok", "okay"}
NO_WORDS = {"no", "n", "nope", "nahi", "nah"}


class InvalidWhatsappSenderError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_phone(phone_e164: str) -> str:
    return hashlib.sha256(phone_e164.encode("utf-8")).hexdigest()


def meta_wa_id_to_e164(wa_id: str) -> str:
    """Meta sends sender ids as bare digits (e.g. '919876543210'), not E.164."""
    raw = wa_id if wa_id.startswith("+") else f"+{wa_id}"
    try:
        return to_e164(raw)
    except InvalidPhoneNumberError as exc:
        raise InvalidWhatsappSenderError(str(exc)) from exc


def is_duplicate_event(db: Session, provider_message_id: str) -> bool:
    if not provider_message_id:
        return False
    existing = (
        db.query(WhatsappWebhookEvent)
        .filter(WhatsappWebhookEvent.provider_message_id == provider_message_id)
        .first()
    )
    return existing is not None


def is_rate_limited(db: Session, sender_hash: str) -> bool:
    window_start = _utcnow() - RATE_LIMIT_WINDOW
    count = (
        db.query(func.count(WhatsappWebhookEvent.id))
        .filter(
            WhatsappWebhookEvent.sender_hash == sender_hash,
            WhatsappWebhookEvent.direction == WhatsappEventDirection.inbound,
            WhatsappWebhookEvent.created_at >= window_start,
        )
        .scalar()
    )
    return (count or 0) >= RATE_LIMIT_MAX_MESSAGES


def _record_event(
    db: Session,
    *,
    direction: WhatsappEventDirection,
    event_type: str,
    status: str,
    provider_message_id: str | None = None,
    family_id: uuid.UUID | None = None,
    step_key: str | None = None,
    sender_hash: str | None = None,
    latency_ms: int | None = None,
    error_code: str | None = None,
    completed: bool = False,
) -> None:
    event = WhatsappWebhookEvent(
        provider_message_id=provider_message_id,
        family_id=family_id,
        direction=direction,
        event_type=event_type,
        step_key=step_key,
        status=status,
        sender_hash=sender_hash,
        latency_ms=latency_ms,
        error_code=error_code,
        completed_at=_utcnow() if completed else None,
    )
    db.add(event)
    db.commit()


def _normalize_yes_no(raw_text: str) -> str | None:
    normalized = raw_text.strip().lower()
    if normalized in YES_WORDS:
        return "Yes"
    if normalized in NO_WORDS:
        return "No"
    return None


def _normalize_medicine_time(raw_text: str) -> str | None:
    text = raw_text.strip()
    if not text or len(text) > 20:
        return None
    return text


def _normalize_answer(question: OnboardingQuestion, raw_text: str) -> str | None:
    if question.type == "choice" and question.options == ["Yes", "No"]:
        return _normalize_yes_no(raw_text)
    if question.key == "medicine_time":
        return _normalize_medicine_time(raw_text)
    return raw_text.strip() or None


def _question_prompt(question: OnboardingQuestion) -> str:
    if question.type == "choice" and question.options:
        return f"{question.prompt} ({' / '.join(question.options)})"
    return question.prompt


def _role_label(role: str) -> str:
    return "your child" if role == MemberRole.child.value else "the parent"


def process_inbound_text_message(
    db: Session,
    *,
    sender_wa_id: str,
    body_text: str,
    provider_message_id: str,
) -> str | None:
    """Route one inbound text message and return the reply text to send, or
    None if nothing should be sent (duplicate delivery or rate-limited).
    """
    start = _utcnow()

    try:
        sender_e164 = meta_wa_id_to_e164(sender_wa_id)
    except InvalidWhatsappSenderError:
        return None

    sender_hash = hash_phone(sender_e164)

    if is_duplicate_event(db, provider_message_id):
        return None

    if is_rate_limited(db, sender_hash):
        _record_event(
            db,
            direction=WhatsappEventDirection.inbound,
            event_type="text",
            status="rate_limited",
            provider_message_id=provider_message_id,
            sender_hash=sender_hash,
        )
        return None

    reply, family_id, step_key, status = _route(db, sender_e164, body_text.strip())

    latency_ms = int((_utcnow() - start).total_seconds() * 1000)
    _record_event(
        db,
        direction=WhatsappEventDirection.inbound,
        event_type="text",
        status=status,
        provider_message_id=provider_message_id,
        family_id=family_id,
        step_key=step_key,
        sender_hash=sender_hash,
        latency_ms=latency_ms,
        completed=True,
    )
    return reply


def _notify_target_member(
    db: Session, family_id: uuid.UUID, target_role: str, question: OnboardingQuestion
) -> None:
    identity = (
        db.query(WhatsappIdentity)
        .filter(WhatsappIdentity.family_id == family_id, WhatsappIdentity.role == target_role)
        .first()
    )
    if identity is None:
        return
    try:
        send_text_message(identity.phone_e164, _question_prompt(question))
    except WhatsappMetaSendError as exc:
        record_outbound_result(
            db, sender_hash=hash_phone(identity.phone_e164), status="send_failed", error_code=exc.error_code
        )
        return
    record_outbound_result(db, sender_hash=hash_phone(identity.phone_e164), status="sent")


def record_outbound_result(
    db: Session,
    *,
    sender_hash: str,
    status: str,
    error_code: str | None = None,
) -> None:
    _record_event(
        db,
        direction=WhatsappEventDirection.outbound,
        event_type="text",
        status=status,
        sender_hash=sender_hash,
        error_code=error_code,
        completed=True,
    )


def _route(
    db: Session, sender_e164: str, body_text: str
) -> tuple[str, uuid.UUID | None, str | None, str]:
    try:
        context: dict[str, Any] = resolve_whatsapp_context(db, sender_e164)
    except WhatsappIdentityNotFoundError:
        reply = (
            "I don't have a family set up for this number yet. "
            f"You can get started here: {settings.whatsapp_signup_url}"
        )
        return reply, None, None, "unknown_sender"

    action = context["action"]
    family_id = context.get("family_id")

    if action == "verify_or_join":
        reply = "This number is registered, but you still need to finish the verification link we sent."
        return reply, family_id, None, "registered_unverified"

    if action == "waiting_for_verification":
        waiting_role = context.get("waiting_on_role")
        who = _role_label(waiting_role) if waiting_role else "the other family member"
        reply = f"Almost there — we're just waiting for {who} to complete their verification link."
        return reply, family_id, None, "waiting_for_verification"

    if action == "start_onboarding":
        role = MemberRole(context["role"])
        _, question = start_onboarding(db, family_id)

        if question.target == role.value:
            reply = _question_prompt(question)
            return reply, family_id, question.key, "onboarding_started"

        # The first question isn't for whoever just messaged us (e.g. the
        # child said "Hi" first, but the question targets the parent) — tell
        # the sender we're waiting, and proactively send the real question
        # to the correct family member instead of guessing who to ask.
        _notify_target_member(db, family_id, question.target, question)
        who = _role_label(question.target)
        reply = f"Got it — I've started your family's setup and sent the first question to {who}."
        return reply, family_id, question.key, "onboarding_started_notified_other"

    if action == "ask_question":
        role = MemberRole(context["role"])
        question: OnboardingQuestion = context["question"]
        normalized = _normalize_answer(question, body_text)
        if normalized is None:
            reply = "Sorry, I didn't quite catch that. " + _question_prompt(question)
            return reply, family_id, question.key, "unclear_answer"

        try:
            _, next_question = submit_onboarding_answer(
                db, family_id, role, question.key, normalized
            )
        except OnboardingAnswerValidationError:
            reply = "Sorry, I didn't quite catch that. " + _question_prompt(question)
            return reply, family_id, question.key, "invalid_answer"
        except OnboardingAnswerConflictError:
            reply = "That doesn't match what you told us earlier for this question."
            return reply, family_id, question.key, "answer_conflict"
        except OnboardingAlreadyCompletedError:
            reply = "Your family's setup is already complete. " + MEDICAL_DISCLAIMER
            return reply, family_id, question.key, "already_completed"

        if next_question is not None:
            reply = _question_prompt(next_question)
            return reply, family_id, next_question.key, "answer_recorded"

        reply = "That's everything — your family's WhatsApp setup is complete. " + MEDICAL_DISCLAIMER
        return reply, family_id, question.key, "onboarding_completed"

    if action == "waiting_for_other_member":
        target_role = context.get("target_role")
        who = _role_label(target_role) if target_role else "the other family member"
        reply = f"We're waiting on {who} to answer the current question before we continue."
        return reply, None, context.get("current_step"), "waiting_for_other_member"

    # action == "health_assistant"
    reply = "Your family's setup is complete. " + MEDICAL_DISCLAIMER
    return reply, family_id, None, "health_assistant"
