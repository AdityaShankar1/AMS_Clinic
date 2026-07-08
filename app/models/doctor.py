from sqlalchemy import String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Doctor(Base):
    __tablename__ = "doctors"
    __table_args__ = (
        Index("ix_doctors_full_name", "full_name"),
    )

    doctor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(String(50), nullable=False)
