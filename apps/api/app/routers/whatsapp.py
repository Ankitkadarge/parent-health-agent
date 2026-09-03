import hmac
import json

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.services.whatsapp_cloud_service import (
    cloud_status,
    extract_inbound_messages,
    process_inbound_message_background,
    send_onboarding_template_background,
    verify_webhook_signature,
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
    payload: WhatsappJoinRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
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

    # This is a no-op until the hosted Meta integration and an approved
    # onboarding template are fully configured. It never blocks verification.
    background_tasks.add_task(
        send_onboarding_template_background,
        family.id,
    )

    return WhatsappJoinResponse(
        family_id=family.id,
        member_id=member.id,
        role=member.role,
        verified_at=identity.verified_at,
        family_status=family.status,
    )


@router.get("/cloud/status")
def cloud_status_endpoint(
    db: Session = Depends(get_db),
) -> dict:
    """Non-secret readiness and event counters for the hosted integration."""
    return cloud_status(db)


@router.get(
    "/cloud/webhook",
    include_in_schema=False,
    response_class=PlainTextResponse,
)
def verify_cloud_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(
        default=None,
        alias="hub.verify_token",
    ),
    challenge: str | None = Query(
        default=None,
        alias="hub.challenge",
    ),
) -> PlainTextResponse:
    configured_token = settings.whatsapp_cloud_verify_token
    if not configured_token:
        raise HTTPException(
            status_code=503,
            detail="Hosted WhatsApp webhook is not configured.",
        )

    if (
        mode == "subscribe"
        and verify_token is not None
        and challenge is not None
        and hmac.compare_digest(configured_token, verify_token)
    ):
        return PlainTextResponse(challenge, status_code=200)

    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@router.post("/cloud/webhook", include_in_schema=False)
async def receive_cloud_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    if not settings.whatsapp_cloud_ready:
        raise HTTPException(
            status_code=503,
            detail="Hosted WhatsApp integration is not configured.",
        )

    raw_body = await request.body()
    if len(raw_body) > settings.whatsapp_cloud_max_webhook_bytes:
        raise HTTPException(
            status_code=413,
            detail="Webhook payload is too large.",
        )

    if not verify_webhook_signature(
        raw_body,
        request.headers.get("x-hub-signature-256"),
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Webhook payload must be valid JSON.",
        ) from exc

    for message in extract_inbound_messages(payload):
        background_tasks.add_task(
            process_inbound_message_background,
            message,
        )

    # Meta requires a quick 200 response. Message processing and outbound sends
    # continue in FastAPI background tasks after this acknowledgement.
    return Response(status_code=200)
