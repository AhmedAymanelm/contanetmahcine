"""Add TikTok columns to oauth_tokens (refresh_token, open_id, scopes, refresh_expires_at)

Revision ID: f1a2b3c4d5e6
Revises: e736e67f7c35
Create Date: 2026-08-10 14:52:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'bc75541ce016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add columns needed for TikTok OAuth (safe to add; nullable for all existing rows)."""
    with op.batch_alter_table('oauth_tokens') as batch_op:
        batch_op.add_column(sa.Column('refresh_token', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('open_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('scopes', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('refresh_expires_at', sa.DateTime(), nullable=True))
        # Also widen access_token from String to Text (safe for PostgreSQL)
        batch_op.alter_column('access_token', type_=sa.Text(), existing_nullable=False)


def downgrade() -> None:
    """Remove TikTok-specific columns."""
    with op.batch_alter_table('oauth_tokens') as batch_op:
        batch_op.drop_column('refresh_expires_at')
        batch_op.drop_column('scopes')
        batch_op.drop_column('open_id')
        batch_op.drop_column('refresh_token')
        batch_op.alter_column('access_token', type_=sa.String(), existing_nullable=False)
