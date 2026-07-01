from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import (
    UserRole, require_role, staff_only, doctor_only, any_role
)
from app.schemas.appointment import (
    AppointmentCreate, AppointmentStatusUpdate, AppointmentReschedule,
    AppointmentPriorityUpdate, AppointmentOut
)
from app.repositories import appointment_repository as repo
from app.services import booking_service
from app.services.priority_service import score_priority

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentOut, status_code=201)
async def book_appointment(
    payload: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Book an appointment. Doctor or Receptionist only."""
    try:
        return await booking_service.book_appointment(db, **payload.model_dump())
    except booking_service.BookingError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[AppointmentOut])
async def list_appointments(
    doctor_id: int | None = None,
    on_date: date | None = None,
    status: str | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """List all appointments. Doctor or Receptionist only."""
    try:
        return await repo.list_appointments(db, doctor_id=doctor_id, on_date=on_date, status=status)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not fetch appointments: {exc}")


@router.get("/my", response_model=list[AppointmentOut])
async def my_appointments(
    x_patient_id: int = Header(...),
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.PATIENT)),
):
    """
    Patient self-service: returns only this patient's own appointments.
    Patient must pass their patient_id in the X-Patient-Id header alongside
    the X-Staff-Key header. (Phase 2 replaces this with a JWT claim.)
    """
    try:
        return await repo.list_appointments(db, patient_id=x_patient_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not fetch appointments: {exc}")


@router.get("/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(
    appointment_id: int,
    x_patient_id: int | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    role: UserRole = Depends(any_role),
):
    """
    Get a single appointment.
    Patients may only view their own appointment.
    """
    appt = await repo.get_appointment_by_id(db, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if role == UserRole.PATIENT:
        if x_patient_id is None or appt.patient_id != x_patient_id:
            raise HTTPException(status_code=403, detail="You can only view your own appointments.")
    return appt


@router.put("/{appointment_id}/status", response_model=AppointmentOut)
async def update_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Update appointment status. Doctor or Receptionist only."""
    try:
        updated = await repo.update_appointment_status(db, appointment_id, payload.status)
        if updated is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Status update failed: {exc}")


@router.put("/{appointment_id}/priority", response_model=AppointmentOut)
async def update_priority(
    appointment_id: int,
    payload: AppointmentPriorityUpdate,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Update the priority labels and recompute the appointment score."""
    appt = await repo.get_appointment_by_id(db, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    completed_visits = 0
    try:
        from app.repositories import patient_repository as patient_repo
        completed_visits = await patient_repo.get_previous_visit_count(db, appt.patient_id)
    except Exception:
        completed_visits = 0

    merged_patient_label = payload.patient_priority_label or appt.patient_priority_label
    merged_severity = payload.severity_level or appt.severity_level
    merged_urgency = payload.urgency_level or appt.urgency_level
    merged_phase = payload.treatment_phase or appt.treatment_phase

    priority = score_priority(
        completed_visits=completed_visits,
        patient_priority_label=merged_patient_label,
        severity_level=merged_severity,
        urgency_level=merged_urgency,
        treatment_phase=merged_phase,
        xray_needed=appt.xray_needed,
        blood_test_needed=appt.blood_test_needed,
        is_urgent_override=appt.is_urgent_override,
    )

    appt.patient_priority_label = priority.patient_priority_label
    appt.severity_level = priority.severity_level
    appt.urgency_level = priority.urgency_level
    appt.treatment_phase = priority.treatment_phase
    appt.priority_score = priority.priority_score
    appt.priority_band = priority.priority_band
    appt.priority_summary = payload.priority_summary or priority.priority_summary
    await db.commit()
    await db.refresh(appt)
    return appt


@router.put("/{appointment_id}/reschedule", response_model=AppointmentOut)
async def reschedule(
    appointment_id: int,
    payload: AppointmentReschedule,
    x_patient_id: int | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    role: UserRole = Depends(any_role),
):
    """
    Reschedule an appointment.
    Patients may only reschedule their own future appointments.
    """
    appt = await repo.get_appointment_by_id(db, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if role == UserRole.PATIENT:
        if x_patient_id is None or appt.patient_id != x_patient_id:
            raise HTTPException(status_code=403, detail="You can only reschedule your own appointments.")
        if appt.status != "scheduled":
            raise HTTPException(status_code=409, detail="Only scheduled appointments can be rescheduled.")

    try:
        updated = await repo.reschedule_appointment(db, appointment_id, payload.new_scheduled_start)
        if updated is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reschedule failed: {exc}")


@router.delete("/{appointment_id}", response_model=AppointmentOut)
async def cancel_appointment(
    appointment_id: int,
    x_patient_id: int | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    role: UserRole = Depends(any_role),
):
    """
    Cancel an appointment (status → 'cancelled', never a hard delete).
    Patients may only cancel their own future appointments.
    """
    appt = await repo.get_appointment_by_id(db, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if role == UserRole.PATIENT:
        if x_patient_id is None or appt.patient_id != x_patient_id:
            raise HTTPException(status_code=403, detail="You can only cancel your own appointments.")
        if appt.status != "scheduled":
            raise HTTPException(status_code=409, detail="Only scheduled appointments can be cancelled.")

    try:
        updated = await repo.update_appointment_status(db, appointment_id, "cancelled")
        return updated
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cancellation failed: {exc}")
