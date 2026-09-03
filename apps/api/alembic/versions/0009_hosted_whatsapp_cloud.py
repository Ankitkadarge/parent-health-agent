"""hosted WhatsApp Cloud API event ledger

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    event_status = postgresql.ENUM(
        "received",
        "processed",
        "ignored",
        "failed",
        name="whatsapp_cloud_event_status",
        create_type=False,
    )
    event_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "whatsapp_cloud_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "provider_message_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("members.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sender_hash", sa.String(length=64), nullable=False),
        sa.Column("message_type", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            event_status,
            nullable=False,
            server_default="received",
        ),
        sa.Column(
            "outbound_message_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "provider_message_id",
            name="uq_whatsapp_cloud_events_provider_message_id",
        ),
    )
    op.create_index(
        "ix_whatsapp_cloud_events_created_at",
        "whatsapp_cloud_events",
        ["created_at"],
    )
    op.create_index(
        "ix_whatsapp_cloud_events_family_id",
        "whatsapp_cloud_events",
        ["family_id"],
    )
    op.create_index(
        "ix_whatsapp_cloud_events_status",
        "whatsapp_cloud_events",
        ["status"],
    )

    # The browser must never query this operational ledger directly.
    op.execute(
        "REVOKE ALL PRIVILEGES ON TABLE "
        "public.whatsapp_cloud_events FROM anon, authenticated"
    )
    op.execute(
        "ALTER TABLE public.whatsapp_cloud_events "
        "ENABLE ROW LEVEL SECURITY"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_whatsapp_cloud_events_status",
        table_name="whatsapp_cloud_events",
    )
    op.drop_index(
        "ix_whatsapp_cloud_events_family_id",
        table_name="whatsapp_cloud_events",
    )
    op.drop_index(
        "ix_whatsapp_cloud_events_created_at",
        table_name="whatsapp_cloud_events",
    )
    op.drop_table("whatsapp_cloud_events")

    postgresql.ENUM(
        name="whatsapp_cloud_event_status"
    ).drop(op.get_bind(), checkfirst=True)
