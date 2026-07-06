"""
Tests for Phase 1/2 hardcoded key auth (X-Staff-Key header).
JWT auth is deferred to a future phase — jose not yet installed.
"""
from app.core.security import resolve_role, UserRole
from app.core.config import settings


def test_doctor_key_resolves_correctly():
    assert resolve_role(settings.DOCTOR_KEY) == UserRole.DOCTOR


def test_receptionist_key_resolves_correctly():
    assert resolve_role(settings.RECEPTIONIST_KEY) == UserRole.RECEPTIONIST


def test_patient_key_resolves_correctly():
    assert resolve_role(settings.PATIENT_KEY) == UserRole.PATIENT


def test_invalid_key_returns_none():
    assert resolve_role("not-a-real-key") is None


def test_empty_key_returns_none():
    assert resolve_role("") is None


def test_all_roles_are_distinct():
    keys = [settings.DOCTOR_KEY, settings.RECEPTIONIST_KEY, settings.PATIENT_KEY]
    assert len(set(keys)) == 3  # no two roles share the same key
