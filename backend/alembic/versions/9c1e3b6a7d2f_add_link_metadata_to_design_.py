"""add link metadata to design relationships

Revision ID: 9c1e3b6a7d2f
Revises: 071ff4ab5de0
Create Date: 2026-09-18 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9c1e3b6a7d2f'
down_revision: Union[str, None] = '071ff4ab5de0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('design_relationships', sa.Column('link_type', sa.String(length=50), nullable=True))
    op.add_column('design_relationships', sa.Column('speed_mbps', sa.Integer(), nullable=True))
    op.add_column('design_relationships', sa.Column('vlan', sa.Integer(), nullable=True))
    op.add_column('design_relationships', sa.Column('subnet', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('design_relationships', 'subnet')
    op.drop_column('design_relationships', 'vlan')
    op.drop_column('design_relationships', 'speed_mbps')
    op.drop_column('design_relationships', 'link_type')
