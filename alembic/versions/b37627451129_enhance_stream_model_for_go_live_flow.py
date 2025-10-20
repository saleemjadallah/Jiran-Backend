"""enhance_stream_model_for_go_live_flow

Revision ID: b37627451129
Revises: 0fa20ccc9b22
Create Date: 2025-10-18 04:30:10.529880

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b37627451129'
down_revision = '0fa20ccc9b22'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Go Live flow fields to streams table
    op.add_column('streams', sa.Column('audience', sa.String(20), server_default='everyone', nullable=False))
    op.add_column('streams', sa.Column('estimated_duration', sa.Integer(), nullable=True))
    op.add_column('streams', sa.Column('notify_followers', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('streams', sa.Column('notify_neighborhood', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('streams', sa.Column('enable_chat', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('streams', sa.Column('enable_comments', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('streams', sa.Column('record_stream', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('streams', sa.Column('vod_url', sa.String(1024), nullable=True))

    # Add analytics fields to streams table
    op.add_column('streams', sa.Column('peak_viewers', sa.Integer(), server_default='0', nullable=False))
    op.add_column('streams', sa.Column('unique_viewers', sa.Integer(), server_default='0', nullable=False))
    op.add_column('streams', sa.Column('total_likes', sa.Integer(), server_default='0', nullable=False))
    op.add_column('streams', sa.Column('chat_messages_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('streams', sa.Column('average_watch_time', sa.Integer(), nullable=True))

    # Create stream_products junction table
    op.create_table(
        'stream_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stream_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('x_position', sa.Float(), nullable=True),
        sa.Column('y_position', sa.Float(), nullable=True),
        sa.Column('timestamp_seconds', sa.Integer(), nullable=True),
        sa.Column('clicks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('views', sa.Integer(), server_default='0', nullable=False),
        sa.Column('inquiries', sa.Integer(), server_default='0', nullable=False),
        sa.Column('purchases', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_stream_products'))
    )

    # Create indexes on stream_products
    op.create_index('ix_stream_products_stream', 'stream_products', ['stream_id'])
    op.create_index('ix_stream_products_product', 'stream_products', ['product_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_stream_products_product', table_name='stream_products')
    op.drop_index('ix_stream_products_stream', table_name='stream_products')

    # Drop stream_products table
    op.drop_table('stream_products')

    # Drop new columns from streams table
    op.drop_column('streams', 'average_watch_time')
    op.drop_column('streams', 'chat_messages_count')
    op.drop_column('streams', 'total_likes')
    op.drop_column('streams', 'unique_viewers')
    op.drop_column('streams', 'peak_viewers')
    op.drop_column('streams', 'vod_url')
    op.drop_column('streams', 'record_stream')
    op.drop_column('streams', 'enable_comments')
    op.drop_column('streams', 'enable_chat')
    op.drop_column('streams', 'notify_neighborhood')
    op.drop_column('streams', 'notify_followers')
    op.drop_column('streams', 'estimated_duration')
    op.drop_column('streams', 'audience')

