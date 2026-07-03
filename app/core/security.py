from dataclasses import dataclass
from enum import Enum
from fastapi import Header, HTTPException
from app.core.config import settings


class UserRole(str, Enum):
    DOCTOR       = "doctor"
    RECEPTIONIST = "receptionist"
    PATIENT      = "patient"


@dataclass
class AuthSession:
    user_id: int
    role: UserRole
    patient_id: int | None


def resolve_role(key: str) -> UserRole | None:
    if key == settings.DOCTOR_KEY:       return UserRole.DOCTOR
    if key == settings.RECEPTIONIST_KEY: return UserRole.RECEPTIONIST
    if key == settings.PATIENT_KEY:      return UserRole.PATIENT
    return None


async def resolve_session(x_staff_key: str = Header(...)) -> AuthSession:
    role = resolve_role(x_staff_key)
    if role is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    patient_id = settings.DEMO_PATIENT_ID if role == UserRole.PATIENT else None
    return AuthSession(user_id=0, role=role, patient_id=patient_id)


def require_role(*allowed: UserRole):
    async def _check(x_staff_key: str = Header(...)) -> UserRole:
        role = resolve_role(x_staff_key)
        if role is None:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")
        if role not in allowed:
            raise HTTPException(status_code=403, detail=f"Access denied. Required: {[r.value for r in allowed]}.")
        return role
    return _check


def require_role_session(*allowed: UserRole):
    async def _check(x_staff_key: str = Header(...)) -> AuthSession:
        role = resolve_role(x_staff_key)
        if role is None:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")
        if role not in allowed:
            raise HTTPException(status_code=403, detail=f"Access denied. Required: {[r.value for r in allowed]}.")
        patient_id = settings.DEMO_PATIENT_ID if role == UserRole.PATIENT else None
        return AuthSession(user_id=0, role=role, patient_id=patient_id)
    return _check


staff_only  = require_role(UserRole.DOCTOR, UserRole.RECEPTIONIST)
doctor_only = require_role(UserRole.DOCTOR)
any_role    = require_role(UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.PATIENT)
