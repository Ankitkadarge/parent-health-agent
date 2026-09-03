import logging
import re
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.routers import families, onboarding, whatsapp

logger = logging.getLogger("parent_health_api")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

app = FastAPI(
    title="Parent Health Agent API",
    version="0.4.0",
    description=(
        "Backend for family signup, verification, hosted WhatsApp onboarding, "
        "and health-profile setup."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    supplied_request_id = request.headers.get("x-request-id", "")
    request_id = (
        supplied_request_id
        if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
        else str(uuid.uuid4())
    )
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "%s %s failed in %.0fms request_id=%s",
            request.method,
            request.url.path,
            duration_ms,
            request_id,
        )
        raise

    duration_ms = (time.perf_counter() - started) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if (
        request.url.path.startswith(("/families", "/whatsapp"))
        and "cache-control" not in response.headers
    ):
        response.headers["Cache-Control"] = "no-store"

    logger.info(
        "%s %s -> %s in %.0fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


app.include_router(families.router)
app.include_router(onboarding.router)
app.include_router(whatsapp.router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": "Parent Health Agent API",
        "status": "ok",
        "health": "/health",
        "readiness": "/ready",
        "whatsapp_status": "/whatsapp/cloud/status",
        "docs": "/docs",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=503,
            detail="Database is temporarily unavailable.",
        ) from exc

    return {"status": "ready", "database": "ok"}
