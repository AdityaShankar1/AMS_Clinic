import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # JWT (Phase 2a+)
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-this-in-production-min-32-chars")
    ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "10"))

    # Legacy Phase 1 hardcoded keys — kept as fallback during transition
    DOCTOR_KEY: str       = os.getenv("DOCTOR_KEY", "doctor-changeme")
    RECEPTIONIST_KEY: str = os.getenv("RECEPTIONIST_KEY", "recep-changeme")
    PATIENT_KEY: str      = os.getenv("PATIENT_KEY", "patient-changeme")
    DEMO_PATIENT_ID: int  = int(os.getenv("DEMO_PATIENT_ID", "1"))


settings = Settings()
