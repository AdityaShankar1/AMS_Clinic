from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"]
)

# Pydantic schema mapping the fields visible in Screenshot 2026-07-03 at 7.22.28 PM.jpg
class AppointmentCreate(BaseModel):
    patient_id: int
    doctor: str
    start_time: str
    duration: str
    reason: Optional[str] = None
    patient_type: Optional[str] = None
    severity: Optional[str] = None
    urgency: Optional[str] = None
    treatment_phase: Optional[str] = None
    xray_required: Optional[bool] = False
    blood_test_required: Optional[bool] = False
    urgent_override: Optional[bool] = False

@router.get("")
async def get_appointments():
    return [
        {
            "id": 1,
            "patient_name": "Test Patient",
            "time": "10:00 AM",
            "status": "scheduled"
        }
    ]

@router.post("")
async def create_appointment(payload: AppointmentCreate):
    # For now, return a success response matching what the UI expects to close the modal
    return {
        "status": "success",
        "message": "Appointment booked successfully",
        "appointment": {
            "id": 2,
            "patient_id": payload.patient_id,
            "doctor": payload.doctor,
            "time": payload.start_time,
            "status": "scheduled"
        }
    }
