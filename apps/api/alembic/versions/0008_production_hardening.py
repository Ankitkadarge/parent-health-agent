"""production hardening and hashed invitation tokens

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-02

"""
import hashlib
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep raw invitation tokens out of PostgreSQL. Renaming preserves the
    # existing unique constraint; values are replaced with SHA-256 digests.
    op.alter_column(
        "family_invites",
        "token",
        new_column_name="token_hash",
        existing_type=sa.String(length=64),
        existing_nullable=False,
    )

    connection = op.get_bind()
    rows = (
        connection.execute(
            sa.text("SELECT id, token_hash FROM family_invites")
        )
        .mappings()
        .all()
    )

    for row in rows:
        raw_token = row["token_hash"]
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        connection.execute(
            sa.text(
                "UPDATE family_invites "
                "SET token_hash = :token_hash "
                "WHERE id = :invite_id"
            ),
            {"token_hash": token_hash, "invite_id": row["id"]},
        )

    op.create_unique_constraint(
        "uq_members_family_role",
        "members",
        ["family_id", "role"],
    )
    op.create_unique_constraint(
        "uq_members_phone_e164",
        "members",
        ["phone_e164"],
    )
    op.create_unique_constraint(
        "uq_whatsapp_identities_family_role",
        "whatsapp_identities",
        ["family_id", "role"],
    )
    op.create_index(
        "ix_family_invites_expires_at",
        "family_invites",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_family_invites_expires_at",
        table_name="family_invites",
    )
    op.drop_constraint(
        "uq_whatsapp_identities_family_role",
        "whatsapp_identities",
        type_="unique",
    )
    op.drop_constraint(
        "uq_members_phone_e164",
        "members",
        type_="unique",
    )
    op.drop_constraint(
        "uq_members_family_role",
        "members",
        type_="unique",
    )

    # Raw tokens cannot be reconstructed from hashes. Remove outstanding
    # invitations before restoring the legacy column name.
    op.execute("DELETE FROM family_invites")
    op.alter_column(
        "family_invites",
        "token_hash",
        new_column_name="token",
        existing_type=sa.String(length=64),
        existing_nullable=False,
    )
