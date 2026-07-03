"""
Centralised model imports — guarantees every table is registered on
Base.metadata before any migration or query runs. See DAILY_LOG.md for
why this matters (lazy FK resolution bug, 2026-06-30).
"""
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.visit_record import VisitRecord
from app.models.user import User
