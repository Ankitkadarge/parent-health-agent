import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class FamilyStatus(str, enum.Enum):
    pending_verification = "pending_verification"
    onboarding = "onboarding"
    active = "active"


class Family(Base):
    __tablename__ = "families"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[FamilyStatus] = mapped_column(
        Enum(FamilyStatus, name="family_status"),
        default=FamilyStatus.pending_verification,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    whatsapp_group_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    members: Mapped[list["Member"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
    whatsapp_identities: Mapped[list["WhatsappIdentity"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
    onboarding_session: Mapped["OnboardingSession"] = relationship(
        back_populates="family", uselist=False, cascade="all, delete-orphan"
    )
    invites: Mapped[list["FamilyInvite"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
