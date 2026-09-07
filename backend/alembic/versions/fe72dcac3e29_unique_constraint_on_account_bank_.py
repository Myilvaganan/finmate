"""unique constraint on account bank+number per user

Revision ID: fe72dcac3e29
Revises: e306941602cf
Create Date: 2026-09-07 13:58:29.956549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe72dcac3e29'
down_revision: Union[str, None] = 'e306941602cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_accounts_user_bank_number", "accounts", ["user_id", "bank_name", "masked_account_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_accounts_user_bank_number", "accounts", type_="unique")
