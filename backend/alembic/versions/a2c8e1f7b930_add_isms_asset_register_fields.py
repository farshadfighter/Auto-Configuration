"""add isms asset register fields

Revision ID: a2c8e1f7b930
Revises: 65faefaf880e
Create Date: 2026-09-12T00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a2c8e1f7b930'
down_revision: Union[str, None] = '65faefaf880e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum types must be created explicitly before add_column on an existing table (unlike
    # op.create_table, which compiles CREATE TYPE automatically).
    information_classification_enum = sa.Enum(
        'public', 'internal', 'confidential', 'restricted', name='information_classification'
    )
    information_classification_enum.create(op.get_bind(), checkfirst=True)
    backup_frequency_enum = sa.Enum('none', 'daily', 'weekly', 'monthly', name='backup_frequency')
    backup_frequency_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'assets',
        sa.Column(
            'information_classification', information_classification_enum, nullable=False, server_default='internal'
        ),
    )
    op.add_column('assets', sa.Column('custodian_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('assets', sa.Column('acquired_at', sa.Date(), nullable=True))
    op.add_column('assets', sa.Column('warranty_expires_at', sa.Date(), nullable=True))
    op.add_column('assets', sa.Column('planned_retirement_at', sa.Date(), nullable=True))
    op.add_column('assets', sa.Column('decommissioned_at', sa.Date(), nullable=True))
    op.add_column('assets', sa.Column('disposal_method', sa.String(length=100), nullable=True))
    op.add_column('assets', sa.Column('disposal_notes', sa.Text(), nullable=True))
    op.add_column('assets', sa.Column('risk_assessment_ref', sa.String(length=255), nullable=True))
    op.add_column('assets', sa.Column('risk_last_reviewed_at', sa.Date(), nullable=True))
    op.add_column('assets', sa.Column('backup_required', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('assets', sa.Column('backup_frequency', backup_frequency_enum, nullable=True))
    op.create_foreign_key(
        'fk_assets_custodian_id_users', 'assets', 'users', ['custodian_id'], ['id']
    )

    op.create_table(
        'compliance_frameworks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_table(
        'asset_compliance_scope_map',
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('compliance_framework_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['compliance_framework_id'], ['compliance_frameworks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('asset_id', 'compliance_framework_id'),
    )


def downgrade() -> None:
    op.drop_table('asset_compliance_scope_map')
    op.drop_table('compliance_frameworks')
    op.drop_constraint('fk_assets_custodian_id_users', 'assets', type_='foreignkey')
    op.drop_column('assets', 'backup_frequency')
    op.drop_column('assets', 'backup_required')
    op.drop_column('assets', 'risk_last_reviewed_at')
    op.drop_column('assets', 'risk_assessment_ref')
    op.drop_column('assets', 'disposal_notes')
    op.drop_column('assets', 'disposal_method')
    op.drop_column('assets', 'decommissioned_at')
    op.drop_column('assets', 'planned_retirement_at')
    op.drop_column('assets', 'warranty_expires_at')
    op.drop_column('assets', 'acquired_at')
    op.drop_column('assets', 'custodian_id')
    op.drop_column('assets', 'information_classification')
    sa.Enum(name='backup_frequency').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='information_classification').drop(op.get_bind(), checkfirst=True)
