from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.whatsapp import (
    WhatsappContextOut,
    WhatsappJoinRequest,
    WhatsappJoinResponse,
    WhatsappResolveOnboardingOut,
    WhatsappResolveOut,
)
from app.services.verification_service import (
    InviteAlreadyUsedError,
    InviteExpiredError,
    InviteNotFoundError,
    InvitePhoneMismatchError,
    join_via_invite,
)
from app.services.whatsapp_resolution_service import (
    WhatsappIdentityNotFoundError,
    resolve_whatsapp_context,
    resolve_whatsapp_identity,
)
from app.utils.phone import InvalidPhoneNumberError, to_e164

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _normalize_phone(phone: str) -> str:
    try:
        return to_e164(phone)
    except InvalidPhoneNumberError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/resolve", response_model=WhatsappResolveOut)
def resolve_endpoint(
    phone: str = Query(...), db: Session = Depends(get_db)
) -> WhatsappResolveOut:
    normalized_phone = _normalize_phone(phone)

    try:
        identity, member, family, session = resolve_whatsapp_identity(db, normalized_phone)
    except WhatsappIdentityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return WhatsappResolveOut(
        family_id=family.id,
        member_id=member.id,
        role=member.role,
        phone_e164=identity.phone_e164,
        verified=identity.verified_at is not None,
        onboarding=WhatsappResolveOnboardingOut(
            status=session.status,
            current_step=session.current_step,
        ),
    )


@router.get("/context", response_model=WhatsappContextOut, response_model_exclude_none=True)
def context_endpoint(
    phone: str = Query(...), db: Session = Depends(get_db)
) -> WhatsappContextOut:
    normalized_phone = _normalize_phone(phone)

    try:
        context = resolve_whatsapp_context(db, normalized_phone)
    except WhatsappIdentityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return WhatsappContextOut(**context)


@router.post("/join", response_model=WhatsappJoinResponse)
def join_endpoint(
    payload: WhatsappJoinRequest, db: Session = Depends(get_db)
) -> WhatsappJoinResponse:
    normalized_phone = _normalize_phone(payload.phone)

    try:
        member, identity, family = join_via_invite(db, payload.token, normalized_phone)
    except InviteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InviteAlreadyUsedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InviteExpiredError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except InvitePhoneMismatchError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return WhatsappJoinResponse(
        family_id=family.id,
        member_id=member.id,
        role=member.role,
        verified_at=identity.verified_at,
        family_status=family.status,
    )
