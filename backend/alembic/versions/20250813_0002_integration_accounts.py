"""add integration_accounts table

Revision ID: 20250813_0002
Revises: 20250813_0001
Create Date: 2025-08-13
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250813_0002'
down_revision = '20250813_0001'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'integration_accounts' in inspector.get_table_names():
        return  # already exists (e.g. created by metadata.create_all in dev)

    op.create_table(
        'integration_accounts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('access_token_hash', sa.String(), nullable=False),
        sa.Column('refresh_token_hash', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('sync_token', sa.String(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_integration_accounts_user_id', 'integration_accounts', ['user_id'])
    op.create_index('ix_integration_accounts_provider', 'integration_accounts', ['provider'])
    op.create_index('ix_integration_accounts_revoked_at', 'integration_accounts', ['revoked_at'])
    op.create_index('uq_integration_accounts_user_provider', 'integration_accounts', ['user_id','provider'], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'integration_accounts' not in inspector.get_table_names():
        return
    op.drop_index('uq_integration_accounts_user_provider', table_name='integration_accounts')
    op.drop_index('ix_integration_accounts_revoked_at', table_name='integration_accounts')
    op.drop_index('ix_integration_accounts_provider', table_name='integration_accounts')
    op.drop_index('ix_integration_accounts_user_id', table_name='integration_accounts')
    op.drop_table('integration_accounts')
