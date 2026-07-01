"""add appointment priority fields

Revision ID: a1c3e5d7b9f0
Revises: 7b554fe1af61
Create Date: 2026-07-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c3e5d7b9f0"
down_revision: Union[str, Sequence[str], None] = "7b554fe1af61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column("patient_priority_label", sa.String(length=20), nullable=True, server_default="auto"),
    )
    op.add_column(
        "appointments",
        sa.Column("severity_level", sa.Integer(), nullable=True, server_default="3"),
    )
    op.add_column(
        "appointments",
        sa.Column("urgency_level", sa.Integer(), nullable=True, server_default="3"),
    )
    op.add_column(
        "appointments",
        sa.Column("treatment_phase", sa.String(length=20), nullable=True, server_default="one_time"),
    )
    op.add_column(
        "appointments",
        sa.Column("priority_score", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "appointments",
        sa.Column("priority_band", sa.String(length=20), nullable=True, server_default="routine"),
    )
    op.add_column(
        "appointments",
        sa.Column("priority_summary", sa.String(length=255), nullable=True),
    )

    op.execute(
        """
        WITH visit_counts AS (
            SELECT
                a.appointment_id,
                CASE
                    WHEN (
                        SELECT COUNT(*)
                        FROM appointments prev
                        WHERE prev.patient_id = a.patient_id
                          AND prev.status = 'completed'
                          AND prev.scheduled_start < a.scheduled_start
                    ) = 0 THEN 'new'
                    ELSE 'established'
                END AS label
            FROM appointments a
        )
        UPDATE appointments appt
        SET
            patient_priority_label = visit_counts.label,
            severity_level = COALESCE(appt.severity_level, 3),
            urgency_level = COALESCE(appt.urgency_level, 3),
            treatment_phase = COALESCE(appt.treatment_phase, 'one_time'),
            priority_score = LEAST(
                100,
                GREATEST(
                    0,
                    CASE WHEN visit_counts.label = 'new' THEN 15 ELSE 8 END
                    + COALESCE(appt.severity_level, 3) * 6
                    + COALESCE(appt.urgency_level, 3) * 7
                    + CASE WHEN COALESCE(appt.treatment_phase, 'one_time') = 'phased' THEN 12 ELSE 4 END
                    + CASE WHEN appt.xray_needed THEN 3 ELSE 0 END
                    + CASE WHEN appt.blood_test_needed THEN 3 ELSE 0 END
                    + CASE WHEN appt.is_urgent_override THEN 10 ELSE 0 END
                )
            ),
            priority_band = CASE
                WHEN (
                    CASE WHEN visit_counts.label = 'new' THEN 15 ELSE 8 END
                    + COALESCE(appt.severity_level, 3) * 6
                    + COALESCE(appt.urgency_level, 3) * 7
                    + CASE WHEN COALESCE(appt.treatment_phase, 'one_time') = 'phased' THEN 12 ELSE 4 END
                    + CASE WHEN appt.xray_needed THEN 3 ELSE 0 END
                    + CASE WHEN appt.blood_test_needed THEN 3 ELSE 0 END
                    + CASE WHEN appt.is_urgent_override THEN 10 ELSE 0 END
                ) >= 75 THEN 'critical'
                WHEN (
                    CASE WHEN visit_counts.label = 'new' THEN 15 ELSE 8 END
                    + COALESCE(appt.severity_level, 3) * 6
                    + COALESCE(appt.urgency_level, 3) * 7
                    + CASE WHEN COALESCE(appt.treatment_phase, 'one_time') = 'phased' THEN 12 ELSE 4 END
                    + CASE WHEN appt.xray_needed THEN 3 ELSE 0 END
                    + CASE WHEN appt.blood_test_needed THEN 3 ELSE 0 END
                    + CASE WHEN appt.is_urgent_override THEN 10 ELSE 0 END
                ) >= 55 THEN 'high'
                WHEN (
                    CASE WHEN visit_counts.label = 'new' THEN 15 ELSE 8 END
                    + COALESCE(appt.severity_level, 3) * 6
                    + COALESCE(appt.urgency_level, 3) * 7
                    + CASE WHEN COALESCE(appt.treatment_phase, 'one_time') = 'phased' THEN 12 ELSE 4 END
                    + CASE WHEN appt.xray_needed THEN 3 ELSE 0 END
                    + CASE WHEN appt.blood_test_needed THEN 3 ELSE 0 END
                    + CASE WHEN appt.is_urgent_override THEN 10 ELSE 0 END
                ) >= 35 THEN 'medium'
                ELSE 'routine'
            END,
            priority_summary = LEFT(
                (
                    CASE
                        WHEN visit_counts.label = 'new' THEN 'new patient'
                        ELSE 'established patient'
                    END
                    || '; severity ' || COALESCE(appt.severity_level, 3) || '/5'
                    || '; urgency ' || COALESCE(appt.urgency_level, 3) || '/5'
                    || CASE
                        WHEN COALESCE(appt.treatment_phase, 'one_time') = 'phased' THEN '; phased treatment'
                        ELSE '; one-time issue'
                    END
                    || CASE WHEN appt.xray_needed THEN '; x-ray report required' ELSE '' END
                    || CASE WHEN appt.blood_test_needed THEN '; blood test report required' ELSE '' END
                    || CASE WHEN appt.is_urgent_override THEN '; urgent override' ELSE '' END
                ),
                255
            )
        FROM visit_counts
        WHERE appt.appointment_id = visit_counts.appointment_id;
        """
    )

    op.alter_column("appointments", "patient_priority_label", nullable=False)
    op.alter_column("appointments", "severity_level", nullable=False)
    op.alter_column("appointments", "urgency_level", nullable=False)
    op.alter_column("appointments", "treatment_phase", nullable=False)
    op.alter_column("appointments", "priority_score", nullable=False)
    op.alter_column("appointments", "priority_band", nullable=False)


def downgrade() -> None:
    op.drop_column("appointments", "priority_summary")
    op.drop_column("appointments", "priority_band")
    op.drop_column("appointments", "priority_score")
    op.drop_column("appointments", "treatment_phase")
    op.drop_column("appointments", "urgency_level")
    op.drop_column("appointments", "severity_level")
    op.drop_column("appointments", "patient_priority_label")
