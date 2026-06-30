"""add scheduled_end column for exclusion constraint

Revision ID: 7b554fe1af61
Revises: 54c77154ea9e
Create Date: 2026-06-30 16:31:58.516493

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '7b554fe1af61'
down_revision: Union[str, Sequence[str], None] = '54c77154ea9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('appointments', sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=True))
    op.execute("""
        UPDATE appointments
        SET scheduled_end = scheduled_start + (duration_minutes * interval '1 minute')
        WHERE scheduled_end IS NULL;
    """)
    op.alter_column('appointments', 'scheduled_end', nullable=False)

    op.execute("""
        CREATE OR REPLACE FUNCTION set_scheduled_end()
        RETURNS trigger AS $$
        BEGIN
            NEW.scheduled_end := NEW.scheduled_start + (NEW.duration_minutes * interval '1 minute');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_set_scheduled_end
        BEFORE INSERT OR UPDATE OF scheduled_start, duration_minutes ON appointments
        FOR EACH ROW EXECUTE FUNCTION set_scheduled_end();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_set_scheduled_end ON appointments;")
    op.execute("DROP FUNCTION IF EXISTS set_scheduled_end();")
    op.drop_column('appointments', 'scheduled_end')
