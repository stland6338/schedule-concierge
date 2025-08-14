"""initial schema

Revision ID: 20250813_0001
Revises: 
Create Date: 2025-08-13
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250813_0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'),
        sa.Column('locale', sa.String(), nullable=False, server_default='en-US'),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table('tasks',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('due_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('priority', sa.SmallInteger(), nullable=False, server_default='3'),
        sa.Column('dynamic_priority', sa.SmallInteger(), nullable=True, index=True),
        sa.Column('energy_tag', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='Draft', index=True),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )
    op.create_table('calendars',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('external_provider', sa.String(), nullable=True, index=True),
        sa.Column('external_id', sa.String(), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table('events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('calendar_id', sa.String(), sa.ForeignKey('calendars.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('start_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('end_at', sa.DateTime(), nullable=False),
        sa.Column('type', sa.String(), nullable=False, server_default='GENERAL', index=True),
        sa.Column('external_event_id', sa.String(), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )


def downgrade():
    op.drop_table('events')
    op.drop_table('calendars')
    op.drop_table('tasks')
    op.drop_table('users')
