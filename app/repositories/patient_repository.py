"""
Data access layer for Patient records.

Per the project's layered architecture: this is the ONLY place that issues
SQLAlchemy queries against the `patients` table. Services call these functions;
they never construct queries themselves. Routers never touch this layer directly.

No hard deletes — "deleting" a patient is a soft deactivation, per the
non-negotiable design rule in DAILY_LOG.md / project guidelines: medical and
financial history must never be destroyed, only marked inactive.
"""
from datetime import date
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.appointment import Appointment


async def create_patient(
    db: AsyncSession,
    full_name: str,
    date_of_birth: date,
    sex: str,
    phone_number: str,
    email: str | None = None,
    referred_by_patient_id: int | None = None,
) -> Patient:
    patient = Patient(
        full_name=full_name,
        date_of_birth=date_of_birth,
        sex=sex,
        phone_number=phone_number,
        email=email,
        referred_by_patient_id=referred_by_patient_id,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


async def get_patient_by_id(db: AsyncSession, patient_id: int) -> Patient | None:
    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    return result.scalar_one_or_none()


async def search_patients(db: AsyncSession, query: str | None = None) -> list[Patient]:
    """Search by name or phone number substring. No query = list all patients."""
    stmt = select(Patient)
    if query:
        like_pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                Patient.full_name.ilike(like_pattern),
                Patient.phone_number.ilike(like_pattern),
            )
        )
    stmt = stmt.order_by(Patient.full_name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_patient(db: AsyncSession, patient_id: int, **fields) -> Patient | None:
    """Generic partial update. `fields` should only contain columns the caller
    actually provided (e.g. via a Pydantic model's `.dict(exclude_unset=True)`),
    so omitted fields are left untouched."""
    patient = await get_patient_by_id(db, patient_id)
    if patient is None:
        return None
    for key, value in fields.items():
        setattr(patient, key, value)
    await db.commit()
    await db.refresh(patient)
    return patient


async def get_previous_visit_count(db: AsyncSession, patient_id: int) -> int:
    """Derived, never stored — per the project's core design rule.
    Counts only COMPLETED appointments, so cancellations/no-shows don't
    inflate a patient's 'regular visitor' status."""
    result = await db.execute(
        select(func.count())
        .select_from(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.status == "completed",
        )
    )
    return result.scalar_one()
