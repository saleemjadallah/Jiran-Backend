"""Phase 8: Admin log for audit trail

Revision ID: 3a91f2c4d8e5
Revises: be5f12795a69
Create Date: 2025-01-20 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3a91f2c4d8e5'
down_revision: Union[str, None] = 'be5f12795a69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create admin_logs table
    op.create_table(
        'admin_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for admin_logs
    op.create_index('ix_admin_logs_admin_user_id', 'admin_logs', ['admin_user_id'])
    op.create_index('ix_admin_logs_action_type', 'admin_logs', ['action_type'])
    op.create_index('ix_admin_logs_target_id', 'admin_logs', ['target_id'])
    op.create_index('ix_admin_logs_created_at', 'admin_logs', ['created_at'])

    # Create composite index for common queries
    op.create_index(
        'ix_admin_logs_action_created',
        'admin_logs',
        ['action_type', 'created_at']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_admin_logs_action_created', table_name='admin_logs')
    op.drop_index('ix_admin_logs_created_at', table_name='admin_logs')
    op.drop_index('ix_admin_logs_target_id', table_name='admin_logs')
    op.drop_index('ix_admin_logs_action_type', table_name='admin_logs')
    op.drop_index('ix_admin_logs_admin_user_id', table_name='admin_logs')

    # Drop table
    op.drop_table('admin_logs')
