"""
Importing all models here guarantees every table is registered on
Base.metadata as soon as anything imports `app.models` — regardless of
which specific model a given file actually uses directly.

This matters because SQLAlchemy resolves string-based ForeignKey
references (e.g. "doctors.doctor_id") lazily, only when a table is
needed during a flush/commit. If a model class was never imported
anywhere in the process, its table never gets registered, and any
other model's FK pointing at it fails with NoReferencedTableError —
even though the table genuinely exists in the database. Centralizing
imports here closes that gap permanently.
"""
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.visit_record import VisitRecord
