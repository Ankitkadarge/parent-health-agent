import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.family import Family, FamilyStatus
from app.models.member import Member, MemberRole
from app.schemas.family import FamilyCreateRequest
from app.services.onboarding_service import initialize_onboarding
from app.services.verification_service import create_invites_for_family
from app.services.whatsapp_group_service import WhatsappGroupCreationError, create_whatsapp_group
from app.utils.phone import to_e164

logger = logging.getLogger(__name__)


def create_family(db: Session, data: FamilyCreateRequest) -> Family:
    """Create a family with its child and parent members.

    This is intentionally kept independent of the HTTP layer so it can later
    be called directly by the Hermes conversational runtime as a tool,
    without going through the API.
    """
    child_phone = to_e164(data.child_phone)
    parent_phone = to_e164(data.parent_phone)

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
    db.commit()
    db.refresh(family)

    try:
        group_name = settings.whatsapp_group_name_template.format(parent_name=data.parent_name)
        family.whatsapp_group_id = create_whatsapp_group(group_name, [child_phone, parent_phone])
        db.commit()
        db.refresh(family)
    except WhatsappGroupCreationError as exc:
        logger.warning("WhatsApp group creation failed for family %s: %s", family.id, exc)

    return family
