"""
Dual-mode auth — accepts both:
  1. Legacy X-Staff-Key header (Phase 1 hardcoded keys, still works)
  2. JWT Bearer token (Phase 2a, proper user accounts)

This lets existing clients (Bootstrap GUI, scripts) keep working
while new clients (React frontend) can use JWT. Both produce the
same AuthSession object so all routers are unchanged.
"""
from dataclasses import dataclass
from enum import Enum

from fastapi import Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

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


_bearer = HTTPBearer(auto_error=False)


def _resolve_key(key: str) -> UserRole | None:
    if key == settings.DOCTOR_KEY:       return UserRole.DOCTOR
    if key == settings.RECEPTIONIST_KEY: return UserRole.RECEPTIONIST
    if key == settings.PATIENT_KEY:      return UserRole.PATIENT
    return None


def _session_from_jwt(token: str) -> AuthSession:
    try:
        from app.core.auth import decode_access_token
        payload = decode_access_token(token)
        return AuthSession(
            user_id=int(payload["sub"]),
            role=UserRole(payload["role"]),
            patient_id=payload.get("patient_id"),
        )
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


async def resolve_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = _bearer,
) -> AuthSession:
    # Try JWT Bearer first
    if credentials is not None:
        return _session_from_jwt(credentials.credentials)

    # Fall back to legacy X-Staff-Key header
    key = request.headers.get("x-staff-key", "")
    role = _resolve_key(key)
    if role is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    patient_id = settings.DEMO_PATIENT_ID if role == UserRole.PATIENT else None
    return AuthSession(user_id=0, role=role, patient_id=patient_id)


def require_role(*allowed: UserRole):
    async def _check(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = _bearer,
    ) -> UserRole:
        session = await resolve_session(request, credentials)
        if session.role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required: {[r.value for r in allowed]}.",
            )
        return session.role
    return _check


def require_role_session(*allowed: UserRole):
    async def _check(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = _bearer,
    ) -> AuthSession:
        session = await resolve_session(request, credentials)
        if session.role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required: {[r.value for r in allowed]}.",
            )
        return session
    return _check


staff_only  = require_role(UserRole.DOCTOR, UserRole.RECEPTIONIST)
doctor_only = require_role(UserRole.DOCTOR)
any_role    = require_role(UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.PATIENT)
