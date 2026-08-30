"""initial schema: families and members

Revision ID: 0001
Revises:
Create Date: 2026-08-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    onboarding_status = postgresql.ENUM(
    "pending", "active", name="onboarding_status", create_type=False
)
    onboarding_status.create(op.get_bind(), checkfirst=True)

    member_role = postgresql.ENUM(
    "child", "parent", name="member_role", create_type=False
)
    member_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "families",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "onboarding_status",
            onboarding_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", member_role, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("preferred_language", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_members_family_id", "members", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_members_family_id", table_name="members")
    op.drop_table("members")
    op.drop_table("families")

    postgresql.ENUM(name="member_role").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="onboarding_status").drop(op.get_bind(), checkfirst=True)
