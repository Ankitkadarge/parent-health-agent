import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.member import MemberRole


SUPPORTED_LANGUAGES = (
    "English",
    "Hindi",
    "Marathi",
    "Gujarati",
    "Tamil",
    "Telugu",
    "Kannada",
    "Bengali",
    "Punjabi",
    "Other",
)


class FamilyCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    child_name: str = Field(min_length=1, max_length=255)
    child_phone: str = Field(min_length=1, max_length=32)
    parent_name: str = Field(min_length=1, max_length=255)
    parent_phone: str = Field(min_length=1, max_length=32)
    parent_preferred_language: str = Field(min_length=1, max_length=50)
    consent: bool = Field(strict=True)

    @field_validator("parent_preferred_language")
    @classmethod
    def language_must_be_supported(cls, value: str) -> str:
        if value not in SUPPORTED_LANGUAGES:
            allowed = ", ".join(SUPPORTED_LANGUAGES)
            raise ValueError(f"Choose one of the supported languages: {allowed}.")
        return value

    @field_validator("consent")
    @classmethod
    def consent_must_be_true(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent is required to create a family.")
        return value


class FamilyInviteOut(BaseModel):
    role: MemberRole
    token: str
    invite_url: str
    expires_at: datetime


class FamilyCreateResponse(BaseModel):
    family_id: uuid.UUID
    invites: list[FamilyInviteOut]
    whatsapp_group_created: bool = False
