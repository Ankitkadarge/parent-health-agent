"""public-user verification: family status + invite tokens

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-30

Repurposes families.onboarding_status (written once at creation, never read
anywhere in the app) into families.status with a 3-value state machine:
pending_verification -> onboarding -> active.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    family_status = postgresql.ENUM(
        "pending_verification", "onboarding", "active", name="family_status", create_type=False
    )
    family_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "families",
        sa.Column(
            "status",
            family_status,
            nullable=False,
            server_default="pending_verification",
        ),
    )
    op.drop_column("families", "onboarding_status")

    postgresql.ENUM(name="onboarding_status").drop(op.get_bind(), checkfirst=True)

    op.create_table(
        "family_invites",
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
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_family_invites_family_id", "family_invites", ["family_id"])
    op.create_unique_constraint(
        "uq_family_invites_member_id", "family_invites", ["member_id"]
    )
    op.create_unique_constraint("uq_family_invites_token", "family_invites", ["token"])


def downgrade() -> None:
    op.drop_table("family_invites")

    onboarding_status = postgresql.ENUM(
        "pending", "active", name="onboarding_status", create_type=False
    )
    onboarding_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "families",
        sa.Column(
            "onboarding_status",
            onboarding_status,
            nullable=False,
            server_default="pending",
        ),
    )
    op.drop_column("families", "status")

    postgresql.ENUM(name="family_status").drop(op.get_bind(), checkfirst=True)
