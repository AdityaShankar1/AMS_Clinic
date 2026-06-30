"""
Phase 1 role-based auth gate.

Three roles, three shared API keys (hardcoded in .env).
The key sent in the X-Staff-Key header determines the caller's role.

Role hierarchy:
  doctor       — full access to everything
  receptionist — can book/manage appointments and patients; cannot write
                 clinical records or delete patients
  patient      — can only view and manage their own appointments;
                 identifies themselves via X-Patient-Id header

In Phase 2 this is replaced by JWT tokens with individual user accounts.
The permission boundaries (what each role can/cannot do) stay identical.
"""
from enum import Enum
from functools import lru_cache
from pydantic import BaseModel

from fastapi import Header, HTTPException

from app.core.config import settings


class UserRole(str, Enum):
    DOCTOR       = "doctor"
    RECEPTIONIST = "receptionist"
    PATIENT      = "patient"


class AuthSession(BaseModel):
    role: UserRole
    patient_id: int | None = None


@lru_cache(maxsize=None)
def _build_key_map() -> dict[str, UserRole]:
    """Build the key→role lookup once at import time."""
    return {
        settings.DOCTOR_KEY:       UserRole.DOCTOR,
        settings.RECEPTIONIST_KEY: UserRole.RECEPTIONIST,
        settings.PATIENT_KEY:      UserRole.PATIENT,
    }


def resolve_role(key: str) -> UserRole | None:
    """Return the role for a given key, or None if the key is invalid."""
    return _build_key_map().get(key)


def resolve_session(x_staff_key: str = Header(...), x_patient_id: int | None = Header(default=None)) -> AuthSession:
    """
    Resolve the caller's session from headers.

    Patients must include X-Patient-Id so the frontend can scope self-service
    appointment access to a single patient record.
    """
    role = resolve_role(x_staff_key)
    if role is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    if not isinstance(x_patient_id, int):
        x_patient_id = None

    if role == UserRole.PATIENT and x_patient_id is None:
        raise HTTPException(status_code=400, detail="Patient sessions require an X-Patient-Id header.")

    return AuthSession(role=role, patient_id=x_patient_id if role == UserRole.PATIENT else None)


def require_role(*allowed: UserRole):
    """
    FastAPI dependency factory.  Usage:

        @router.post("/foo", dependencies=[Depends(require_role(UserRole.DOCTOR))])

    or as a parameter dependency to also receive the resolved role:

        async def my_endpoint(role: UserRole = Depends(require_role(UserRole.DOCTOR, UserRole.RECEPTIONIST))):
            ...
    """
    async def _check(x_staff_key: str = Header(...)) -> UserRole:
        role = resolve_role(x_staff_key)
        if role is None:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")
        if role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role(s): {[r.value for r in allowed]}."
            )
        return role

    return _check


# Convenience shorthands used across routers
staff_only   = require_role(UserRole.DOCTOR, UserRole.RECEPTIONIST)
doctor_only  = require_role(UserRole.DOCTOR)
any_role     = require_role(UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.PATIENT)
