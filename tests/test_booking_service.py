from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services import booking_service


IST = timezone(timedelta(hours=5, minutes=30))


class FakeDB:
    def __init__(self):
        self.rolled_back = False

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_booking_after_cutoff_is_rejected(monkeypatch):
    async def fake_overlap(*args, **kwargs):
        return False

    monkeypatch.setattr(booking_service.appointment_repo, "check_overlap_exists", fake_overlap)

    with pytest.raises(booking_service.BookingError, match="cannot be booked to start after"):
        await booking_service.book_appointment(
            FakeDB(),
            patient_id=1,
            doctor_id=7,
            scheduled_start=datetime(2026, 7, 1, 20, 45, tzinfo=IST),
        )


@pytest.mark.asyncio
async def test_booking_before_opening_is_rejected(monkeypatch):
    async def fake_overlap(*args, **kwargs):
        return False

    monkeypatch.setattr(booking_service.appointment_repo, "check_overlap_exists", fake_overlap)

    with pytest.raises(booking_service.BookingError, match="clinic opens at"):
        await booking_service.book_appointment(
            FakeDB(),
            patient_id=1,
            doctor_id=7,
            scheduled_start=datetime(2026, 7, 1, 16, 0, tzinfo=IST),
        )


@pytest.mark.asyncio
async def test_booking_within_hours_succeeds(monkeypatch):
    created = {}

    async def fake_overlap(*args, **kwargs):
        return False

    async def fake_create_appointment(db, **payload):
        created.update(payload)
        return SimpleNamespace(appointment_id=101, **payload)

    monkeypatch.setattr(booking_service.appointment_repo, "check_overlap_exists", fake_overlap)
    monkeypatch.setattr(booking_service.appointment_repo, "create_appointment", fake_create_appointment)

    appointment = await booking_service.book_appointment(
        FakeDB(),
        patient_id=1,
        doctor_id=7,
        scheduled_start=datetime(2026, 7, 1, 18, 0, tzinfo=IST),
    )

    assert appointment.appointment_id == 101
    assert created["patient_id"] == 1
    assert created["doctor_id"] == 7


@pytest.mark.asyncio
async def test_overlap_is_rejected_for_regular_booking(monkeypatch):
    async def fake_overlap(*args, **kwargs):
        return True

    monkeypatch.setattr(booking_service.appointment_repo, "check_overlap_exists", fake_overlap)

    with pytest.raises(booking_service.BookingError, match="already has an appointment"):
        await booking_service.book_appointment(
            FakeDB(),
            patient_id=1,
            doctor_id=7,
            scheduled_start=datetime(2026, 7, 1, 18, 0, tzinfo=IST),
        )


@pytest.mark.asyncio
async def test_urgent_override_bypasses_overlap_but_not_cutoff(monkeypatch):
    created = {}

    async def fake_overlap(*args, **kwargs):
        return True

    async def fake_create_appointment(db, **payload):
        created.update(payload)
        return SimpleNamespace(appointment_id=202, **payload)

    monkeypatch.setattr(booking_service.appointment_repo, "check_overlap_exists", fake_overlap)
    monkeypatch.setattr(booking_service.appointment_repo, "create_appointment", fake_create_appointment)

    appointment = await booking_service.book_appointment(
        FakeDB(),
        patient_id=1,
        doctor_id=7,
        scheduled_start=datetime(2026, 7, 1, 19, 0, tzinfo=IST),
        is_urgent_override=True,
        override_reason="Emergency fit-in",
    )

    assert appointment.appointment_id == 202
    assert created["is_urgent_override"] is True
    assert created["override_reason"] == "Emergency fit-in"
