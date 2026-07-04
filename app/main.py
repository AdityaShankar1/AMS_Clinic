from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.session import engine
from app.core.logging import request_logging_middleware
from app.routers import auth, patients, doctors, appointments, visit_records, gui

app = FastAPI(title="Clinic AMS")

app.middleware('http')(request_logging_middleware)

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


app.include_router(gui.router)
app.include_router(auth.router)
app.include_router(appointments.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(visit_records.router)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health/detailed")
async def health_detailed():
    """
    Extended health check — useful for ops dashboards and automated
    monitoring. Returns DB connectivity, migration state, and basic
    system info. In a production setup this would feed a Grafana
    dashboard or trigger PagerDuty alerts.
    """
    import sys
    from datetime import datetime, timezone
    checks = {}

    try:
        async with engine.connect() as conn:
            from sqlalchemy import text as _text
            version = await conn.scalar(_text("SELECT version()"))
            migration = await conn.scalar(
                _text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            patient_count = await conn.scalar(_text("SELECT COUNT(*) FROM patients"))
            appt_count = await conn.scalar(_text("SELECT COUNT(*) FROM appointments"))
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
