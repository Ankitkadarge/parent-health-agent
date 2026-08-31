"""simplify onboarding to diabetes and medication essentials

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-01

Adds explicit fields for the short MVP onboarding flow and moves any
in-progress legacy onboarding session to the new first question. Existing
legacy profile columns are retained so previously collected data is not lost.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "parent_health_profiles",
        sa.Column("diagnosed_with_diabetes", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "parent_health_profiles",
        sa.Column("taking_medication", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "parent_health_profiles",
        sa.Column("medicine_time", sa.String(length=255), nullable=True),
    )

    # The question keys changed completely. Restart any unfinished legacy
    # session at the first new question without deleting its historical answers.
    op.execute(
        """
        UPDATE onboarding_sessions
        SET current_step = 'diagnosed_with_diabetes'
        WHERE status = 'in_progress'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE onboarding_sessions
        SET current_step = 'preferred_language'
        WHERE status = 'in_progress'
          AND current_step IN (
              'diagnosed_with_diabetes',
              'taking_medication',
              'medicine_time'
          )
        """
    )

    op.drop_column("parent_health_profiles", "medicine_time")
    op.drop_column("parent_health_profiles", "taking_medication")
    op.drop_column("parent_health_profiles", "diagnosed_with_diabetes")
