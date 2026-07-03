"""
Seed Phase 2 user accounts.
Run once: venv/bin/python seed_users.py
Passwords should be changed via POST /auth/change-password after first login.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.auth import hash_password
from app.repositories import user_repository as user_repo
import app.models  # registers all models

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"statement_cache_size": 0},
)
Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Adjust emails and passwords before running.
# Passwords here are defaults — change immediately via /auth/change-password.
STAFF_USERS = [
    {
        "email": "rashmi@clinic.local",
        "password": "Rashmi@1234",
        "full_name": "Dr. Rashmi N",
        "role": "doctor",
    },
    {
        "email": "shrinidhi@clinic.local",
        "password": "Shrinidhi@1234",
        "full_name": "Dr. Shrinidhi M S",
        "role": "doctor",
    },
    {
        "email": "receptionist@clinic.local",
        "password": "Recep@1234",
        "full_name": "Clinic Receptionist",
        "role": "receptionist",
    },
]


async def seed():
    async with Session() as db:
        for u in STAFF_USERS:
            existing = await user_repo.get_user_by_email(db, u["email"])
            if existing:
                print(f"  already exists: {u['email']} ({existing.role})")
                continue
            user = await user_repo.create_user(
                db,
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
            )
            print(f"  created: {user.email} ({user.role}) id={user.user_id}")
    await engine.dispose()


print("Seeding staff user accounts...")
asyncio.run(seed())
print("Done. Change default passwords immediately via POST /auth/change-password")
