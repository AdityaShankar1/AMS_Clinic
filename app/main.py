from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import engine
from app.routers import auth, patients, doctors, appointments, visit_records, gui

app = FastAPI(title="Clinic AMS")


@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "error", "db": str(exc)}


# GUI router — serves the frontend SPA, public (auth happens inside the SPA)
app.include_router(gui.router)
app.include_router(auth.router)

# API routers — each endpoint declares its own role requirement via Depends()
app.include_router(appointments.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(visit_records.router)
