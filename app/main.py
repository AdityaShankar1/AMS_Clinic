from fastapi import FastAPI
from sqlalchemy import text
from app.db.session import engine

app = FastAPI(title="Clinic AMS")

@app.get("/health")
async def health_check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        result.scalar()
    return {"status": "ok", "db": "connected"}
