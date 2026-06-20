"""add agent and params to tasks

Revision ID: a3a2095dfa03
Revises: a7a5d216d788
Create Date: 2026-06-20 21:33:10.002997

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3a2095dfa03"
down_revision: Union[str, Sequence[str], None] = "a7a5d216d788"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("agent", sa.String(length=32), nullable=False, server_default="claude"),
    )
    op.add_column(
        "tasks",
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.alter_column("tasks", "agent", server_default=None)


def downgrade() -> None:
    op.drop_column("tasks", "params")
    op.drop_column("tasks", "agent")
