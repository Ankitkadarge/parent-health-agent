import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.family import Family, FamilyStatus
from app.models.family_invite import FamilyInvite
from app.models.member import Member, MemberRole
from app.models.whatsapp_identity import WhatsappIdentity

INVITE_VALIDITY = timedelta(days=7)


def _utcnow() -> datetime:
    """Naive UTC now, matching the project's plain DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class InviteNotFoundError(Exception):
    pass


class InviteAlreadyUsedError(Exception):
    pass


class InviteExpiredError(Exception):
    pass


class InvitePhoneMismatchError(Exception):
    pass


def create_invites_for_family(family: Family) -> dict[MemberRole, str]:
    """Attach one invite per member and return the one-time raw tokens.

    Only token digests are stored in PostgreSQL. The raw values are returned to
    the caller once so they can be placed in the verification links.
    """
    now = _utcnow()
    raw_tokens: dict[MemberRole, str] = {}
    invites: list[FamilyInvite] = []

    for member in family.members:
        raw_token = secrets.token_urlsafe(32)
        raw_tokens[member.role] = raw_token
        invites.append(
            FamilyInvite(
                member=member,
                token_hash=hash_invite_token(raw_token),
                expires_at=now + INVITE_VALIDITY,
            )
        )

    family.invites = invites
    return raw_tokens


def _all_members_verified(db: Session, family_id: uuid.UUID) -> bool:
    identities = (
        db.query(WhatsappIdentity).filter(WhatsappIdentity.family_id == family_id).all()
    )
    return len(identities) > 0 and all(
        identity.verified_at is not None for identity in identities
    )


def join_via_invite(
    db: Session, token: str, phone_e164: str
) -> tuple[Member, WhatsappIdentity, Family]:
    token_hash = hash_invite_token(token.strip())
    invite = (
        db.query(FamilyInvite).filter(FamilyInvite.token_hash == token_hash).first()
    )
    if invite is None:
        raise InviteNotFoundError("Invalid invite token.")

    if invite.used_at is not None:
        raise InviteAlreadyUsedError("This invite has already been used.")

    if invite.expires_at < _utcnow():
        raise InviteExpiredError("This invite has expired.")

    member = invite.member
    if member.phone_e164 != phone_e164:
        raise InvitePhoneMismatchError(
            "This phone number doesn't match the invited member."
        )

    identity = (
        db.query(WhatsappIdentity)
        .filter(WhatsappIdentity.member_id == member.id)
        .first()
    )
    if identity is None:
        raise InviteNotFoundError("This invitation is not linked to a WhatsApp identity.")

    now = _utcnow()
    identity.verified_at = now
    invite.used_at = now
    db.flush()

    family = invite.family
    if (
        family.status == FamilyStatus.pending_verification
        and _all_members_verified(db, family.id)
    ):
        family.status = FamilyStatus.onboarding

    db.commit()
    db.refresh(identity)
    db.refresh(family)
    return member, identity, family
