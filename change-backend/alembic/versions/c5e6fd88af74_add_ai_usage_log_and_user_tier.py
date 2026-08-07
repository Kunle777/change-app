"""add ai_usage_log and user tier

Revision ID: c5e6fd88af74
Revises: 33b7b610b802
Create Date: 2026-08-07 18:58:20.694005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e6fd88af74'
down_revision: Union[str, Sequence[str], None] = '33b7b610b802'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    user_tier = sa.Enum('free', 'premium', name='user_tier')
    user_tier.create(op.get_bind(), checkfirst=True)

    op.create_table('ai_usage_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('tokens_used', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('users', sa.Column('tier', sa.Enum('free', 'premium', name='user_tier'), server_default='free', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'tier')
    op.drop_table('ai_usage_logs')
    sa.Enum(name='user_tier').drop(op.get_bind(), checkfirst=True)
