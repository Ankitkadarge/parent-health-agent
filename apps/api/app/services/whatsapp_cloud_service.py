from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
import unicodedata
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.family import Family, FamilyStatus
from app.models.member import MemberRole
from app.models.whatsapp_cloud_event import (
    WhatsappCloudEvent,
    WhatsappCloudEventStatus,
)
from app.models.whatsapp_identity import WhatsappIdentity
from app.services.onboarding_questions import OnboardingQuestion
from app.services.onboarding_service import (
    OnboardingAlreadyCompletedError,
    OnboardingAnswerConflictError,
    OnboardingAnswerValidationError,
    OnboardingNotStartedError,
    OnboardingStepMismatchError,
    start_onboarding,
    submit_onboarding_answer,
)
from app.services.whatsapp_resolution_service import (
    WhatsappIdentityNotFoundError,
    resolve_whatsapp_context,
    resolve_whatsapp_identity,
)
from app.utils.phone import InvalidPhoneNumberError, to_e164

logger = logging.getLogger(__name__)


class WhatsappCloudConfigurationError(RuntimeError):
    pass


class WhatsappCloudSendError(RuntimeError):
    pass


@dataclass(frozen=True)
class WhatsappCloudInboundMessage:
    provider_message_id: str
    sender_wa_id: str
    message_type: str
    text: str | None
    phone_number_id: str | None


SendText = Callable[[str, str], str]


_YES_VALUES = {
    "yes",
    "y",
    "yeah",
    "yep",
    "haan",
    "han",
    "haa",
    "ha",
    "ji haan",
    "ji han",
    "हाँ",
    "हां",
    "जी हाँ",
    "जी हां",
    "हो",
    "होय",
    "હા",
    "ஆம்",
    "ஆமாம்",
    "అవును",
    "ಹೌದು",
    "হ্যাঁ",
    "হ্যা",
    "ਹਾਂ",
}
_NO_VALUES = {
    "no",
    "n",
    "nope",
    "nah",
    "nahi",
    "nahin",
    "na",
    "नहीं",
    "नही",
    "न",
    "नाही",
    "ना",
    "ના",
    "இல்லை",
    "கிடையாது",
    "కాదు",
    "లేదు",
    "ಇಲ್ಲ",
    "না",
    "ਨਹੀਂ",
    "ਨਹੀ",
}


def verify_webhook_signature(
    raw_body: bytes,
    signature_header: str | None,
) -> bool:
    secret = settings.whatsapp_cloud_app_secret
    if not secret or not signature_header:
        return False

    supplied = signature_header.strip()
    if not supplied.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, supplied)


def extract_inbound_messages(payload: Any) -> list[WhatsappCloudInboundMessage]:
    if not isinstance(payload, dict):
        return []
    if payload.get("object") != "whatsapp_business_account":
        return []

    extracted: list[WhatsappCloudInboundMessage] = []

    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []):
            if not isinstance(change, dict) or change.get("field") != "messages":
                continue

            value = change.get("value")
            if not isinstance(value, dict):
                continue

            metadata = value.get("metadata")
            phone_number_id = (
                metadata.get("phone_number_id")
                if isinstance(metadata, dict)
                else None
            )
            configured_phone_id = settings.whatsapp_cloud_phone_number_id
            if (
                configured_phone_id
                and phone_number_id
                and str(phone_number_id) != configured_phone_id
            ):
                continue

            for message in value.get("messages", []):
                if not isinstance(message, dict):
                    continue

                provider_message_id = message.get("id")
                sender_wa_id = message.get("from")
                message_type = message.get("type")
                if not all(
                    isinstance(item, str) and item.strip()
                    for item in (
                        provider_message_id,
                        sender_wa_id,
                        message_type,
                    )
                ):
                    continue

                text: str | None = None
                text_object = message.get("text")
                if message_type == "text" and isinstance(text_object, dict):
                    body = text_object.get("body")
                    if isinstance(body, str):
                        text = body.strip()

                extracted.append(
                    WhatsappCloudInboundMessage(
                        provider_message_id=provider_message_id.strip(),
                        sender_wa_id=sender_wa_id.strip(),
                        message_type=message_type.strip(),
                        text=text,
                        phone_number_id=(
                            str(phone_number_id)
                            if phone_number_id is not None
                            else None
                        ),
                    )
                )

    return extracted


