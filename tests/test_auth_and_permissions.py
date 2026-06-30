from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import AuthSession, UserRole, any_role, doctor_only, resolve_role, resolve_session, staff_only
from app.schemas.appointment import AppointmentCreate
from app.schemas.patient import PatientCreate
from app.schemas.visit_record import VisitRecordCreate
from app.routers.appointments import book_appointment, get_appointment, my_appointments
from app.routers.auth import who_am_i
from app.routers.patients import create_patient
from app.routers.visit_records import create_visit_record


class FakeDB:
    pass


def test_role_key_mapping_is_stable():
    assert resolve_role(settings.DOCTOR_KEY) == UserRole.DOCTOR
    assert resolve_role(settings.RECEPTIONIST_KEY) == UserRole.RECEPTIONIST
    assert resolve_role(settings.PATIENT_KEY) == UserRole.PATIENT
    assert resolve_role("not-a-real-key") is None


@pytest.mark.asyncio
async def test_auth_resolution_supports_all_roles():
    doctor = resolve_session(x_staff_key=settings.DOCTOR_KEY)
    receptionist = resolve_session(x_staff_key=settings.RECEPTIONIST_KEY)
    patient = resolve_session(x_staff_key=settings.PATIENT_KEY, x_patient_id=42)

    assert doctor == AuthSession(role=UserRole.DOCTOR, patient_id=None)
    assert receptionist == AuthSession(role=UserRole.RECEPTIONIST, patient_id=None)
    assert patient == AuthSession(role=UserRole.PATIENT, patient_id=42)

    assert await who_am_i(doctor) == doctor


def test_patient_auth_requires_patient_id():
    with pytest.raises(HTTPException) as exc:
        resolve_session(x_staff_key=settings.PATIENT_KEY)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_staff_and_patient_permissions(monkeypatch):
    fake_db = FakeDB()

    async def fake_create_patient(db, **payload):
        return {"patient_id": 1, **payload}

    async def fake_create_visit_record(db, **payload):
        return {"visit_record_id": 99, **payload}

    async def fake_list_appointments(db, **kwargs):
        return [{"appointment_id": 7, "patient_id": 42}]

    async def fake_get_appointment_by_id(db, appointment_id):
        return SimpleNamespace(appointment_id=appointment_id, patient_id=42, status="scheduled")

    monkeypatch.setattr("app.routers.patients.repo.create_patient", fake_create_patient)
    monkeypatch.setattr("app.routers.visit_records.repo.create_visit_record", fake_create_visit_record)
    monkeypatch.setattr("app.routers.appointments.repo.list_appointments", fake_list_appointments)
    monkeypatch.setattr("app.routers.appointments.repo.get_appointment_by_id", fake_get_appointment_by_id)

    receptionist_role = await staff_only(x_staff_key=settings.RECEPTIONIST_KEY)
    patient_role = await any_role(x_staff_key=settings.PATIENT_KEY)
    doctor_role = await doctor_only(x_staff_key=settings.DOCTOR_KEY)

    async def fake_book_appointment(db, **payload):
        return {"appointment_id": 11, **payload}

    monkeypatch.setattr(
        "app.routers.appointments.booking_service.book_appointment",
        fake_book_appointment,
    )

    booked = await book_appointment(
        payload=AppointmentCreate(
            patient_id=42,
            doctor_id=1,
            scheduled_start=datetime(2026, 7, 1, 18, 0),
        ),
        db=fake_db,
        _role=receptionist_role,
    )
    assert booked["appointment_id"] == 11

    created_patient = await create_patient(
        payload=PatientCreate(
            full_name="Test Patient",
            date_of_birth="1990-01-01",
            sex="M",
            phone_number="9999999999",
        ),
        db=fake_db,
        _role=receptionist_role,
    )
    assert created_patient["patient_id"] == 1

    created_visit = await create_visit_record(
        payload=VisitRecordCreate(
            appointment_id=7,
            visit_date="2026-07-01",
            treatment_status="completed",
        ),
        db=fake_db,
        _role=doctor_role,
    )
    assert created_visit["visit_record_id"] == 99

    my_appts = await my_appointments(
        x_patient_id=42,
        db=fake_db,
        _role=patient_role,
    )
    assert my_appts[0]["patient_id"] == 42

    own_appt = await get_appointment(
        appointment_id=7,
        x_patient_id=42,
        db=fake_db,
        role=patient_role,
    )
    assert own_appt.patient_id == 42

    with pytest.raises(HTTPException) as exc:
        await get_appointment(
            appointment_id=7,
            x_patient_id=99,
            db=fake_db,
            role=patient_role,
        )
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        await staff_only(x_staff_key=settings.PATIENT_KEY)
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        await doctor_only(x_staff_key=settings.RECEPTIONIST_KEY)
    assert exc.value.status_code == 403
