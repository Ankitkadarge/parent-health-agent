from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.family import Family, FamilyStatus
from app.models.member import Member, MemberRole
from app.models.whatsapp_identity import WhatsappIdentity
from app.schemas.family import FamilyCreateRequest
from app.services.onboarding_service import initialize_onboarding
from app.services.verification_service import create_invites_for_family
from app.utils.phone import to_e164


class DuplicatePhoneError(Exception):
    """Raised when a phone number is already connected to a family."""


def create_family(db: Session, data: FamilyCreateRequest) -> Family:
    """Create a family with its child and parent members.

    This is intentionally kept independent of the HTTP layer so it can later
    be called directly by the Hermes conversational runtime as a tool,
    without going through the API.
    """
    child_phone = to_e164(data.child_phone)
    parent_phone = to_e164(data.parent_phone)

    existing = (
        db.query(WhatsappIdentity)
        .filter(WhatsappIdentity.phone_e164.in_([child_phone, parent_phone]))
        .first()
    )
    if existing is not None:
        raise DuplicatePhoneError("This WhatsApp number is already connected to a family.")

    family = Family(status=FamilyStatus.pending_verification)
    family.members = [
        Member(
            role=MemberRole.child,
            name=data.child_name,
            phone_e164=child_phone,
        ),
        Member(
            role=MemberRole.parent,
            name=data.parent_name,
            phone_e164=parent_phone,
            preferred_language=data.parent_preferred_language,
        ),
    ]
    initialize_onboarding(family)
    create_invites_for_family(family)

    db.add(family)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicatePhoneError(
            "This WhatsApp number is already connected to a family."
        ) from exc
    db.refresh(family)
    return family