def _graph_url() -> str:
    return (
        "https://graph.facebook.com/"
        f"{settings.whatsapp_cloud_graph_version}/"
        f"{settings.whatsapp_cloud_phone_number_id}/messages"
    )


def _recipient_id(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise WhatsappCloudSendError("Recipient WhatsApp ID is invalid.")
    return digits


def _send_payload(payload: dict[str, Any]) -> str:
    if not settings.whatsapp_cloud_ready:
        raise WhatsappCloudConfigurationError(
            "Hosted WhatsApp Cloud API is not fully configured."
        )

    try:
        with httpx.Client(
            timeout=settings.whatsapp_cloud_timeout_seconds,
        ) as client:
            response = client.post(
                _graph_url(),
                headers={
                    "Authorization": (
                        f"Bearer {settings.whatsapp_cloud_access_token}"
                    ),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise WhatsappCloudSendError(
            "Meta WhatsApp Cloud API rejected the outbound message."
        ) from exc

    try:
        body = response.json()
        messages = body.get("messages")
        message_id = messages[0].get("id")
    except (ValueError, AttributeError, IndexError, TypeError) as exc:
        raise WhatsappCloudSendError(
            "Meta WhatsApp Cloud API returned an unreadable response."
        ) from exc

    if not isinstance(message_id, str) or not message_id:
        raise WhatsappCloudSendError(
            "Meta WhatsApp Cloud API did not return a message ID."
        )
    return message_id


def send_text_message(to_wa_id: str, body: str) -> str:
    message = body.strip()
    if not message:
        raise WhatsappCloudSendError("Outbound WhatsApp message is empty.")

    return _send_payload(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": _recipient_id(to_wa_id),
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message[:4096],
            },
        }
    )


def send_template_message(
    to_wa_id: str,
    template_name: str,
    language_code: str,
) -> str:
    if not template_name or not language_code:
        raise WhatsappCloudConfigurationError(
            "The onboarding template is not configured."
        )

    return _send_payload(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": _recipient_id(to_wa_id),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
    )


def _phone_input_from_wa_id(sender_wa_id: str) -> str:
    digits = re.sub(r"\D", "", sender_wa_id)
    if not digits:
        raise InvalidPhoneNumberError("Invalid WhatsApp sender.")
    return f"+{digits}"


def _sender_hash(phone_e164: str) -> str:
    return hashlib.sha256(phone_e164.encode("utf-8")).hexdigest()


def _claim_event(
    db: Session,
    message: WhatsappCloudInboundMessage,
    sender_hash: str,
) -> WhatsappCloudEvent | None:
    event = WhatsappCloudEvent(
        provider_message_id=message.provider_message_id,
        sender_hash=sender_hash,
        message_type=message.message_type,
        status=WhatsappCloudEventStatus.received,
    )
    db.add(event)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(WhatsappCloudEvent)
            .filter(
                WhatsappCloudEvent.provider_message_id
                == message.provider_message_id
            )
            .first()
        )
        if existing is not None:
            return None
        raise

    db.refresh(event)
    return event


def _finish_event(
    db: Session,
    event: WhatsappCloudEvent,
    *,
    action: str,
    outbound_message_id: str | None,
    latency_ms: int,
    family_id: uuid.UUID | None = None,
    member_id: uuid.UUID | None = None,
    status: WhatsappCloudEventStatus = WhatsappCloudEventStatus.processed,
    error_code: str | None = None,
) -> None:
    event.family_id = family_id
    event.member_id = member_id
    event.action = action
    event.status = status
    event.outbound_message_id = outbound_message_id
    event.latency_ms = latency_ms
    event.error_code = error_code
    event.processed_at = datetime.now(timezone.utc)
    db.commit()


