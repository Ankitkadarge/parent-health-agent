import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.family import FamilyStatus
from app.models.member import MemberRole
from app.models.onboarding_session import OnboardingSessionStatus
from app.services.onboarding_questions import OnboardingQuestion


class WhatsappResolveOnboardingOut(BaseModel):
    status: OnboardingSessionStatus
    current_step: str | None


class WhatsappResolveOut(BaseModel):
    family_id: uuid.UUID
    member_id: uuid.UUID
    role: MemberRole
    phone_e164: str
    verified: bool
    onboarding: WhatsappResolveOnboardingOut


class WhatsappContextOut(BaseModel):
    action: str
    family_id: uuid.UUID | None = None
    member_id: uuid.UUID | None = None
    role: MemberRole | None = None
    target_role: str | None = None
    waiting_on_role: str | None = None
    current_step: str | None = None
    question: OnboardingQuestion | None = None


class WhatsappJoinRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    token: str = Field(min_length=20, max_length=128)
    phone: str = Field(min_length=1, max_length=32)


class WhatsappJoinResponse(BaseModel):
    family_id: uuid.UUID
    member_id: uuid.UUID
    role: MemberRole
    verified_at: datetime
    family_status: FamilyStatus
