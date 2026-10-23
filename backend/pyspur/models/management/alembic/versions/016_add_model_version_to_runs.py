# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
"""add_model_version_to_runs

Revision ID: 016
Revises: 015
Create Date: 2026-06-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("model_version", sa.String(), nullable=True))

    # Backfill existing runs with the default model version.
    op.execute("UPDATE runs SET model_version = '1.0' WHERE model_version IS NULL")


def downgrade() -> None:
    op.drop_column("runs", "model_version")
