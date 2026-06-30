from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base

class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.doctor_id"), nullable=False)

    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="scheduled")
    reason_for_visit: Mapped[str | None] = mapped_column(String(255), nullable=True)

    xray_needed: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    blood_test_needed: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    is_urgent_override: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    override_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    rescheduled_to_appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.appointment_id"), nullable=True
    )
