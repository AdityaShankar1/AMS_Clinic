from pydantic import BaseModel, ConfigDict

class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    doctor_id: int
    full_name: str
    specialty: str
