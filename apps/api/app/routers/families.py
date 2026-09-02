from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.schemas.family import FamilyCreateRequest, FamilyCreateResponse, FamilyInviteOut
from app.services.family_service import (
    DuplicatePhoneError,
    SamePhoneNumberError,
    create_family,
)
from app.utils.phone import InvalidPhoneNumberError

router = APIRouter(prefix="/families", tags=["families"])


@router.post("", response_model=FamilyCreateResponse, status_code=201)
def create_family_endpoint(
    payload: FamilyCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> FamilyCreateResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        created = create_family(db, payload)
    except InvalidPhoneNumberError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SamePhoneNumberError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicatePhoneError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    family = created.family
    invite_tokens = created.invite_tokens
    invite_base_url = settings.normalized_invite_base_url
    return FamilyCreateResponse(
        family_id=family.id,
        invites=[
            FamilyInviteOut(
                role=invite.member.role,
                token=invite_tokens[invite.member.role],
                invite_url=(
                    f"{invite_base_url}?token="
                    f"{quote(invite_tokens[invite.member.role], safe='')}"
                ),
                expires_at=invite.expires_at,
            )
            for invite in family.invites
        ],
        whatsapp_group_created=family.whatsapp_group_id is not None,
    )
