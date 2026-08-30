"""whatsapp identities and onboarding sessions

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    onboarding_session_status = postgresql.ENUM(
        "pending", "in_progress", "completed", name="onboarding_session_status", create_type=False
    )
    onboarding_session_status.create(op.get_bind(), checkfirst=True)

    # member_role already exists (created in 0001) — reuse it, don't recreate the type.
    member_role = postgresql.ENUM("child", "parent", name="member_role", create_type=False)

    op.create_table(
        "whatsapp_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("platform_user_id", sa.String(length=255), nullable=True),
        sa.Column("role", member_role, nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_whatsapp_identities_family_id", "whatsapp_identities", ["family_id"])
    op.create_unique_constraint(
        "uq_whatsapp_identities_member_id", "whatsapp_identities", ["member_id"]
    )
    op.create_unique_constraint(
        "uq_whatsapp_identities_phone_e164", "whatsapp_identities", ["phone_e164"]
    )

    op.create_table(
        "onboarding_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            onboarding_session_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_onboarding_sessions_family_id", "onboarding_sessions", ["family_id"]
    )


def downgrade() -> None:
    op.drop_table("onboarding_sessions")

    op.drop_constraint(
        "uq_whatsapp_identities_phone_e164", "whatsapp_identities", type_="unique"
    )
    op.drop_constraint("uq_whatsapp_identities_member_id", "whatsapp_identities", type_="unique")
    op.drop_index("ix_whatsapp_identities_family_id", table_name="whatsapp_identities")
    op.drop_table("whatsapp_identities")

    postgresql.ENUM(name="onboarding_session_status").drop(op.get_bind(), checkfirst=True)
