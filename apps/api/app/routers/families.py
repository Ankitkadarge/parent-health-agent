from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.schemas.family import FamilyCreateRequest, FamilyCreateResponse, FamilyInviteOut
from app.services.family_service import DuplicatePhoneError, create_family
from app.utils.phone import InvalidPhoneNumberError

router = APIRouter(prefix="/families", tags=["families"])


@router.post("", response_model=FamilyCreateResponse, status_code=201)
def create_family_endpoint(
    payload: FamilyCreateRequest, db: Session = Depends(get_db)
) -> FamilyCreateResponse:
    try:
        family = create_family(db, payload)
    except InvalidPhoneNumberError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicatePhoneError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return FamilyCreateResponse(
        family_id=family.id,
        invites=[
            FamilyInviteOut(
                role=invite.member.role,
                token=invite.token,
                invite_url=f"{settings.whatsapp_invite_base_url}?token={invite.token}",
                expires_at=invite.expires_at,
            )
            for invite in family.invites
        ],
    )
