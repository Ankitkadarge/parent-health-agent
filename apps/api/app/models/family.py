import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class OnboardingStatus(str, enum.Enum):
    pending = "pending"
    active = "active"


class Family(Base):
    __tablename__ = "families"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    onboarding_status: Mapped[OnboardingStatus] = mapped_column(
        Enum(OnboardingStatus, name="onboarding_status"),
        default=OnboardingStatus.pending,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    members: Mapped[list["Member"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
    whatsapp_identities: Mapped[list["WhatsappIdentity"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
    onboarding_session: Mapped["OnboardingSession"] = relationship(
        back_populates="family", uselist=False, cascade="all, delete-orphan"
    )
