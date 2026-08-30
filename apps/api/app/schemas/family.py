import uuid

from pydantic import BaseModel, Field, field_validator


class FamilyCreateRequest(BaseModel):
    child_name: str = Field(min_length=1, max_length=255)
    child_phone: str = Field(min_length=1)
    parent_name: str = Field(min_length=1, max_length=255)
    parent_phone: str = Field(min_length=1)
    parent_preferred_language: str = Field(min_length=1, max_length=50)
    consent: bool

    @field_validator("consent")
    @classmethod
    def consent_must_be_true(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent is required to create a family.")
        return value


class FamilyCreateResponse(BaseModel):
    family_id: uuid.UUID
