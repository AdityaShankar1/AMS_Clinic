from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.session import engine
from app.core.logging import request_logging_middleware
from app.routers.auth import router as auth_router
from app.routers.patients import router as patients_router
from app.routers.doctors import router as doctors_router
from app.routers.appointments import router as appointments_router
from app.routers.visit_records import router as visit_records_router
from app.routers.gui import router as gui_router
from app.routers.analytics import router as analytics_router

app = FastAPI(title="Clinic AMS")

app.middleware("http")(request_logging_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ams-clinic-frontend-3br9e1ti9-aditya-shankars-projects-3311bc39.vercel.app",
        "https://ams-clinic.vercel.app",
        "https://ams-clinic-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "error", "db": str(exc)}


@app.get("/health/detailed")
async def health_detailed():
    import sys
    from datetime import datetime, timezone
    checks = {}
    try:
        async with engine.connect() as conn:
            version = await conn.scalar(text("SELECT version()"))
            migration = await conn.scalar(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            patient_count = await conn.scalar(text("SELECT COUNT(*) FROM patients"))
            appt_count = await conn.scalar(text("SELECT COUNT(*) FROM appointments"))
        checks["database"] = {
            "status": "ok",
            "postgres_version": version.split(",")[0] if version else None,
            "migration_head": migration,
            "patient_count": patient_count,
            "appointment_count": appt_count,
        }
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    return {
        "status": "ok" if checks["database"]["status"] == "ok" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "checks": checks,
    }


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(gui_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(appointments_router)
app.include_router(patients_router)
app.include_router(doctors_router)
app.include_router(visit_records_router)
