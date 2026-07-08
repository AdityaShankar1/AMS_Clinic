from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentReschedule,
    AppointmentStatusUpdate,
)
from app.services import booking_service
from app.repositories import appointment_repository as appointment_repo

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"]
)

@router.get("", response_model=List[AppointmentOut])
async def get_appointments(
    doctor_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    on_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch and list appointments filtered by doctor, patient, date, or status.
    Ordered by priority score descending and start time.
    """
    appointments = await appointment_repo.list_appointments(
        db=db,
        doctor_id=doctor_id,
        patient_id=patient_id,
        on_date=on_date,
        status=status,
        limit=limit,
        offset=skip
    )
    return appointments

@router.get("/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific appointment by its ID.
    """
    appointment = await appointment_repo.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found."
        )
    return appointment

@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Book a new appointment via the business logic service layer.
    Ensures cutoff times and overlap validation rules apply.
    """
    try:
        appointment = await booking_service.book_appointment(
            db=db,
            patient_id=payload.patient_id,
            doctor_id=payload.doctor_id,
            scheduled_start=payload.scheduled_start,
            duration_minutes=payload.duration_minutes,
            reason_for_visit=payload.reason_for_visit,
            xray_needed=payload.xray_needed,
            blood_test_needed=payload.blood_test_needed,
            patient_priority_label=payload.patient_priority_label,
            severity_level=payload.severity_level,
            urgency_level=payload.urgency_level,
            treatment_phase=payload.treatment_phase,
            is_urgent_override=payload.is_urgent_override,
            override_reason=payload.override_reason
        )
        return appointment
    except booking_service.BookingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )

@router.put("/{appointment_id}/status", response_model=AppointmentOut)
async def update_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an appointment's operational status (e.g., 'completed', 'no_show').
    """
    appointment = await appointment_repo.update_appointment_status(
        db=db,
        appointment_id=appointment_id,
        status=payload.status
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found."
        )
    return appointment

@router.put("/{appointment_id}/reschedule", response_model=AppointmentOut)
async def reschedule(
    appointment_id: int,
    payload: AppointmentReschedule,
    db: AsyncSession = Depends(get_db)
):
    """
    Reschedule an existing appointment slot to a new timestamp.
    """
    appointment = await appointment_repo.reschedule_appointment(
        db=db,
        appointment_id=appointment_id,
        new_scheduled_start=payload.new_scheduled_start
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found."
        )
    return appointment

@router.delete("/{appointment_id}", response_model=AppointmentOut)
async def cancel_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Soft-deletes an appointment by shifting its status to 'cancelled'.
    Maintains historic logging context per core design specifications.
    """
    appointment = await appointment_repo.update_appointment_status(
        db=db,
        appointment_id=appointment_id,
        status="cancelled"
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found."
        )
    return appointment
