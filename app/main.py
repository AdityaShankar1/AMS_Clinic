from fastapi import FastAPI, Depends
from sqlalchemy import text

from app.db.session import engine
from app.core.security import require_staff_key
from app.routers import patients, doctors, appointments, visit_records, gui

app = FastAPI(title="Clinic AMS")


@app.get("/health")
async def health_check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        result.scalar()
    return {"status": "ok", "db": "connected"}


# GUI router (public, handles own auth prompts via X-Staff-Key fetch calls)
app.include_router(gui.router)

# Everything below requires the staff key header (X-Staff-Key).
# This is the P1 baseline gate — real role-based auth lands in Phase 2.
app.include_router(patients.router, dependencies=[Depends(require_staff_key)])
app.include_router(doctors.router, dependencies=[Depends(require_staff_key)])
app.include_router(appointments.router, dependencies=[Depends(require_staff_key)])
app.include_router(visit_records.router, dependencies=[Depends(require_staff_key)])

