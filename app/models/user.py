from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Role stored directly on the user — matches UserRole enum values exactly.
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    # For patient-role users: links back to the patients table so we can
    # scope their API access to their own records without an extra lookup.
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patients.patient_id"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
