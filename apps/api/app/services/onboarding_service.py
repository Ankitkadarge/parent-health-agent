import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.family import Family, FamilyStatus
from app.models.member import Member, MemberRole
from app.models.onboarding_answer import OnboardingAnswer
from app.models.onboarding_session import OnboardingSession, OnboardingSessionStatus
from app.models.parent_health_profile import ParentHealthProfile
from app.models.whatsapp_identity import WhatsappIdentity
from app.services.onboarding_questions import (
    FIRST_STEP,
    OnboardingQuestion,
    get_next_question,
    get_question,
)

PROFILE_FIELD_BY_STEP = {
    "conditions": "conditions",
    "medications": "medications",
    "dietary_preferences": "dietary_preferences",
    "activity_level": "activity_level",
    "reminder_preferences": "reminder_preferences",
}


class OnboardingNotFoundError(Exception):
    pass


class OnboardingAlreadyCompletedError(Exception):
    pass


class OnboardingNotStartedError(Exception):
    pass


class OnboardingStepMismatchError(Exception):
    pass


class OnboardingAnswerConflictError(Exception):
    pass


class OnboardingAnswerValidationError(Exception):
    pass


def initialize_onboarding(family: Family) -> None:
    """Attach WhatsApp identities (one per member) and a pending onboarding
    session to a not-yet-committed Family. Does not commit — the caller
    commits the whole family graph in one transaction.
    """
    family.whatsapp_identities = [
        WhatsappIdentity(
            member=member,
            phone_e164=member.phone_e164,
            role=member.role,
        )
        for member in family.members
    ]
    family.onboarding_session = OnboardingSession(status=OnboardingSessionStatus.pending)


def _get_session(db: Session, family_id: uuid.UUID) -> OnboardingSession:
    session = (
        db.query(OnboardingSession).filter(OnboardingSession.family_id == family_id).first()
    )
    if session is None:
        raise OnboardingNotFoundError(f"No onboarding found for family {family_id}")
    return session


def get_onboarding_state(
    db: Session, family_id: uuid.UUID
) -> tuple[OnboardingSession, list[tuple[Member, datetime | None]]]:
    session = _get_session(db, family_id)

    members = db.query(Member).filter(Member.family_id == family_id).all()
    identities = (
        db.query(WhatsappIdentity).filter(WhatsappIdentity.family_id == family_id).all()
    )
    verified_at_by_member = {identity.member_id: identity.verified_at for identity in identities}

    members_with_status = [(member, verified_at_by_member.get(member.id)) for member in members]
    return session, members_with_status


def start_onboarding(db: Session, family_id: uuid.UUID) -> tuple[OnboardingSession, OnboardingQuestion]:
    session = _get_session(db, family_id)

    if session.status == OnboardingSessionStatus.completed:
        raise OnboardingAlreadyCompletedError("Onboarding is already completed.")

    if session.status == OnboardingSessionStatus.pending:
        session.status = OnboardingSessionStatus.in_progress
        session.started_at = datetime.now(timezone.utc)
        session.current_step = FIRST_STEP.key
        db.commit()
        db.refresh(session)

    question = get_question(session.current_step)
    return session, question


def _normalize_for_comparison(value: Any) -> Any:
    """Best-effort normalization used both for storage and for comparing a
    resubmitted answer against what's already on record. Never raises —
    validation of shape/options happens separately in _validate_answer_value.
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return sorted({str(item).strip() for item in value})
    return value


def _validate_answer_value(question: OnboardingQuestion, value: Any) -> Any:
    if question.type == "choice":
        if not isinstance(value, str) or value not in (question.options or []):
            raise OnboardingAnswerValidationError(
                f"'{value}' is not a valid option for '{question.key}'."
            )
    elif question.type == "multi_choice":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise OnboardingAnswerValidationError(f"'{question.key}' expects a list of options.")
        options = set(question.options or [])
        invalid = [item for item in value if item not in options]
        if invalid:
            raise OnboardingAnswerValidationError(
                f"Invalid options for '{question.key}': {', '.join(invalid)}"
            )
    elif question.type == "free_text":
        if not isinstance(value, str) or not value.strip():
            raise OnboardingAnswerValidationError(f"'{question.key}' requires a non-empty answer.")
    else:
        raise OnboardingAnswerValidationError(f"Unknown question type '{question.type}'.")

    return _normalize_for_comparison(value)


def _get_or_create_health_profile(
    db: Session, family: Family, parent_member: Member
) -> ParentHealthProfile:
    profile = (
        db.query(ParentHealthProfile)
        .filter(ParentHealthProfile.parent_member_id == parent_member.id)
        .first()
    )
    if profile is None:
        profile = ParentHealthProfile(family_id=family.id, parent_member_id=parent_member.id)
        db.add(profile)
    return profile


def submit_onboarding_answer(
    db: Session, family_id: uuid.UUID, member_role: MemberRole, key: str, value: Any
) -> tuple[OnboardingSession, OnboardingQuestion | None]:
    session = _get_session(db, family_id)

    if session.status == OnboardingSessionStatus.completed:
        raise OnboardingAlreadyCompletedError("Onboarding is already completed.")
    if session.status == OnboardingSessionStatus.pending:
        raise OnboardingNotStartedError("Onboarding has not been started yet.")

    if key != session.current_step:
        existing = (
            db.query(OnboardingAnswer)
            .filter(OnboardingAnswer.family_id == family_id, OnboardingAnswer.step_key == key)
            .first()
        )
        if existing is None:
            raise OnboardingStepMismatchError(
                f"Expected an answer for '{session.current_step}', got '{key}'."
            )
        if existing.value != _normalize_for_comparison(value):
            raise OnboardingAnswerConflictError(
                f"'{key}' was already answered with a different value."
            )
        # Idempotent replay of an already-answered step: report current
        # actual state, change nothing.
        current_question = get_question(session.current_step) if session.current_step else None
        return session, current_question

    question = get_question(key)
    if question is None:
        raise OnboardingStepMismatchError(f"Unknown onboarding step '{key}'.")

    if member_role.value != question.target:
        raise OnboardingAnswerValidationError(
            f"'{key}' should be answered by the {question.target}, not the {member_role.value}."
        )

    normalized_value = _validate_answer_value(question, value)

    family = session.family
    answering_member = next((m for m in family.members if m.role == member_role), None)
    if answering_member is None:
        raise OnboardingAnswerValidationError(f"No {member_role.value} member found for this family.")

    db.add(
        OnboardingAnswer(
            family_id=family_id,
            step_key=key,
            member_role=member_role,
            answered_by_member_id=answering_member.id,
            value=normalized_value,
        )
    )

    if key == "preferred_language":
        answering_member.preferred_language = normalized_value
    else:
        parent_member = next((m for m in family.members if m.role == MemberRole.parent), None)
        if parent_member is None:
            raise OnboardingAnswerValidationError("No parent member found for this family.")
        profile = _get_or_create_health_profile(db, family, parent_member)
        setattr(profile, PROFILE_FIELD_BY_STEP[key], normalized_value)

    next_question = get_next_question(key)
    if next_question is not None:
        session.current_step = next_question.key
    else:
        session.status = OnboardingSessionStatus.completed
        session.current_step = None
        session.completed_at = datetime.now(timezone.utc)
        family.status = FamilyStatus.active

    db.commit()
    db.refresh(session)
    return session, next_question
