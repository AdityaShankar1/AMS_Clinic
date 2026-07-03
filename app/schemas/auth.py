from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str


class AuthSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    role: str
    patient_id: int | None
