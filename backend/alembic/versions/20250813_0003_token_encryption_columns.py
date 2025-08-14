"""add encrypted token columns

Revision ID: 0003_token_encryption
Revises: 0002_integration_accounts
Create Date: 2025-08-13
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_token_encryption'
down_revision = '0002_integration_accounts'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('integration_accounts') as batch_op:
        batch_op.add_column(sa.Column('access_token_encrypted', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('refresh_token_encrypted', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('integration_accounts') as batch_op:
        batch_op.drop_column('access_token_encrypted')
        batch_op.drop_column('refresh_token_encrypted')
