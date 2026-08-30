import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.member import MemberRole


class OnboardingAnswer(Base):
    """The canonical, immutable record of an onboarding answer.

    One row per (family_id, step_key) — a step is answered once. Later
    resubmissions of the same step are validated against this row rather
    than creating new ones.
    """

    __tablename__ = "onboarding_answers"
    __table_args__ = (
        UniqueConstraint("family_id", "step_key", name="uq_onboarding_answers_family_step"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)
    member_role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="member_role"), nullable=False
    )
    answered_by_member_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("members.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    family: Mapped["Family"] = relationship()
    answered_by_member: Mapped["Member"] = relationship()
