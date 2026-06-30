import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    STAFF_ACCESS_KEY: str = os.getenv("STAFF_ACCESS_KEY", "changeme")
    STAFF_ACCESS_KEY: str = os.getenv("STAFF_ACCESS_KEY", "changeme")

settings = Settings()
