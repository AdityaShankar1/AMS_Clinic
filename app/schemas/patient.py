from pydantic import BaseModel, ConfigDict
from datetime import date, datetime

class PatientCreate(BaseModel):
    full_name: str
    date_of_birth: date
    sex: str
    phone_number: str
    email: str | None = None
    referred_by_patient_id: int | None = None

class PatientUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    email: str | None = None
    consent_given: bool | None = None

class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    patient_id: int
    full_name: str
    date_of_birth: date
    sex: str
    phone_number: str
    email: str | None
    consent_given: bool
    referred_by_patient_id: int | None
    created_at: datetime
