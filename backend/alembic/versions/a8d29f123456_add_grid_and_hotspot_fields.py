"""add_grid_and_hotspot_fields

Revision ID: a8d29f123456
Revises: 069fa0c40831
Create Date: 2026-08-14 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a8d29f123456'
down_revision: Union[str, None] = '069fa0c40831'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('grid_cells', sa.Column('h3_index', sa.String(), nullable=True))
    op.add_column('grid_cells', sa.Column('damage_class', sa.String(), nullable=True))
    
    op.add_column('hotspot_results', sa.Column('h3_index', sa.String(), nullable=True))
    op.add_column('hotspot_results', sa.Column('classification', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('hotspot_results', 'classification')
    op.drop_column('hotspot_results', 'h3_index')
    op.drop_column('grid_cells', 'damage_class')
    op.drop_column('grid_cells', 'h3_index')