def _normalized_reply(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return " ".join(normalized.split()).strip(" .,!?:;\"'")


def _normalize_yes_no(value: str) -> str | None:
    normalized = _normalized_reply(value)
    if normalized in _YES_VALUES:
        return "Yes"
    if normalized in _NO_VALUES:
        return "No"

    first_word = normalized.split(" ", 1)[0] if normalized else ""
    if first_word in _YES_VALUES:
        return "Yes"
    if first_word in _NO_VALUES:
        return "No"
    return None


def _answer_value(
    question: OnboardingQuestion,
    text: str | None,
) -> Any | None:
    if text is None:
        return None

    if question.type == "choice":
        if question.options == ["Yes", "No"]:
            return _normalize_yes_no(text)

        normalized = _normalized_reply(text)
        for option in question.options or []:
            if normalized == _normalized_reply(option):
                return option
        return None

    if question.type == "free_text":
        answer = text.strip()
        return answer[:200] if answer else None

    return None


def _question_message(question: OnboardingQuestion) -> str:
    if question.type == "choice" and question.options:
        options = " or ".join(question.options)
        return f"{question.prompt}\nReply {options}."
    return question.prompt


def _completed_message() -> str:
    return (
        "Your family health setup is complete. "
        "Your answers have been saved securely. "
        "This beta does not provide medical advice."
    )


def _message_for_current_context(context: dict[str, Any]) -> str:
    action = context.get("action")

    if action == "ask_question":
        question = context.get("question")
        if isinstance(question, OnboardingQuestion):
            return _question_message(question)

    if action == "waiting_for_other_member":
        target_role = context.get("target_role") or "other family member"
        return (
            f"The {target_role} needs to answer the current setup question. "
            "I will continue when they message this WhatsApp number."
        )

    if action == "health_assistant":
        return _completed_message()

    return (
        "I could not continue the setup just now. "
        "Please try again in a moment."
    )


def process_inbound_message(
    db: Session,
    message: WhatsappCloudInboundMessage,
    *,
    send_text: SendText = send_text_message,
) -> None:
    started = time.perf_counter()
    normalized_phone = to_e164(_phone_input_from_wa_id(message.sender_wa_id))
    event = _claim_event(db, message, _sender_hash(normalized_phone))
    if event is None:
        return

    family_id: uuid.UUID | None = None
    member_id: uuid.UUID | None = None
    action = "unregistered"

    try:
        try:
            identity, member, family, _ = resolve_whatsapp_identity(
                db,
                normalized_phone,
            )
        except WhatsappIdentityNotFoundError:
            response_text = (
                "This WhatsApp number is not registered with Parent Health "
                f"Agent yet. Sign up at {settings.normalized_cloud_landing_url}."
            )
        else:
            family_id = family.id
            member_id = member.id

            if identity.platform_user_id != message.sender_wa_id:
                identity.platform_user_id = message.sender_wa_id
                db.commit()

            context = resolve_whatsapp_context(db, normalized_phone)
            action = str(context.get("action") or "unknown")

            if action == "verify_or_join":
                response_text = (
                    "Your number is registered, but verification is still "
                    "required. Open the personal verification link created "
                    "during signup, then message me again."
                )
            elif action == "waiting_for_verification":
                waiting_on = context.get("waiting_on_role") or "other member"
                response_text = (
                    f"Your number is verified. The {waiting_on} still needs "
                    "to use their verification link."
                )
            elif action == "start_onboarding":
                _, question = start_onboarding(db, family.id)
                if question.target == member.role.value:
                    response_text = _question_message(question)
                else:
                    response_text = (
                        f"Setup is ready. The {question.target} needs to "
                        "answer the first question from their WhatsApp number."
                    )
            elif action == "ask_question":
                question = context.get("question")
                if not isinstance(question, OnboardingQuestion):
                    raise RuntimeError(
                        "The backend returned an invalid onboarding question."
                    )

                answer = _answer_value(question, message.text)
                if answer is None:
                    if message.message_type != "text":
                        response_text = (
                            "Please reply with a text message.\n"
                            f"{_question_message(question)}"
                        )
                    else:
                        response_text = (
                            "I could not match that answer.\n"
                            f"{_question_message(question)}"
                        )
                else:
                    try:
                        session, next_question = submit_onboarding_answer(
                            db,
                            family.id,
                            member.role,
                            question.key,
                            answer,
                        )
                    except OnboardingAnswerValidationError:
                        response_text = (
                            "I could not match that answer.\n"
                            f"{_question_message(question)}"
                        )
                    except OnboardingAlreadyCompletedError:
                        response_text = _completed_message()
                    except (
                        OnboardingNotStartedError,
                        OnboardingStepMismatchError,
                        OnboardingAnswerConflictError,
                    ):
                        latest_context = resolve_whatsapp_context(
                            db,
                            normalized_phone,
                        )
                        response_text = _message_for_current_context(
                            latest_context
                        )
                    else:
                        if next_question is not None:
                            response_text = _question_message(next_question)
                        elif session.status.value == "completed":
                            response_text = _completed_message()
                        else:
                            response_text = (
                                "Your answer was saved. "
                                "Please message me again to continue."
                            )
            elif action == "waiting_for_other_member":
                target_role = context.get("target_role") or "other member"
                response_text = (
                    f"The {target_role} needs to answer the current setup "
                    "question from their own WhatsApp number."
                )
            elif action == "health_assistant":
                response_text = _completed_message()
            else:
                response_text = (
                    "I could not determine the next setup step. "
                    "Please try again in a moment."
                )

        outbound_message_id = send_text(
            message.sender_wa_id,
            response_text,
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        _finish_event(
            db,
            event,
            action=action,
            outbound_message_id=outbound_message_id,
            latency_ms=latency_ms,
            family_id=family_id,
            member_id=member_id,
        )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000)
        try:
            _finish_event(
                db,
                event,
                action=action,
                outbound_message_id=None,
                latency_ms=latency_ms,
                family_id=family_id,
                member_id=member_id,
                status=WhatsappCloudEventStatus.failed,
                error_code=type(exc).__name__[:100],
            )
        except SQLAlchemyError:
            db.rollback()
            logger.exception(
                "Could not store WhatsApp Cloud event failure event_id=%s",
                event.id,
            )

        logger.exception(
            "WhatsApp Cloud message processing failed event_id=%s",
            event.id,
        )


def process_inbound_message_background(
    message: WhatsappCloudInboundMessage,
) -> None:
    db = SessionLocal()
    try:
        process_inbound_message(db, message)
    finally:
        db.close()


def send_onboarding_template_background(family_id: uuid.UUID) -> None:
    if not settings.whatsapp_cloud_auto_start_ready:
        return

    db = SessionLocal()
    try:
        family = db.get(Family, family_id)
        if family is None or family.status != FamilyStatus.onboarding:
            return

        parent_identity = (
            db.query(WhatsappIdentity)
            .filter(
                WhatsappIdentity.family_id == family_id,
                WhatsappIdentity.role == MemberRole.parent,
                WhatsappIdentity.verified_at.is_not(None),
            )
            .first()
        )
        if parent_identity is None:
            return

        recipient = (
            parent_identity.platform_user_id
            or parent_identity.phone_e164
        )
        outbound_message_id = send_template_message(
            recipient,
            settings.whatsapp_cloud_onboarding_template_name,
            settings.whatsapp_cloud_onboarding_template_language,
        )
        logger.info(
            "Sent onboarding template family_id=%s outbound_id=%s",
            family_id,
            outbound_message_id,
        )
    except Exception:
        logger.exception(
            "Could not send automatic onboarding template family_id=%s",
            family_id,
        )
    finally:
        db.close()


def cloud_status(db: Session) -> dict[str, Any]:
    processed_events = (
        db.query(WhatsappCloudEvent)
        .filter(
            WhatsappCloudEvent.status
            == WhatsappCloudEventStatus.processed
        )
        .count()
    )
    failed_events = (
        db.query(WhatsappCloudEvent)
        .filter(
            WhatsappCloudEvent.status
            == WhatsappCloudEventStatus.failed
        )
        .count()
    )
    last_event = (
        db.query(WhatsappCloudEvent)
        .order_by(WhatsappCloudEvent.created_at.desc())
        .first()
    )

    return {
        "provider": "meta_whatsapp_cloud_api",
        "enabled": settings.whatsapp_cloud_enabled,
        "configured": settings.whatsapp_cloud_ready,
        "auto_start_enabled": settings.whatsapp_cloud_auto_start_enabled,
        "auto_start_configured": settings.whatsapp_cloud_auto_start_ready,
        "processed_events": processed_events,
        "failed_events": failed_events,
        "last_event_status": (
            last_event.status.value if last_event is not None else None
        ),
        "last_event_at": (
            last_event.created_at.isoformat()
            if last_event is not None
            else None
        ),
    }
