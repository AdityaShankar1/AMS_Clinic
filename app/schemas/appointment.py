from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Literal

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    scheduled_start: datetime
    duration_minutes: int = 20
    reason_for_visit: str | None = None
    xray_needed: bool = False
    blood_test_needed: bool = False
    patient_priority_label: Literal["auto", "new", "established"] = "auto"
    severity_level: int = 3
    urgency_level: int = 3
    treatment_phase: Literal["one_time", "phased"] = "one_time"
    is_urgent_override: bool = False
    override_reason: str | None = None


class AppointmentPriorityUpdate(BaseModel):
    patient_priority_label: Literal["auto", "new", "established"] | None = None
    severity_level: int | None = None
    urgency_level: int | None = None
    treatment_phase: Literal["one_time", "phased"] | None = None
    priority_summary: str | None = None

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
    patient_priority_label: str
    severity_level: int
    urgency_level: int
    treatment_phase: str
    priority_score: int
    priority_band: str
    priority_summary: str | None
    is_urgent_override: bool
    override_reason: str | None
    rescheduled_to_appointment_id: int | None
