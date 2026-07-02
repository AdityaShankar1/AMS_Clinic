"""Seed demo patients and appointments for a realistic clinic dashboard.

Run this after the schema migration so the UI lands on non-empty data.
The script is idempotent: re-running it updates the same named demo rows
instead of creating duplicates.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, date, time, timedelta, timezone

import asyncpg
from dotenv import load_dotenv

from app.services.priority_service import score_priority


IST = timezone(timedelta(hours=5, minutes=30))

DOCTORS = [
    {"full_name": "Dr. Shrinidhi M S", "specialty": "Periodontics"},
    {"full_name": "Dr. Rashmi N", "specialty": "Orthodontics"},
]

PATIENTS = [
    {"full_name": "Dev Shah", "date_of_birth": date(1987, 11, 20), "sex": "Male", "phone_number": "9000000001", "email": "dev.shah@example.com"},
    {"full_name": "Ananya Iyer", "date_of_birth": date(1998, 4, 12), "sex": "Female", "phone_number": "9000000002", "email": "ananya.iyer@example.com"},
    {"full_name": "Farah Ahmed", "date_of_birth": date(1995, 9, 5), "sex": "Female", "phone_number": "9000000003", "email": "farah.ahmed@example.com"},
    {"full_name": "Kunal Patil", "date_of_birth": date(1978, 2, 18), "sex": "Male", "phone_number": "9000000004", "email": "kunal.patil@example.com"},
    {"full_name": "Riya Menon", "date_of_birth": date(2001, 6, 30), "sex": "Female", "phone_number": "9000000005", "email": "riya.menon@example.com"},
    {"full_name": "Joseph Thomas", "date_of_birth": date(1969, 12, 1), "sex": "Male", "phone_number": "9000000006", "email": "joseph.thomas@example.com"},
]


def normalize_dsn(raw_dsn: str) -> str:
    if raw_dsn.startswith("postgresql+asyncpg://"):
        return raw_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw_dsn


def dt(day_offset: int, hour: int, minute: int = 0) -> datetime:
    base = datetime(2026, 7, 1, hour=hour, minute=minute, tzinfo=IST)
    return base + timedelta(days=day_offset)


async def get_or_create_doctor(conn: asyncpg.Connection, full_name: str, specialty: str) -> int:
    existing = await conn.fetchrow("SELECT doctor_id FROM doctors WHERE full_name = $1", full_name)
    if existing:
        await conn.execute(
            "UPDATE doctors SET specialty = $2 WHERE doctor_id = $1",
            existing["doctor_id"],
            specialty,
        )
        return existing["doctor_id"]

    return await conn.fetchval(
        "INSERT INTO doctors (full_name, specialty) VALUES ($1, $2) RETURNING doctor_id",
        full_name,
        specialty,
    )


async def get_or_create_patient(conn: asyncpg.Connection, patient: dict) -> int:
    existing = await conn.fetchrow("SELECT patient_id FROM patients WHERE full_name = $1", patient["full_name"])
    if existing:
        await conn.execute(
            """
            UPDATE patients
            SET date_of_birth = $2,
                sex = $3,
                phone_number = $4,
                email = $5,
                consent_given = true
            WHERE patient_id = $1
            """,
            existing["patient_id"],
            patient["date_of_birth"],
            patient["sex"],
            patient["phone_number"],
            patient["email"],
        )
        return existing["patient_id"]

    return await conn.fetchval(
        """
        INSERT INTO patients (full_name, date_of_birth, sex, phone_number, email, consent_given)
        VALUES ($1, $2, $3, $4, $5, true)
        RETURNING patient_id
        """,
        patient["full_name"],
        patient["date_of_birth"],
        patient["sex"],
        patient["phone_number"],
        patient["email"],
    )


async def completed_visit_count(conn: asyncpg.Connection, patient_id: int) -> int:
    return await conn.fetchval(
        "SELECT COUNT(*) FROM appointments WHERE patient_id = $1 AND status = 'completed'",
        patient_id,
    )


async def upsert_visit_record(
    conn: asyncpg.Connection,
    appointment_id: int,
    visit_date: date,
    diagnosis_notes: str,
) -> None:
    existing = await conn.fetchrow(
        "SELECT visit_record_id FROM visit_records WHERE appointment_id = $1",
        appointment_id,
    )
    if existing:
        await conn.execute(
            """
            UPDATE visit_records
            SET visit_date = $2,
                diagnosis_notes = $3,
                treatment_status = 'completed'
            WHERE visit_record_id = $1
            """,
            existing["visit_record_id"],
            visit_date,
            diagnosis_notes,
        )
        return

    await conn.execute(
        """
        INSERT INTO visit_records (appointment_id, visit_date, diagnosis_notes, treatment_status)
        VALUES ($1, $2, $3, 'completed')
        """,
        appointment_id,
        visit_date,
        diagnosis_notes,
    )


async def upsert_appointment(
    conn: asyncpg.Connection,
    *,
    patient_id: int,
    doctor_id: int,
    scheduled_start: datetime,
    duration_minutes: int,
    reason_for_visit: str,
    xray_needed: bool,
    blood_test_needed: bool,
    patient_priority_label: str,
    severity_level: int,
    urgency_level: int,
    treatment_phase: str,
    status: str,
    is_urgent_override: bool = False,
    override_reason: str | None = None,
) -> int:
    existing = await conn.fetchrow(
        """
        SELECT appointment_id
        FROM appointments
        WHERE patient_id = $1 AND doctor_id = $2 AND scheduled_start = $3
        """,
        patient_id,
        doctor_id,
        scheduled_start,
    )

    visit_count = await completed_visit_count(conn, patient_id)
    priority = score_priority(
        completed_visits=visit_count,
        patient_priority_label=patient_priority_label,
        severity_level=severity_level,
        urgency_level=urgency_level,
        treatment_phase=treatment_phase,
        xray_needed=xray_needed,
        blood_test_needed=blood_test_needed,
        is_urgent_override=is_urgent_override,
    )

    params = (
        patient_id,
        doctor_id,
        scheduled_start,
        duration_minutes,
        reason_for_visit,
        xray_needed,
        blood_test_needed,
        priority.patient_priority_label,
        priority.severity_level,
        priority.urgency_level,
        priority.treatment_phase,
        priority.priority_score,
        priority.priority_band,
        priority.priority_summary,
        is_urgent_override,
        override_reason,
        status,
    )

    if existing:
        appointment_id = existing["appointment_id"]
        await conn.execute(
            """
            UPDATE appointments
            SET patient_id = $2,
                doctor_id = $3,
                scheduled_start = $4,
                duration_minutes = $5,
                reason_for_visit = $6,
                xray_needed = $7,
                blood_test_needed = $8,
                patient_priority_label = $9,
                severity_level = $10,
                urgency_level = $11,
                treatment_phase = $12,
                priority_score = $13,
                priority_band = $14,
                priority_summary = $15,
                is_urgent_override = $16,
                override_reason = $17,
                status = $18
            WHERE appointment_id = $1
            """,
            appointment_id,
            *params,
        )
    else:
        appointment_id = await conn.fetchval(
            """
            INSERT INTO appointments (
                patient_id, doctor_id, scheduled_start, duration_minutes,
                reason_for_visit, xray_needed, blood_test_needed,
                patient_priority_label, severity_level, urgency_level, treatment_phase,
                priority_score, priority_band, priority_summary,
                is_urgent_override, override_reason, status
            ) VALUES (
                $1, $2, $3, $4,
                $5, $6, $7,
                $8, $9, $10, $11,
                $12, $13, $14,
                $15, $16, $17
            )
            RETURNING appointment_id
            """,
            *params,
        )

    if status == "completed":
        await upsert_visit_record(
            conn,
            appointment_id,
            scheduled_start.date(),
            reason_for_visit or "Completed treatment note",
        )

    return appointment_id


async def main() -> None:
    load_dotenv()
    raw_dsn = os.getenv("DATABASE_URL")
    if not raw_dsn:
        raise SystemExit("DATABASE_URL is missing. Add it to .env before seeding.")

    conn = await asyncpg.connect(normalize_dsn(raw_dsn))
    try:
        doctor_ids: dict[str, int] = {}
        for doctor in DOCTORS:
            doctor_ids[doctor["full_name"]] = await get_or_create_doctor(
                conn,
                doctor["full_name"],
                doctor["specialty"],
            )

        patient_ids: dict[str, int] = {}
        for patient in PATIENTS:
            patient_ids[patient["full_name"]] = await get_or_create_patient(conn, patient)

        dr_periodontics = doctor_ids["Dr. Shrinidhi M S"]
        dr_orthodontics = doctor_ids["Dr. Rashmi N"]

        demo_schedule = [
            # Historical completed appointments so the "regular patient" logic has data.
            {
                "patient": "Dev Shah",
                "doctor_id": dr_periodontics,
                "scheduled_start": dt(-90, 18, 0),
                "duration_minutes": 30,
                "reason_for_visit": "Periodontal maintenance and review",
                "xray_needed": False,
                "blood_test_needed": False,
                "patient_priority_label": "established",
                "severity_level": 2,
                "urgency_level": 2,
                "treatment_phase": "phased",
                "status": "completed",
            },
            {
                "patient": "Dev Shah",
                "doctor_id": dr_periodontics,
                "scheduled_start": dt(-60, 18, 30),
                "duration_minutes": 30,
                "reason_for_visit": "Gum inflammation follow-up",
                "xray_needed": False,
                "blood_test_needed": False,
                "patient_priority_label": "established",
                "severity_level": 2,
                "urgency_level": 3,
                "treatment_phase": "phased",
                "status": "completed",
            },
            {
                "patient": "Dev Shah",
                "doctor_id": dr_periodontics,
                "scheduled_start": dt(-30, 19, 0),
                "duration_minutes": 30,
                "reason_for_visit": "Regular periodontal review",
                "xray_needed": False,
                "blood_test_needed": False,
                "patient_priority_label": "established",
                "severity_level": 1,
                "urgency_level": 2,
                "treatment_phase": "phased",
                "status": "completed",
            },
            # Upcoming appointments used by the receptionist/doctor dashboard.
            {
                "patient": "Ananya Iyer",
                "doctor_id": dr_orthodontics,
                "scheduled_start": dt(2, 17, 30),
                "duration_minutes": 30,
                "reason_for_visit": "Severe pain and swelling, needs same-week attention",
                "xray_needed": True,
                "blood_test_needed": True,
                "patient_priority_label": "auto",
                "severity_level": 5,
                "urgency_level": 5,
                "treatment_phase": "phased",
                "status": "scheduled",
            },
            {
                "patient": "Farah Ahmed",
                "doctor_id": dr_periodontics,
                "scheduled_start": dt(2, 18, 30),
                "duration_minutes": 20,
                "reason_for_visit": "Tooth filling consultation",
                "xray_needed": True,
                "blood_test_needed": False,
                "patient_priority_label": "new",
                "severity_level": 4,
                "urgency_level": 4,
                "treatment_phase": "one_time",
                "status": "scheduled",
            },
            {
                "patient": "Kunal Patil",
                "doctor_id": dr_periodontics,
                "scheduled_start": dt(3, 17, 45),
                "duration_minutes": 30,
                "reason_for_visit": "Phase 2 implant follow-up",
                "xray_needed": False,
                "blood_test_needed": True,
                "patient_priority_label": "established",
                "severity_level": 3,
                "urgency_level": 4,
                "treatment_phase": "phased",
                "status": "scheduled",
            },
            {
                "patient": "Riya Menon",
                "doctor_id": dr_orthodontics,
                "scheduled_start": dt(4, 18, 0),
                "duration_minutes": 20,
                "reason_for_visit": "Regular aligner review",
                "xray_needed": False,
                "blood_test_needed": False,
                "patient_priority_label": "auto",
                "severity_level": 2,
                "urgency_level": 3,
                "treatment_phase": "phased",
                "status": "scheduled",
            },
            {
                "patient": "Joseph Thomas",
                "doctor_id": dr_orthodontics,
                "scheduled_start": dt(4, 19, 0),
                "duration_minutes": 20,
                "reason_for_visit": "Routine cleaning and polishing",
                "xray_needed": False,
                "blood_test_needed": False,
                "patient_priority_label": "auto",
                "severity_level": 1,
                "urgency_level": 2,
                "treatment_phase": "one_time",
                "status": "scheduled",
            },
            {
                "patient": "Dev Shah",
                "doctor_id": dr_periodontics,
                "scheduled_start": dt(5, 18, 15),
                "duration_minutes": 30,
                "reason_for_visit": "Established recall visit",
                "xray_needed": False,
                "blood_test_needed": False,
                "patient_priority_label": "auto",
                "severity_level": 2,
                "urgency_level": 2,
                "treatment_phase": "phased",
                "status": "scheduled",
            },
        ]

        for item in demo_schedule:
            await upsert_appointment(
                conn,
                patient_id=patient_ids[item["patient"]],
                doctor_id=item["doctor_id"],
                scheduled_start=item["scheduled_start"],
                duration_minutes=item["duration_minutes"],
                reason_for_visit=item["reason_for_visit"],
                xray_needed=item["xray_needed"],
                blood_test_needed=item["blood_test_needed"],
                patient_priority_label=item["patient_priority_label"],
                severity_level=item["severity_level"],
                urgency_level=item["urgency_level"],
                treatment_phase=item["treatment_phase"],
                status=item["status"],
            )

        print("Seeded demo patients:")
        for name, patient_id in patient_ids.items():
            print(f"  {patient_id}: {name}")

        print("\nSeeded demo appointments and visit records.")
        print(f"Recommended demo patient id for login: {patient_ids['Dev Shah']}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
