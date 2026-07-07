"""
Tests for Phase 2a JWT auth + legacy key fallback.
"""
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
import pytest

from app.core.config import settings
from app.core.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.core.security import UserRole, _resolve_key, _session_from_jwt
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
    expired_payload = {
        "sub": "1", "role": "doctor", "patient_id": None,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm="HS256")
    with pytest.raises(JWTError):
        decode_access_token(expired_token)


def test_tampered_token_raises():
    token = create_access_token(user_id=1, role="doctor")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(JWTError):
        decode_access_token(tampered)


# ── Legacy key resolution ─────────────────────────────────────────────────

def test_doctor_key_resolves():
    assert _resolve_key(settings.DOCTOR_KEY) == UserRole.DOCTOR


def test_receptionist_key_resolves():
    assert _resolve_key(settings.RECEPTIONIST_KEY) == UserRole.RECEPTIONIST


def test_patient_key_resolves():
    assert _resolve_key(settings.PATIENT_KEY) == UserRole.PATIENT


def test_invalid_key_returns_none():
    assert _resolve_key("not-a-real-key") is None


def test_all_role_keys_are_distinct():
    keys = [settings.DOCTOR_KEY, settings.RECEPTIONIST_KEY, settings.PATIENT_KEY]
    assert len(set(keys)) == 3


# ── JWT session resolution ────────────────────────────────────────────────

def test_jwt_session_resolves_doctor():
    token = create_access_token(user_id=1, role="doctor")
    session = _session_from_jwt(token)
    assert session.role == UserRole.DOCTOR
    assert session.user_id == 1


def test_jwt_session_resolves_patient_with_id():
    token = create_access_token(user_id=5, role="patient", patient_id=42)
    session = _session_from_jwt(token)
    assert session.role == UserRole.PATIENT
    assert session.patient_id == 42


def test_jwt_session_rejects_invalid_token():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _session_from_jwt("not.a.token")
    assert exc.value.status_code == 401
