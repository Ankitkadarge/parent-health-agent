import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class WhatsappCloudEventStatus(str, enum.Enum):
    received = "received"
    processed = "processed"
    ignored = "ignored"
    failed = "failed"


class WhatsappCloudEvent(Base):
    __tablename__ = "whatsapp_cloud_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_message_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    family_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("families.id", ondelete="SET NULL"),
        nullable=True,
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[WhatsappCloudEventStatus] = mapped_column(
        Enum(WhatsappCloudEventStatus, name="whatsapp_cloud_event_status"),
        default=WhatsappCloudEventStatus.received,
        nullable=False,
    )
    outbound_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)
