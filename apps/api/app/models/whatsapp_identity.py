import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.member import MemberRole


class WhatsappIdentity(Base):
    __tablename__ = "whatsapp_identities"
    __table_args__ = (
        UniqueConstraint(
            "family_id",
            "role",
            name="uq_whatsapp_identities_family_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("members.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    platform_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="member_role"), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    family: Mapped["Family"] = relationship(back_populates="whatsapp_identities")
    member: Mapped["Member"] = relationship()
