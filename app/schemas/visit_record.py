from pydantic import BaseModel, ConfigDict
from datetime import date

class VisitRecordCreate(BaseModel):
    appointment_id: int
    diagnosis_notes: str | None = None
    treatment_status: str = "in_progress"
    visit_date: date

class VisitRecordUpdate(BaseModel):
    diagnosis_notes: str | None = None
    treatment_status: str | None = None

class VisitRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    visit_record_id: int
    appointment_id: int
    diagnosis_notes: str | None
    treatment_status: str
    visit_date: date
