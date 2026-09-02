import logging
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.family import Family, FamilyStatus
from app.models.member import Member, MemberRole
from app.models.whatsapp_identity import WhatsappIdentity
from app.schemas.family import FamilyCreateRequest
from app.services.onboarding_service import initialize_onboarding
from app.services.verification_service import create_invites_for_family
from app.services.whatsapp_group_service import (
    WhatsappGroupCreationError,
    create_whatsapp_group,
)
from app.utils.phone import to_e164

logger = logging.getLogger(__name__)


class DuplicatePhoneError(Exception):
    """Raised when a phone number is already connected to a family."""


class SamePhoneNumberError(Exception):
    """Raised when child and parent normalize to the same WhatsApp number."""


@dataclass(frozen=True)
class CreatedFamily:
    family: Family
    invite_tokens: dict[MemberRole, str]


def _try_create_whatsapp_group(
    db: Session,
    family: Family,
    *,
    parent_name: str,
    child_phone: str,
    parent_phone: str,
) -> None:
    if not settings.whatsapp_group_creation_enabled:
        return

    if not settings.normalized_bridge_base_url:
        logger.warning(
            "WhatsApp group creation is enabled but WHATSAPP_BRIDGE_BASE_URL is empty"
        )
        return

    try:
        group_name = settings.whatsapp_group_name_template.format(
            parent_name=parent_name
        )
        group_id = create_whatsapp_group(
            group_name,
            [child_phone, parent_phone],
        )
    except WhatsappGroupCreationError as exc:
        logger.warning(
            "WhatsApp group creation failed for family %s: %s",
            family.id,
            exc,
        )
        return

    family.whatsapp_group_id = group_id
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        family.whatsapp_group_id = None
        logger.exception(
            "Created WhatsApp group but could not store its id for family %s",
            family.id,
        )
        return

    db.refresh(family)


def create_family(
    db: Session,
    data: FamilyCreateRequest,
) -> CreatedFamily:
    """Create a family and its one-time verification invitations."""
    child_phone = to_e164(data.child_phone)
    parent_phone = to_e164(data.parent_phone)

    if child_phone == parent_phone:
        raise SamePhoneNumberError(
            "Your WhatsApp number and your parent's WhatsApp number must be different."
        )

    existing = (
        db.query(WhatsappIdentity)
        .filter(WhatsappIdentity.phone_e164.in_([child_phone, parent_phone]))
        .first()
    )
    if existing is not None:
        raise DuplicatePhoneError(
            "One of these WhatsApp numbers is already connected to a family."
        )

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
    invite_tokens = create_invites_for_family(family)

    db.add(family)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicatePhoneError(
            "One of these WhatsApp numbers is already connected to a family."
        ) from exc

    db.refresh(family)
    _try_create_whatsapp_group(
        db,
        family,
        parent_name=data.parent_name,
        child_phone=child_phone,
        parent_phone=parent_phone,
    )
    return CreatedFamily(
        family=family,
        invite_tokens=invite_tokens,
    )
