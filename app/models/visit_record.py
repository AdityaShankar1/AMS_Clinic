from sqlalchemy import String, Integer, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from app.db.base import Base

class VisitRecord(Base):
    __tablename__ = "visit_records"

    visit_record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.appointment_id"), nullable=False, unique=True
    )
    diagnosis_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    treatment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
