"""security hardening for Supabase-exposed public tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-31

The application talks to PostgreSQL through the FastAPI backend. Browser-facing
Supabase roles therefore do not need direct table access. This migration revokes
that access, enables RLS as a deny-by-default safety boundary, and adds the one
missing foreign-key index reported by the database advisor.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = (
    "alembic_version",
    "families",
    "members",
    "whatsapp_identities",
    "family_invites",
    "onboarding_sessions",
    "onboarding_answers",
    "parent_health_profiles",
)


def upgrade() -> None:
    # Supabase creates these roles, but local PostgreSQL installations may not.
    # Guarding the revokes keeps the migration portable for local development.
    op.execute(
        """
        DO $security$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL PRIVILEGES ON TABLE
                    public.alembic_version,
                    public.families,
                    public.members,
                    public.whatsapp_identities,
                    public.family_invites,
                    public.onboarding_sessions,
                    public.onboarding_answers,
                    public.parent_health_profiles
                FROM anon;
                REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM anon;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE ALL ON TABLES FROM anon;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE ALL ON SEQUENCES FROM anon;
            END IF;

            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL PRIVILEGES ON TABLE
                    public.alembic_version,
                    public.families,
                    public.members,
                    public.whatsapp_identities,
                    public.family_invites,
                    public.onboarding_sessions,
                    public.onboarding_answers,
                    public.parent_health_profiles
                FROM authenticated;
                REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE ALL ON TABLES FROM authenticated;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    REVOKE ALL ON SEQUENCES FROM authenticated;
            END IF;
        END
        $security$;
        """
    )

    for table in TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_onboarding_answers_answered_by_member_id
        ON public.onboarding_answers (answered_by_member_id)
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS public.ix_onboarding_answers_answered_by_member_id"
    )

    for table in reversed(TABLES):
        op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY')

    # Intentionally do not restore broad anon/authenticated grants. Re-introducing
    # direct public access should require a separate, explicit migration with
    # narrowly scoped RLS policies.
