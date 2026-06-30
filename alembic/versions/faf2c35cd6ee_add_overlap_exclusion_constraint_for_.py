"""add overlap exclusion constraint for appointments

Revision ID: faf2c35cd6ee
Revises: 2ab99cab8d92
Create Date: 2026-06-30 16:08:55.587099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'faf2c35cd6ee'
down_revision: Union[str, Sequence[str], None] = '2ab99cab8d92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
    op.execute("""
        ALTER TABLE appointments
        ADD CONSTRAINT no_overlap_for_regular_bookings
        EXCLUDE USING gist (
            doctor_id WITH =,
            tstzrange(scheduled_start, scheduled_end) WITH &&
        )
        WHERE (is_urgent_override = false AND status <> 'cancelled');
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE appointments DROP CONSTRAINT no_overlap_for_regular_bookings;")
    op.execute("DROP EXTENSION IF EXISTS btree_gist;")
