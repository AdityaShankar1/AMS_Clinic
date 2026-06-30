from pydantic import BaseModel, ConfigDict

from app.core.security import UserRole


class AuthSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: UserRole
    patient_id: int | None = None
