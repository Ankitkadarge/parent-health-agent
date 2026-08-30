import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.onboarding import (
    OnboardingAnswerRequest,
    OnboardingAnswerResponse,
    OnboardingMemberOut,
    OnboardingStartResponse,
    OnboardingStateOut,
)
from app.services.onboarding_service import (
    OnboardingAlreadyCompletedError,
    OnboardingAnswerConflictError,
    OnboardingAnswerValidationError,
    OnboardingNotFoundError,
    OnboardingNotStartedError,
    OnboardingStepMismatchError,
    get_onboarding_state,
    start_onboarding,
    submit_onboarding_answer,
)

router = APIRouter(prefix="/families", tags=["onboarding"])


@router.get("/{family_id}/onboarding", response_model=OnboardingStateOut)
def get_onboarding_endpoint(family_id: uuid.UUID, db: Session = Depends(get_db)) -> OnboardingStateOut:
    try:
        session, members_with_status = get_onboarding_state(db, family_id)
    except OnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return OnboardingStateOut(
        family_id=session.family_id,
        status=session.status,
        current_step=session.current_step,
        members=[
            OnboardingMemberOut(
                role=member.role,
                name=member.name,
                phone_e164=member.phone_e164,
                verified_at=verified_at,
            )
            for member, verified_at in members_with_status
        ],
    )


@router.post("/{family_id}/onboarding/start", response_model=OnboardingStartResponse)
def start_onboarding_endpoint(
    family_id: uuid.UUID, db: Session = Depends(get_db)
) -> OnboardingStartResponse:
    try:
        session, question = start_onboarding(db, family_id)
    except OnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OnboardingAlreadyCompletedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return OnboardingStartResponse(
        family_id=session.family_id,
        status=session.status,
        current_step=session.current_step,
        question=question,
    )


@router.post("/{family_id}/onboarding/answer", response_model=OnboardingAnswerResponse)
def submit_onboarding_answer_endpoint(
    family_id: uuid.UUID, payload: OnboardingAnswerRequest, db: Session = Depends(get_db)
) -> OnboardingAnswerResponse:
    try:
        session, question = submit_onboarding_answer(
            db, family_id, payload.member_role, payload.key, payload.value
        )
    except OnboardingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        OnboardingAlreadyCompletedError,
        OnboardingNotStartedError,
        OnboardingStepMismatchError,
        OnboardingAnswerConflictError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OnboardingAnswerValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return OnboardingAnswerResponse(
        family_id=session.family_id,
        status=session.status,
        current_step=session.current_step,
        question=question,
    )
