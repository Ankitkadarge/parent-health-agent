import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.member import MemberRole
from app.models.onboarding_session import OnboardingSessionStatus
from app.services.onboarding_questions import OnboardingQuestion


class OnboardingMemberOut(BaseModel):
    role: MemberRole
    name: str
    phone_e164: str
    verified_at: datetime | None = None


class OnboardingStateOut(BaseModel):
    family_id: uuid.UUID
    status: OnboardingSessionStatus
    current_step: str | None
    members: list[OnboardingMemberOut]


class OnboardingStartResponse(BaseModel):
    family_id: uuid.UUID
    status: OnboardingSessionStatus
    current_step: str | None
    question: OnboardingQuestion


class OnboardingAnswerRequest(BaseModel):
    member_role: MemberRole
    key: str = Field(min_length=1)
    value: str | list[str]


class OnboardingAnswerResponse(BaseModel):
    family_id: uuid.UUID
    status: OnboardingSessionStatus
    current_step: str | None
    question: OnboardingQuestion | None
