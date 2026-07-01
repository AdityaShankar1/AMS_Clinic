"""
Business rules for booking appointments — the one place these two rules live,
per the Phase 0 design:

1. CUTOFF TIME: no new appointment (regular or urgent) may start after the
   clinic's last bookable time. This is a business policy, not a data
   integrity rule, so it lives here in application code, not the database —
   it's expected to change over time (e.g. different weekday cutoffs later).

2. OVERLAP: regular appointments may never overlap for the same doctor.
   Urgent-override appointments are the deliberate, explicit exception —
   the database's EXCLUDE constraint already encodes this distinction via
   its WHERE clause, but this service performs a pre-flight check too, so
   the user gets a clean error message instead of a raw database exception.
   The database constraint remains the actual source of truth under
   concurrent requests.
"""
from datetime import datetime, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.appointment import Appointment
from app.repositories import appointment_repository as appointment_repo
from app.repositories import patient_repository as patient_repo
from app.services.priority_service import score_priority


# Clinic policy, per Phase 0 design: opens effectively at 17:00, last
# bookable slot starts at 20:30. Weekdays only until weekend schedule is
# confirmed with the clinic (see "Open Decisions" in project guidelines).
LAST_BOOKABLE_START_TIME = time(20, 30)
CLINIC_OPEN_TIME = time(17, 0)


class BookingError(Exception):
    """Raised for any business-rule rejection (cutoff or overlap).
    Routers catch this and translate it into a clean HTTP 4xx response."""
    pass


async def book_appointment(
    db: AsyncSession,
    patient_id: int,
    doctor_id: int,
    scheduled_start: datetime,
    duration_minutes: int = 20,
    reason_for_visit: str | None = None,
    xray_needed: bool = False,
    blood_test_needed: bool = False,
    patient_priority_label: str = "auto",
    severity_level: int = 3,
    urgency_level: int = 3,
    treatment_phase: str = "one_time",
    is_urgent_override: bool = False,
    override_reason: str | None = None,
) -> Appointment:
    # Rule 1: cutoff time applies to EVERY booking, no exceptions —
    # including urgent overrides, per the explicit Phase 0 decision.
    if scheduled_start.time() > LAST_BOOKABLE_START_TIME:
        raise BookingError(
            f"Appointments cannot be booked to start after "
            f"{LAST_BOOKABLE_START_TIME.strftime('%I:%M %p')}."
        )

    if scheduled_start.time() < CLINIC_OPEN_TIME:
        raise BookingError(
            f"The clinic opens at {CLINIC_OPEN_TIME.strftime('%I:%M %p')}; "
            f"appointments cannot be booked before then."
        )

    # Rule 2: overlap check — skipped entirely for urgent overrides, since
    # those are explicitly allowed to coexist with an existing booking.
    if not is_urgent_override:
        overlap = await appointment_repo.check_overlap_exists(
            db, doctor_id, scheduled_start, duration_minutes
        )
        if overlap:
            raise BookingError(
                "This doctor already has an appointment at that time. "
                "If this is urgent, use the urgent-override option instead."
            )

    completed_visits = await patient_repo.get_previous_visit_count(db, patient_id)
    priority = score_priority(
        completed_visits=completed_visits,
        patient_priority_label=patient_priority_label,
        severity_level=severity_level,
        urgency_level=urgency_level,
        treatment_phase=treatment_phase,
        xray_needed=xray_needed,
        blood_test_needed=blood_test_needed,
        is_urgent_override=is_urgent_override,
    )

    # The database's EXCLUDE constraint is the final backstop — if a race
    # condition slips past the check above (two requests at the same
    # instant), Postgres itself will reject the insert. We catch that here
    # and translate it into the same clean BookingError, rather than
    # leaking a raw IntegrityError to the caller.
    try:
        appointment = await appointment_repo.create_appointment(
            db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_start=scheduled_start,
            duration_minutes=duration_minutes,
            reason_for_visit=reason_for_visit,
            xray_needed=xray_needed,
            blood_test_needed=blood_test_needed,
            patient_priority_label=priority.patient_priority_label,
            severity_level=priority.severity_level,
            urgency_level=priority.urgency_level,
            treatment_phase=priority.treatment_phase,
            priority_score=priority.priority_score,
            priority_band=priority.priority_band,
            priority_summary=priority.priority_summary,
            is_urgent_override=is_urgent_override,
            override_reason=override_reason,
        )
    except IntegrityError:
        await db.rollback()
        raise BookingError(
            "This doctor already has an appointment at that time. "
            "If this is urgent, use the urgent-override option instead."
        )

    return appointment
