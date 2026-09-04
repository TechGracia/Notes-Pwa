"""add google oauth fields

Revision ID: d6d25811824c
Revises: d9db73826718
Create Date: 2026-09-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d6d25811824c"
down_revision: Union[str, Sequence[str], None] = "d9db73826718"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ---------------------------------------------------------
    # Add Google OAuth columns
    # ---------------------------------------------------------

    # Add these temporarily as nullable because existing users
    # already exist in the database.
    op.add_column(
        "users",
        sa.Column(
            "google_id",
            sa.String(length=255),
            nullable=True
        )
    )

    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.String(length=50),
            nullable=True
        )
    )

    # ---------------------------------------------------------
    # Existing users are local/password users
    # ---------------------------------------------------------

    op.execute(
        "UPDATE users SET auth_provider = 'local' "
        "WHERE auth_provider IS NULL"
    )

    # ---------------------------------------------------------
    # OAuth users may not have a password
    # ---------------------------------------------------------

    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=True
    )

    # ---------------------------------------------------------
    # auth_provider is now required
    # ---------------------------------------------------------

    op.alter_column(
        "users",
        "auth_provider",
        existing_type=sa.String(length=50),
        nullable=False
    )

    # ---------------------------------------------------------
    # Index Google ID
    # ---------------------------------------------------------

    op.create_index(
        "ix_users_google_id",
        "users",
        ["google_id"],
        unique=False
    )


def downgrade() -> None:

    op.drop_index(
        "ix_users_google_id",
        table_name="users"
    )

    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=False
    )

    op.drop_column(
        "users",
        "auth_provider"
    )

    op.drop_column(
        "users",
        "google_id"
    )