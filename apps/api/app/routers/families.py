from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.family import FamilyCreateRequest, FamilyCreateResponse
from app.services.family_service import create_family
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

    return FamilyCreateResponse(family_id=family.id)
