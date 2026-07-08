"""
Data access layer for Appointment records.

This layer does NOT enforce the overlap or cutoff-time rules — those live in
app/services/booking_service.py. This layer's job is purely to read and write
rows; the database constraint (EXCLUDE USING gist) is the final backstop for
overlap, and booking_service is responsible for the cutoff-time check and for
catching/translating the database's rejection into a clean application error.

No hard deletes — "cancelling" an appointment is a status change, never a row
removal, per the project's core design rule.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment


async def create_appointment(
    db: AsyncSession,
    patient_id: int,
    doctor_id: int,
    scheduled_start: datetime,
    duration_minutes: int = 20,
    reason_for_visit: str | None = None,
    xray_needed: bool = False,
    blood_test_needed: bool = False,
    patient_priority_label: str = "auto",
    severity_level: int = 3,
    urgency_level: int = 3,
    treatment_phase: str = "one_time",
    priority_score: int = 0,
    priority_band: str = "routine",
    priority_summary: str | None = None,
    is_urgent_override: bool = False,
    override_reason: str | None = None,
) -> Appointment:
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        scheduled_start=scheduled_start,
        duration_minutes=duration_minutes,
        reason_for_visit=reason_for_visit,
        xray_needed=xray_needed,
        blood_test_needed=blood_test_needed,
        patient_priority_label=patient_priority_label,
        severity_level=severity_level,
        urgency_level=urgency_level,
        treatment_phase=treatment_phase,
        priority_score=priority_score,
        priority_band=priority_band,
        priority_summary=priority_summary,
        is_urgent_override=is_urgent_override,
        override_reason=override_reason,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


async def get_appointment_by_id(db: AsyncSession, appointment_id: int) -> Appointment | None:
    result = await db.execute(
        select(Appointment).where(Appointment.appointment_id == appointment_id)
    )
    return result.scalar_one_or_none()


async def list_appointments(
    db: AsyncSession,
    doctor_id: int | None = None,
    patient_id: int | None = None,
    on_date: date | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[Appointment]:
    stmt = select(Appointment)
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if on_date is not None:
        stmt = stmt.where(
            Appointment.scheduled_start >= datetime.combine(on_date, datetime.min.time()),
            Appointment.scheduled_start < datetime.combine(on_date, datetime.max.time()),
        )
    if status is not None:
        stmt = stmt.where(Appointment.status == status)
    stmt = stmt.order_by(Appointment.priority_score.desc(), Appointment.scheduled_start)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_appointment_status(
    db: AsyncSession,
    appointment_id: int,
    status: str,
) -> Appointment | None:
    """Status changes only — completed / cancelled / no_show / rescheduled.
    Never deletes the row."""
    appointment = await get_appointment_by_id(db, appointment_id)
    if appointment is None:
        return None
    appointment.status = status
    await db.commit()
    await db.refresh(appointment)
    return appointment


async def reschedule_appointment(
    db: AsyncSession,
    appointment_id: int,
    new_scheduled_start: datetime,
) -> Appointment | None:
    """Moves an appointment to a new time. Does not change duration or doctor."""
    appointment = await get_appointment_by_id(db, appointment_id)
    if appointment is None:
        return None
    appointment.scheduled_start = new_scheduled_start
    await db.commit()
    await db.refresh(appointment)
    return appointment


async def link_reschedule(
    db: AsyncSession,
    original_appointment_id: int,
    new_appointment_id: int,
) -> Appointment | None:
    """Marks the original appointment as 'rescheduled' and links it to the new
    one, per the urgent-override design from Phase 0 — preserves the trail of
    why a patient got bumped, instead of losing that context the way the
    paper diary would."""
    original = await get_appointment_by_id(db, original_appointment_id)
    if original is None:
        return None
    original.status = "rescheduled"
    original.rescheduled_to_appointment_id = new_appointment_id
    await db.commit()
    await db.refresh(original)
    return original


async def check_overlap_exists(
    db: AsyncSession,
    doctor_id: int,
    scheduled_start: datetime,
    duration_minutes: int,
) -> bool:
    """Pre-flight check used by booking_service to give a friendly error
    BEFORE attempting the insert. This is a courtesy, not the source of
    truth — the database's EXCLUDE constraint is still the real guarantee,
    since this query has an inherent race condition under concurrent
    requests that only the database-level constraint can fully close."""
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.is_urgent_override == False,  # noqa: E712
        Appointment.status != "cancelled",
        Appointment.scheduled_start < scheduled_start + timedelta(minutes=duration_minutes),
        Appointment.scheduled_end > scheduled_start,
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None
