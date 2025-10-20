"""add_messaging_and_offers_indexes

Revision ID: 0fa20ccc9b22
Revises: 600ef51be77e
Create Date: 2025-10-18 03:38:47.529374

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '0fa20ccc9b22'
down_revision = '600ef51be77e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Performance indexes for messaging and offers queries

    # Conversations: Composite index for finding existing conversations
    op.create_index(
        'ix_conversations_buyer_seller_product',
        'conversations',
        ['buyer_id', 'seller_id', 'product_id'],
        unique=False
    )

    # Conversations: Index for filtering archived conversations
    op.create_index(
        'ix_conversations_archived',
        'conversations',
        ['is_archived_buyer', 'is_archived_seller'],
        unique=False
    )

    # Messages: Composite index for conversation messages ordered by time
    op.create_index(
        'ix_messages_conversation_created',
        'messages',
        ['conversation_id', 'created_at'],
        unique=False
    )

    # Messages: Index for unread messages
    op.create_index(
        'ix_messages_is_read',
        'messages',
        ['is_read'],
        unique=False
    )

    # Offers: Composite index for pending offers near expiration
    op.create_index(
        'ix_offers_status_expires',
        'offers',
        ['status', 'expires_at'],
        unique=False
    )

    # Offers: Index for buyer offers
    op.create_index(
        'ix_offers_buyer_created',
        'offers',
        ['buyer_id', 'created_at'],
        unique=False
    )

    # Offers: Index for seller offers
    op.create_index(
        'ix_offers_seller_created',
        'offers',
        ['seller_id', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('ix_offers_seller_created', table_name='offers')
    op.drop_index('ix_offers_buyer_created', table_name='offers')
    op.drop_index('ix_offers_status_expires', table_name='offers')
    op.drop_index('ix_messages_is_read', table_name='messages')
    op.drop_index('ix_messages_conversation_created', table_name='messages')
    op.drop_index('ix_conversations_archived', table_name='conversations')
    op.drop_index('ix_conversations_buyer_seller_product', table_name='conversations')

