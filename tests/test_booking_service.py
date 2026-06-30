"""
Verifies the cutoff-time business rule in app/services/booking_service.py.

This is the one Phase 0 design rule that lives in application code rather
than the database (see booking_service.py's module docstring for why) — so
unlike the overlap constraint, there's no database-level guarantee backing
this up. It has to be correct in the Python logic itself, which is exactly
why it needs direct test coverage.
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.db.session import AsyncSessionLocal
from app.services import booking_service
from app.repositories import patient_repository as patient_repo


IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def test_doctor_and_patient(db_session):
    """Creates a throwaway doctor + patient for each test, cleans up after."""
    from sqlalchemy import text

    doctor_id = await db_session.scalar(
        text(
            "INSERT INTO doctors (full_name, specialty) "
            "VALUES ('Booking Test Doctor', 'ortho') RETURNING doctor_id"
        )
    )
    patient = await patient_repo.create_patient(
        db_session,
        full_name="Booking Test Patient",
        date_of_birth=datetime(1990, 1, 1).date(),
        sex="M",
        phone_number="9000000000",
    )
    await db_session.commit()

    yield doctor_id, patient.patient_id

    await db_session.execute(text("DELETE FROM appointments WHERE doctor_id = :id"), {"id": doctor_id})
    await db_session.execute(text("DELETE FROM doctors WHERE doctor_id = :id"), {"id": doctor_id})
    await db_session.execute(text("DELETE FROM patients WHERE patient_id = :id"), {"id": patient.patient_id})
    await db_session.commit()


async def test_booking_after_cutoff_is_rejected(db_session, test_doctor_and_patient):
    doctor_id, patient_id = test_doctor_and_patient
    too_late = datetime(2026, 7, 1, 20, 45, tzinfo=IST)  # 8:45 PM — past the 8:30 PM cutoff

    with pytest.raises(booking_service.BookingError, match="cannot be booked to start after"):
        await booking_service.book_appointment(
            db_session,
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_start=too_late,
        )


async def test_urgent_override_still_respects_cutoff(db_session, test_doctor_and_patient):
    """The one rule with NO exceptions, per the explicit Phase 0 decision —
    even an urgent override cannot bypass the cutoff time."""
    doctor_id, patient_id = test_doctor_and_patient
    too_late = datetime(2026, 7, 1, 21, 0, tzinfo=IST)  # 9:00 PM

    with pytest.raises(booking_service.BookingError, match="cannot be booked to start after"):
        await booking_service.book_appointment(
            db_session,
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_start=too_late,
            is_urgent_override=True,
            override_reason="VIP patient",
        )


async def test_booking_before_opening_is_rejected(db_session, test_doctor_and_patient):
    doctor_id, patient_id = test_doctor_and_patient
    too_early = datetime(2026, 7, 1, 16, 0, tzinfo=IST)  # 4:00 PM — clinic opens at 5:00 PM

    with pytest.raises(booking_service.BookingError, match="clinic opens at"):
        await booking_service.book_appointment(
            db_session,
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_start=too_early,
        )


async def test_booking_within_hours_succeeds(db_session, test_doctor_and_patient):
    doctor_id, patient_id = test_doctor_and_patient
    valid_time = datetime(2026, 7, 1, 18, 0, tzinfo=IST)  # 6:00 PM — well within hours

    appointment = await booking_service.book_appointment(
        db_session,
        patient_id=patient_id,
        doctor_id=doctor_id,
        scheduled_start=valid_time,
    )
    assert appointment.appointment_id is not None
    assert appointment.status == "scheduled"


async def test_urgent_override_bypasses_overlap_but_not_cutoff(db_session, test_doctor_and_patient):
    """Confirms the urgent-override exception applies ONLY to the overlap
    rule, exactly as designed — books two appointments at the same time
    for the same doctor, second one flagged urgent, and confirms both
    succeed without raising."""
    doctor_id, patient_id = test_doctor_and_patient
    same_time = datetime(2026, 7, 1, 19, 0, tzinfo=IST)

    first = await booking_service.book_appointment(
        db_session, patient_id=patient_id, doctor_id=doctor_id, scheduled_start=same_time,
    )
    second = await booking_service.book_appointment(
        db_session,
        patient_id=patient_id,
        doctor_id=doctor_id,
        scheduled_start=same_time,
        is_urgent_override=True,
        override_reason="Patient in acute pain, doctor agreed to fit in",
    )

    assert first.appointment_id != second.appointment_id
    assert second.is_urgent_override is True
