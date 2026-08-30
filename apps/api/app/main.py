from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import families, onboarding, whatsapp

app = FastAPI(title="Parent Health Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(families.router)
app.include_router(onboarding.router)
app.include_router(whatsapp.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
