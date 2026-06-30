import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Phase 1 role keys — three separate secrets, one per role.
    # In Phase 2 these are replaced by JWT-issued tokens with individual
    # user accounts; the role boundary stays the same.
    DOCTOR_KEY: str       = os.getenv("DOCTOR_KEY", "doctor-changeme")
    RECEPTIONIST_KEY: str = os.getenv("RECEPTIONIST_KEY", "recep-changeme")
    PATIENT_KEY: str      = os.getenv("PATIENT_KEY", "patient-changeme")


settings = Settings()
