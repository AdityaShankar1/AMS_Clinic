"""
Seed Phase 2a user accounts. Run once after deployment.
Change passwords immediately via POST /auth/change-password.
"""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.auth import hash_password
from app.repositories import user_repository as user_repo
import app.models

engine = create_async_engine(settings.DATABASE_URL, connect_args={"statement_cache_size": 0})
Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

STAFF = [
    {"email": "rashmi@clinic.local",      "password": "Rashmi@1234",    "full_name": "Dr. Rashmi N",       "role": "doctor"},
    {"email": "shrinidhi@clinic.local",   "password": "Shrinidhi@1234", "full_name": "Dr. Shrinidhi M S",  "role": "doctor"},
    {"email": "receptionist@clinic.local","password": "Recep@1234",     "full_name": "Clinic Receptionist", "role": "receptionist"},
]

async def seed():
    async with Session() as db:
        for u in STAFF:
            existing = await user_repo.get_user_by_email(db, u["email"])
            if existing:
                print(f"  exists: {u['email']}")
                continue
            user = await user_repo.create_user(
                db, email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"], role=u["role"],
            )
            print(f"  created: {user.email} ({user.role})")
    await engine.dispose()

asyncio.run(seed())
print("Done — change default passwords via POST /auth/change-password")
