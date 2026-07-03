"""
Tests for JWT auth layer.
Verifies token creation, decoding, role resolution, and permission gates
entirely in-memory — no HTTP server, no DB needed for most cases.
"""
import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.core.config import settings
from app.core.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.core.security import UserRole, _resolve
from fastapi.security import HTTPAuthorizationCredentials


# ── Password hashing ──────────────────────────────────────────────────────

def test_password_hash_and_verify():
    hashed = hash_password("MySecret@123")
    assert verify_password("MySecret@123", hashed)
    assert not verify_password("wrong", hashed)


# ── Token creation and decoding ───────────────────────────────────────────

def test_token_contains_correct_claims():
    token = create_access_token(user_id=1, role="doctor", patient_id=None)
    payload = decode_access_token(token)
    assert payload["sub"] == "1"
    assert payload["role"] == "doctor"
    assert payload["patient_id"] is None


def test_patient_token_carries_patient_id():
    token = create_access_token(user_id=5, role="patient", patient_id=42)
    payload = decode_access_token(token)
    assert payload["patient_id"] == 42


def test_expired_token_raises():
    from jose import JWTError
    expired_payload = {
        "sub": "1",
        "role": "doctor",
        "patient_id": None,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm="HS256")
    with pytest.raises(JWTError):
        decode_access_token(expired_token)


def test_tampered_token_raises():
    from jose import JWTError
    token = create_access_token(user_id=1, role="doctor")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(JWTError):
        decode_access_token(tampered)


# ── Role resolution ───────────────────────────────────────────────────────

def _make_credentials(role: str, user_id: int = 1) -> HTTPAuthorizationCredentials:
    token = create_access_token(user_id=user_id, role=role)
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_resolve_doctor():
    session = _resolve(_make_credentials("doctor"))
    assert session.role == UserRole.DOCTOR
    assert session.user_id == 1


def test_resolve_receptionist():
    session = _resolve(_make_credentials("receptionist", user_id=2))
    assert session.role == UserRole.RECEPTIONIST


def test_resolve_patient():
    token = create_access_token(user_id=5, role="patient", patient_id=42)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    session = _resolve(creds)
    assert session.role == UserRole.PATIENT
    assert session.patient_id == 42


def test_missing_credentials_raises_401():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _resolve(None)
    assert exc.value.status_code == 401


def test_invalid_token_raises_401():
    from fastapi import HTTPException
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.token")
    with pytest.raises(HTTPException) as exc:
        _resolve(creds)
    assert exc.value.status_code == 401
