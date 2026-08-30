from sqlalchemy.orm import Session

from app.models.family import Family, FamilyStatus
from app.models.member import Member
from app.models.onboarding_session import OnboardingSession, OnboardingSessionStatus
from app.models.whatsapp_identity import WhatsappIdentity
from app.services.onboarding_questions import get_question


class WhatsappIdentityNotFoundError(Exception):
    pass


def resolve_whatsapp_identity(
    db: Session, phone_e164: str
) -> tuple[WhatsappIdentity, Member, Family, OnboardingSession]:
    identity = (
        db.query(WhatsappIdentity).filter(WhatsappIdentity.phone_e164 == phone_e164).first()
    )
    if identity is None:
        raise WhatsappIdentityNotFoundError(f"No WhatsApp identity found for {phone_e164}")

    member = identity.member
    family = identity.family
    session = family.onboarding_session
    return identity, member, family, session


def resolve_whatsapp_context(db: Session, phone_e164: str) -> dict:
    """The actionable conversational state Hermes needs to decide how to
    respond to an inbound WhatsApp message. Deliberately transport-agnostic —
    no WhatsApp/Hermes SDK calls here, just business logic over our own state.
    """
    identity, member, family, session = resolve_whatsapp_identity(db, phone_e164)

    if identity.verified_at is None:
        return {
            "action": "verify_or_join",
            "family_id": family.id,
            "member_id": member.id,
            "role": member.role,
        }

    if family.status == FamilyStatus.pending_verification:
        other_identity = (
            db.query(WhatsappIdentity)
            .filter(
                WhatsappIdentity.family_id == family.id,
                WhatsappIdentity.member_id != member.id,
            )
            .first()
        )
        return {
            "action": "waiting_for_verification",
            "family_id": family.id,
            "member_id": member.id,
            "role": member.role,
            "waiting_on_role": other_identity.role.value if other_identity else None,
        }

    if session.status == OnboardingSessionStatus.pending:
        return {
            "action": "start_onboarding",
            "family_id": family.id,
            "member_id": member.id,
            "role": member.role,
        }

    if session.status == OnboardingSessionStatus.in_progress:
        question = get_question(session.current_step)

        if question.target == member.role.value:
            return {
                "action": "ask_question",
                "family_id": family.id,
                "member_id": member.id,
                "role": member.role,
                "question": question,
            }

        return {
            "action": "waiting_for_other_member",
            "target_role": question.target,
            "current_step": session.current_step,
            "question": question,
        }

    return {
        "action": "health_assistant",
        "family_id": family.id,
        "member_id": member.id,
        "role": member.role,
    }
