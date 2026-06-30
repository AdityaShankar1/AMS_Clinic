"""
Data access layer for VisitRecord. No hard deletes — ever. Medical records
are never removed through this layer, period.
"""
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visit_record import VisitRecord


async def create_visit_record(
    db: AsyncSession,
    appointment_id: int,
    visit_date: date,
    diagnosis_notes: str | None = None,
    treatment_status: str = "in_progress",
) -> VisitRecord:
    record = VisitRecord(
        appointment_id=appointment_id,
        visit_date=visit_date,
        diagnosis_notes=diagnosis_notes,
        treatment_status=treatment_status,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_visit_record_by_id(db: AsyncSession, visit_record_id: int) -> VisitRecord | None:
    result = await db.execute(
        select(VisitRecord).where(VisitRecord.visit_record_id == visit_record_id)
    )
    return result.scalar_one_or_none()


async def get_visit_record_by_appointment(db: AsyncSession, appointment_id: int) -> VisitRecord | None:
    result = await db.execute(
        select(VisitRecord).where(VisitRecord.appointment_id == appointment_id)
    )
    return result.scalar_one_or_none()


async def list_visit_records_for_patient(db: AsyncSession, patient_id: int) -> list[VisitRecord]:
    """Patient's visit history — joins through appointments since VisitRecord
    has no direct patient_id column (intentional, per Phase 0 design: bill/
    record what was actually done, traced back through the appointment)."""
    from app.models.appointment import Appointment

    stmt = (
        select(VisitRecord)
        .join(Appointment, VisitRecord.appointment_id == Appointment.appointment_id)
        .where(Appointment.patient_id == patient_id)
        .order_by(VisitRecord.visit_date.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_visit_record(db: AsyncSession, visit_record_id: int, **fields) -> VisitRecord | None:
    record = await get_visit_record_by_id(db, visit_record_id)
    if record is None:
        return None
    for key, value in fields.items():
        setattr(record, key, value)
    await db.commit()
    await db.refresh(record)
    return record
