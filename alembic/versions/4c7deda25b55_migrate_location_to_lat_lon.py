"""migrate_location_to_lat_lon

Revision ID: 4c7deda25b55
Revises: 3a91f2c4d8e5
Create Date: 2025-10-22 08:02:39.353408

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '4c7deda25b55'
down_revision = '3a91f2c4d8e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new location_lat and location_lon columns
    op.add_column('users', sa.Column('location_lat', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('location_lon', sa.Float(), nullable=True))

    # Drop the old PostGIS location column
    op.drop_column('users', 'location')


def downgrade() -> None:
    # Re-add the old location column (PostGIS geometry)
    from geoalchemy2 import Geometry
    op.add_column('users', sa.Column('location', Geometry('POINT', srid=4326), nullable=True))

    # Drop the new columns
    op.drop_column('users', 'location_lon')
    op.drop_column('users', 'location_lat')

