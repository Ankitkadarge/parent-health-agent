"""onboarding answers and parent health profiles

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # member_role already exists (created in 0001) — reuse it, don't recreate the type.
    member_role = postgresql.ENUM("child", "parent", name="member_role", create_type=False)

    op.create_table(
        "parent_health_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("medications", sa.Text(), nullable=True),
        sa.Column("dietary_preferences", sa.Text(), nullable=True),
        sa.Column("activity_level", sa.String(length=50), nullable=True),
        sa.Column("reminder_preferences", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_parent_health_profiles_family_id", "parent_health_profiles", ["family_id"]
    )
    op.create_unique_constraint(
        "uq_parent_health_profiles_parent_member_id",
        "parent_health_profiles",
        ["parent_member_id"],
    )

    op.create_table(
        "onboarding_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("member_role", member_role, nullable=False),
        sa.Column(
            "answered_by_member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column(
            "answered_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_onboarding_answers_family_id", "onboarding_answers", ["family_id"])
    op.create_unique_constraint(
        "uq_onboarding_answers_family_step", "onboarding_answers", ["family_id", "step_key"]
    )


def downgrade() -> None:
    op.drop_table("onboarding_answers")

    op.drop_constraint(
        "uq_parent_health_profiles_parent_member_id",
        "parent_health_profiles",
        type_="unique",
    )
    op.drop_index("ix_parent_health_profiles_family_id", table_name="parent_health_profiles")
    op.drop_table("parent_health_profiles")
