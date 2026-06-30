from pydantic import BaseModel, ConfigDict
from datetime import datetime

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    scheduled_start: datetime
    duration_minutes: int = 20
    reason_for_visit: str | None = None
    xray_needed: bool = False
    blood_test_needed: bool = False
    is_urgent_override: bool = False
    override_reason: str | None = None

class AppointmentStatusUpdate(BaseModel):
    status: str

class AppointmentReschedule(BaseModel):
    new_scheduled_start: datetime

class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    appointment_id: int
    patient_id: int
    doctor_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int
    booked_at: datetime
    status: str
    reason_for_visit: str | None
    xray_needed: bool
    blood_test_needed: bool
    is_urgent_override: bool
    override_reason: str | None
    rescheduled_to_appointment_id: int | None
