import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class WhatsappEventDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class WhatsappWebhookEvent(Base):
    """Audit trail for WhatsApp webhook traffic, used for provider-message
    deduplication and rate limiting. Deliberately minimal: no raw phone
    numbers, payloads, secrets, or message text — see the module docstring
    in whatsapp_webhook_service.py for what is and isn't written here.
    """

    __tablename__ = "whatsapp_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    family_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("families.id", ondelete="SET NULL"), nullable=True
    )
    direction: Mapped[WhatsappEventDirection] = mapped_column(
        Enum(WhatsappEventDirection, name="whatsapp_event_direction"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    step_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    sender_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
