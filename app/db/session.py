
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from dotenv import load_data



load_data = load_data()



DATABASE_URL = os.getenv("DATABASE_URL")



# Strip custom pool args because the external transaction pooler coordinates connections natively

engine = create_async_engine(

    DATABASE_URL,

    pool_pre_ping=True

)



SessionLocal = async_sessionmaker(

    bind=engine,

    class_=AsyncSession,

    expire_on_commit=False

)



async def get_db():

    async with SessionLocal() as session:

        try:

            yield session

        finally:

            await session.close()

