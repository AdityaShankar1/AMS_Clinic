from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.appointment import (
    AppointmentCreate, AppointmentStatusUpdate, AppointmentReschedule, AppointmentOut
)
from app.repositories import appointment_repository as repo
from app.services import booking_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentOut, status_code=201)
async def book_appointment(payload: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await booking_service.book_appointment(db, **payload.model_dump())
    except booking_service.BookingError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[AppointmentOut])
async def list_appointments(
    doctor_id: int | None = None,
    on_date: date | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await repo.list_appointments(db, doctor_id=doctor_id, on_date=on_date, status=status)


@router.get("/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    appt = await repo.get_appointment_by_id(db, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.put("/{appointment_id}/status", response_model=AppointmentOut)
async def update_status(appointment_id: int, payload: AppointmentStatusUpdate, db: AsyncSession = Depends(get_db)):
    updated = await repo.update_appointment_status(db, appointment_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return updated


@router.put("/{appointment_id}/reschedule", response_model=AppointmentOut)
async def reschedule(appointment_id: int, payload: AppointmentReschedule, db: AsyncSession = Depends(get_db)):
    updated = await repo.reschedule_appointment(db, appointment_id, payload.new_scheduled_start)
    if updated is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return updated


@router.delete("/{appointment_id}", response_model=AppointmentOut)
async def cancel_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    """Cancellation is a status change, never a row delete."""
    updated = await repo.update_appointment_status(db, appointment_id, "cancelled")
    if updated is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return updated
