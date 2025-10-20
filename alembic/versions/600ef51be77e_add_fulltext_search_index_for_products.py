"""add_fulltext_search_index_for_products

Revision ID: 600ef51be77e
Revises: 35644ce37583
Create Date: 2025-10-17 18:25:06.815441

This migration adds a GIN (Generalized Inverted Index) for full-text search
on the products table. The index is created on the concatenation of title
and description columns using PostgreSQL's to_tsvector function.

This enables fast full-text search queries for product search functionality.
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '600ef51be77e'
down_revision = '35644ce37583'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GIN index for full-text search on products."""
    # Create GIN index using to_tsvector on title and description
    # This index enables fast full-text search queries
    op.execute("""
        CREATE INDEX idx_products_fulltext_search
        ON products
        USING GIN (to_tsvector('english', title || ' ' || COALESCE(description, '')))
    """)


def downgrade() -> None:
    """Remove GIN index for full-text search."""
    op.execute("DROP INDEX IF EXISTS idx_products_fulltext_search")

