"""add whatsapp_webhook_events for dedup and rate limiting

Numbered 0008 to keep the migration chain sequential after 0007 (the
originating task referred to this as migration 0009).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

whatsapp_event_direction = sa.Enum(
    "inbound", "outbound", name="whatsapp_event_direction"
)


def upgrade() -> None:
    whatsapp_event_direction.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "whatsapp_webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("family_id", sa.Uuid(), nullable=True),
        sa.Column("direction", whatsapp_event_direction, nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("sender_hash", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_message_id"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_whatsapp_webhook_events_sender_hash_created_at",
        "whatsapp_webhook_events",
        ["sender_hash", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_whatsapp_webhook_events_sender_hash_created_at",
        table_name="whatsapp_webhook_events",
    )
    op.drop_table("whatsapp_webhook_events")
    whatsapp_event_direction.drop(op.get_bind(), checkfirst=True)
