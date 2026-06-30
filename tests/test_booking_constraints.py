"""
Verifies the database-level guarantees designed in Phase 0:
- No two regular (non-urgent) appointments may overlap for the same doctor.
- This is enforced by a Postgres EXCLUDE USING gist constraint, not application code,
  so it holds regardless of which code path inserts a row.

This talks directly to the database via asyncpg rather than going through the app's
ORM/repository layer, since the goal here is to verify the raw database constraint
itself — independent of any future application-level validation logic.
"""
import os
import pytest
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# asyncpg wants a plain postgresql:// URL, not the +asyncpg SQLAlchemy variant
RAW_DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")


@pytest.mark.asyncio
async def test_overlapping_appointments_are_rejected():
    conn = await asyncpg.connect(RAW_DATABASE_URL)

    doctor_id = await conn.fetchval(
        "INSERT INTO doctors (full_name, specialty) VALUES ('Test Doctor', 'ortho') RETURNING doctor_id"
    )
    patient_id = await conn.fetchval(
        "INSERT INTO patients (full_name, date_of_birth, sex, phone_number) "
        "VALUES ('Test Patient', '1990-01-01', 'M', '9999999999') RETURNING patient_id"
    )

    try:
        await conn.execute(
            "INSERT INTO appointments (patient_id, doctor_id, scheduled_start) VALUES ($1, $2, '2026-07-01 17:00:00+05:30')",
            patient_id, doctor_id
        )

        with pytest.raises(asyncpg.exceptions.ExclusionViolationError):
            await conn.execute(
                "INSERT INTO appointments (patient_id, doctor_id, scheduled_start) VALUES ($1, $2, '2026-07-01 17:10:00+05:30')",
                patient_id, doctor_id
            )
    finally:
        await conn.execute("DELETE FROM appointments WHERE doctor_id = $1", doctor_id)
        await conn.execute("DELETE FROM doctors WHERE doctor_id = $1", doctor_id)
        await conn.execute("DELETE FROM patients WHERE patient_id = $1", patient_id)
        await conn.close()


@pytest.mark.asyncio
async def test_non_overlapping_appointments_are_allowed():
    """Sanity check the constraint isn't overly strict — back-to-back, non-overlapping
    appointments for the same doctor should succeed."""
    conn = await asyncpg.connect(RAW_DATABASE_URL)

    doctor_id = await conn.fetchval(
        "INSERT INTO doctors (full_name, specialty) VALUES ('Test Doctor 2', 'perio') RETURNING doctor_id"
    )
    patient_id = await conn.fetchval(
        "INSERT INTO patients (full_name, date_of_birth, sex, phone_number) "
        "VALUES ('Test Patient 2', '1990-01-01', 'F', '8888888888') RETURNING patient_id"
    )

    try:
        await conn.execute(
            "INSERT INTO appointments (patient_id, doctor_id, scheduled_start, duration_minutes) VALUES ($1, $2, '2026-07-01 17:00:00+05:30', 20)",
            patient_id, doctor_id
        )
        # Starts exactly when the first one ends — should NOT be treated as overlapping
        await conn.execute(
            "INSERT INTO appointments (patient_id, doctor_id, scheduled_start, duration_minutes) VALUES ($1, $2, '2026-07-01 17:20:00+05:30', 20)",
            patient_id, doctor_id
        )
        count = await conn.fetchval("SELECT COUNT(*) FROM appointments WHERE doctor_id = $1", doctor_id)
        assert count == 2
    finally:
        await conn.execute("DELETE FROM appointments WHERE doctor_id = $1", doctor_id)
        await conn.execute("DELETE FROM doctors WHERE doctor_id = $1", doctor_id)
        await conn.execute("DELETE FROM patients WHERE patient_id = $1", patient_id)
        await conn.close()
