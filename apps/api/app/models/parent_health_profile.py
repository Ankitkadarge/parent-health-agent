import uuid
from datetime import datetime

from sqlalchemy import Boolean, JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class ParentHealthProfile(Base):
    """Structured health profile for one parent/patient. Keyed by
    parent_member_id (not family_id) so a family can hold more than one
    profile if it ever supports multiple parents/patients.
    """

    __tablename__ = "parent_health_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    parent_member_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("members.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Current MVP diabetes onboarding fields.
    diagnosed_with_diabetes: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    taking_medication: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    medicine_time: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Kept for backwards compatibility with profiles created by the earlier,
    # longer onboarding flow. New onboarding does not populate these fields.
    conditions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    dietary_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reminder_preferences: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    family: Mapped["Family"] = relationship()
    parent_member: Mapped["Member"] = relationship()
