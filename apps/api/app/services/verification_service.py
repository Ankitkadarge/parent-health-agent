import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.family import Family, FamilyStatus
from app.models.family_invite import FamilyInvite
from app.models.member import Member
from app.models.whatsapp_identity import WhatsappIdentity

INVITE_VALIDITY = timedelta(days=7)


def _utcnow() -> datetime:
    """Naive UTC now, matching this codebase's convention of plain (non-timezone-
    aware) DateTime columns — comparing against a stored value must use the same
    naive convention or Postgres raises on aware-vs-naive comparisons."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class InviteNotFoundError(Exception):
    pass


class InviteAlreadyUsedError(Exception):
    pass


class InviteExpiredError(Exception):
    pass


class InvitePhoneMismatchError(Exception):
    pass


def create_invites_for_family(family: Family) -> None:
    """Attach one invite per member to a not-yet-committed Family. Does not
    commit — the caller commits the whole family graph in one transaction.
    """
    now = _utcnow()
    family.invites = [
        FamilyInvite(
            member=member,
            token=secrets.token_urlsafe(32),
            expires_at=now + INVITE_VALIDITY,
        )
        for member in family.members
    ]


def _all_members_verified(db: Session, family_id: uuid.UUID) -> bool:
    identities = (
        db.query(WhatsappIdentity).filter(WhatsappIdentity.family_id == family_id).all()
    )
    return len(identities) > 0 and all(identity.verified_at is not None for identity in identities)


def join_via_invite(
    db: Session, token: str, phone_e164: str
) -> tuple[Member, WhatsappIdentity, Family]:
    invite = db.query(FamilyInvite).filter(FamilyInvite.token == token).first()
    if invite is None:
        raise InviteNotFoundError("Invalid invite token.")

    if invite.used_at is not None:
        raise InviteAlreadyUsedError("This invite has already been used.")

    if invite.expires_at < _utcnow():
        raise InviteExpiredError("This invite has expired.")

    member = invite.member
    if member.phone_e164 != phone_e164:
        raise InvitePhoneMismatchError("This phone number doesn't match the invited member.")

    identity = (
        db.query(WhatsappIdentity).filter(WhatsappIdentity.member_id == member.id).first()
    )

    now = _utcnow()
    identity.verified_at = now
    invite.used_at = now

    family = invite.family
    if family.status == FamilyStatus.pending_verification and _all_members_verified(
        db, family.id
    ):
        family.status = FamilyStatus.onboarding

    db.commit()
    db.refresh(identity)
    db.refresh(family)
    return member, identity, family
