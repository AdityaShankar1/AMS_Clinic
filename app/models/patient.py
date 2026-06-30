from sqlalchemy import String, Date, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date, datetime
from app.db.base import Base

class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(10), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    referred_by_patient_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
