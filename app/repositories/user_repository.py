from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    hashed_password: str,
    full_name: str,
    role: str,
    patient_id: int | None = None,
) -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
        patient_id=patient_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_password(
    db: AsyncSession, user_id: int, new_hashed_password: str
) -> User | None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None
    user.hashed_password = new_hashed_password
    await db.commit()
    await db.refresh(user)
    return user
