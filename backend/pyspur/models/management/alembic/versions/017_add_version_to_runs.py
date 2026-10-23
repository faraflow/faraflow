# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
"""add version and updated_at to runs

Revision ID: 017
Revises: 016
Create Date: 2026-06-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Monotonic change token + last-modified timestamp used by the lightweight
    # status heartbeat to detect meaningful run changes without loading tasks.
    op.add_column(
        "runs",
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("runs", sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "updated_at")
    op.drop_column("runs", "version")
