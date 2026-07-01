#!/usr/bin/env python3
"""
Clinic AMS — Diagnostic Script
Run: venv/bin/python scripts/diagnose.py
Tells you exactly what's working, what isn't, and likely why.
Share the output with Claude or a reviewer instead of screenshots.
"""
import asyncio
import os
import sys
import importlib
import subprocess
from datetime import datetime

# ── ANSI colours ─────────────────────────────────────────────────────────────
GRN = "\033[92m"; RED = "\033[91m"; YLW = "\033[93m"; BLU = "\033[94m"; RST = "\033[0m"; BLD = "\033[1m"
OK  = f"{GRN}✓{RST}"; FAIL = f"{RED}✗{RST}"; WARN = f"{YLW}⚠{RST}"

issues: list[str] = []

def ok(msg):   print(f"  {OK}  {msg}")
def fail(msg): print(f"  {FAIL}  {RED}{msg}{RST}"); issues.append(msg)
def warn(msg): print(f"  {WARN}  {YLW}{msg}{RST}")
def section(title): print(f"\n{BLD}{BLU}{'─'*55}{RST}\n{BLD} {title}{RST}\n{'─'*55}")

# ── 1. Environment ─────────────────────────────────────────────────────────
section("1 · Environment")
in_venv = sys.prefix != sys.base_prefix
ok(f"Python {sys.version.split()[0]} — venv {'active' if in_venv else 'NOT ACTIVE'}") if in_venv else fail(f"Python {sys.version.split()[0]} — venv NOT active (run: source venv/bin/activate)")

from dotenv import load_dotenv
load_dotenv()
for var in ["DATABASE_URL", "DOCTOR_KEY", "RECEPTIONIST_KEY", "PATIENT_KEY"]:
    val = os.getenv(var)
    if val:
        display = val[:20] + "..." if len(val) > 20 else val
        ok(f"{var} = {display}")
    else:
        fail(f"{var} missing from .env")

demo_id = os.getenv("DEMO_PATIENT_ID", "NOT SET")
warn(f"DEMO_PATIENT_ID = {demo_id} (should be a real patient_id from your DB)")

# ── 2. Core imports ────────────────────────────────────────────────────────
section("2 · Core imports")
modules = {
    "FastAPI":           "fastapi",
    "SQLAlchemy":        "sqlalchemy",
    "asyncpg":           "asyncpg",
    "Alembic":           "alembic",
    "Pydantic":          "pydantic",
    "python-dotenv":     "dotenv",
    "greenlet":          "greenlet",
    "pytest-asyncio":    "pytest_asyncio",
}
for name, mod in modules.items():
    try:
        m = importlib.import_module(mod)
        ver = getattr(m, "__version__", "?")
        ok(f"{name} {ver}")
    except ImportError as e:
        fail(f"{name} not installed: {e}")

# ── 3. App module imports ──────────────────────────────────────────────────
section("3 · App module imports")
app_modules = [
    "app.core.config",
    "app.core.security",
    "app.db.base",
    "app.db.session",
    "app.models",
    "app.models.patient",
    "app.models.doctor",
    "app.models.appointment",
    "app.models.visit_record",
    "app.repositories.patient_repository",
    "app.repositories.appointment_repository",
    "app.repositories.visit_record_repository",
    "app.services.booking_service",
    "app.services.priority_service",
    "app.routers.patients",
    "app.routers.appointments",
    "app.routers.doctors",
    "app.routers.visit_records",
    "app.main",
]
for mod in app_modules:
    try:
        importlib.import_module(mod)
        ok(mod)
    except Exception as e:
        fail(f"{mod}: {e}")

# ── 4. Database connectivity ───────────────────────────────────────────────
section("4 · Database connectivity")

async def check_db():
    import asyncpg
    raw_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(raw_url, timeout=8)
        ver = await conn.fetchval("SELECT version()")
        ok(f"Connected: {ver[:60]}")

        # Check all expected tables exist
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        existing = {r["tablename"] for r in tables}
        for t in ["patients", "doctors", "appointments", "visit_records", "alembic_version"]:
            if t in existing:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {t}")
                ok(f"Table '{t}' exists ({count} rows)")
            else:
                fail(f"Table '{t}' missing — run: alembic upgrade head")

        # Check constraint
        constraint = await conn.fetchval(
            "SELECT conname FROM pg_constraint WHERE conname='no_overlap_for_regular_bookings'"
        )
        if constraint:
            ok("Exclusion constraint 'no_overlap_for_regular_bookings' present")
        else:
            fail("Exclusion constraint missing — re-apply the gist migration manually")

        # Check btree_gist
        ext = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname='btree_gist'")
        ok("btree_gist extension installed") if ext else fail("btree_gist missing")

        # Check trigger
        trigger = await conn.fetchval(
            "SELECT trigger_name FROM information_schema.triggers WHERE trigger_name='trg_set_scheduled_end'"
        )
        ok("Trigger 'trg_set_scheduled_end' present") if trigger else fail("Trigger missing — re-apply scheduled_end migration")

        # Check migration head
        current = await conn.fetchval("SELECT version_num FROM alembic_version")
        ok(f"Alembic current head: {current}")

        # Check doctors seeded
        doctors = await conn.fetch("SELECT full_name, specialty FROM doctors ORDER BY full_name")
        if doctors:
            for d in doctors:
                ok(f"Doctor seeded: {d['full_name']} ({d['specialty']})")
        else:
            warn("No doctors seeded — run: python3 seed_doctors.py")

        await conn.close()
    except Exception as e:
        fail(f"DB connection failed: {e}")
        if "could not translate host" in str(e) or "timeout" in str(e).lower():
            warn("Likely cause: IPv6-only direct connection failing on this network — try the pooler URL (port 6543)")

asyncio.run(check_db())

# ── 5. Auth layer ──────────────────────────────────────────────────────────
section("5 · Auth / security layer")
try:
    from app.core.security import resolve_role, UserRole
    from app.core.config import settings

    pairs = [
        (settings.DOCTOR_KEY, UserRole.DOCTOR),
        (settings.RECEPTIONIST_KEY, UserRole.RECEPTIONIST),
        (settings.PATIENT_KEY, UserRole.PATIENT),
    ]
    for key, expected in pairs:
        resolved = resolve_role(key)
        if resolved == expected:
            ok(f"{expected.value} key resolves correctly")
        else:
            fail(f"{expected.value} key resolves to {resolved} (expected {expected})")

    bad = resolve_role("definitely-wrong-key")
    ok("Invalid key correctly returns None") if bad is None else fail("Invalid key should return None")
except Exception as e:
    fail(f"Auth check failed: {e}")

# ── 6. Booking service rules ───────────────────────────────────────────────
section("6 · Booking service business rules (unit check)")
try:
    from app.services.booking_service import CLINIC_OPEN_TIME, LAST_BOOKABLE_START_TIME, BookingError
    from datetime import time
    ok(f"Clinic opens at: {CLINIC_OPEN_TIME.strftime('%H:%M')} (expected 17:00)")  if CLINIC_OPEN_TIME == time(17,0) else warn(f"Clinic open time is {CLINIC_OPEN_TIME} — expected 17:00")
    ok(f"Last bookable slot: {LAST_BOOKABLE_START_TIME.strftime('%H:%M')} (expected 20:30)") if LAST_BOOKABLE_START_TIME == time(20,30) else warn(f"Cutoff is {LAST_BOOKABLE_START_TIME} — expected 20:30")
    ok("BookingError importable")
except Exception as e:
    fail(f"booking_service check failed: {e}")

# ── 7. Priority service ────────────────────────────────────────────────────
section("7 · Priority service (unit check)")
try:
    from app.services.priority_service import score_priority
    r = score_priority(completed_visits=0, severity_level=5, urgency_level=5, is_urgent_override=True, treatment_phase="phased")
    ok(f"score_priority works — new critical case scores {r.priority_score} band={r.priority_band}")
    r2 = score_priority(completed_visits=10, severity_level=1, urgency_level=1)
    ok(f"Established routine patient scores {r2.priority_score} band={r2.priority_band}")
except Exception as e:
    fail(f"priority_service check failed: {e}")

# ── 8. Pytest suite ────────────────────────────────────────────────────────
section("8 · Test suite")
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"],
    capture_output=True, text=True
)
for line in result.stdout.splitlines():
    if "PASSED" in line:   print(f"  {OK}  {line.strip()}")
    elif "FAILED" in line: print(f"  {FAIL}  {RED}{line.strip()}{RST}"); issues.append(line.strip())
    elif "ERROR"  in line: print(f"  {FAIL}  {RED}{line.strip()}{RST}"); issues.append(line.strip())
    elif "passed" in line or "failed" in line: print(f"  → {line.strip()}")

# ── 9. HTTP smoke tests ────────────────────────────────────────────────────
section("9 · HTTP smoke tests (server must be running on port 8001)")
try:
    import urllib.request, urllib.error, json as _json
    port = 8001
    doctor_key = os.getenv("DOCTOR_KEY", "")
    recep_key  = os.getenv("RECEPTIONIST_KEY", "")
    patient_key = os.getenv("PATIENT_KEY", "")

    def http_get(path, headers=None):
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=4) as r:
                return r.status, _json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, {}
        except Exception as e:
            return None, str(e)

    # Health
    status, body = http_get("/health")
    if status == 200 and body.get("db") == "connected":
        ok(f"GET /health → 200, db=connected")
    else:
        fail(f"GET /health → {status} {body} (is uvicorn running on port {port}?)")

    # Auth/me for each role
    for role_name, key in [("doctor", doctor_key), ("receptionist", recep_key), ("patient", patient_key)]:
        status, body = http_get("/auth/me", {"X-Staff-Key": key})
        if status == 200 and body.get("role") == role_name:
            ok(f"GET /auth/me with {role_name} key → role={body.get('role')}")
        else:
            fail(f"GET /auth/me with {role_name} key → {status} {body}")

    # Gate check — no key should 401
    status, _ = http_get("/patients")
    ok("No key → 401 (gate works)") if status == 401 else fail(f"No key → {status} (expected 401 — gate not working)")

    # Doctors list
    status, body = http_get("/doctors", {"X-Staff-Key": doctor_key})
    if status == 200 and isinstance(body, list):
        ok(f"GET /doctors → {len(body)} doctor(s) returned")
        for d in body: ok(f"  · {d.get('full_name')} ({d.get('specialty')})")
    else:
        fail(f"GET /doctors → {status} {body}")

    # Patients list
    status, body = http_get("/patients", {"X-Staff-Key": doctor_key})
    if status == 200:
        ok(f"GET /patients → {len(body)} patient(s)")
    else:
        fail(f"GET /patients → {status}")

    # Appointments list
    status, body = http_get("/appointments", {"X-Staff-Key": doctor_key})
    if status == 200:
        ok(f"GET /appointments → {len(body)} appointment(s)")
    else:
        fail(f"GET /appointments → {status}")

except Exception as e:
    fail(f"HTTP smoke tests failed: {e}")

# ── Summary ────────────────────────────────────────────────────────────────
section("Summary")
if not issues:
    print(f"\n  {GRN}{BLD}All checks passed. Phase 1 is healthy.{RST}\n")
else:
    print(f"\n  {RED}{BLD}{len(issues)} issue(s) found:{RST}")
    for i, issue in enumerate(issues, 1):
        print(f"  {RED}{i}. {issue}{RST}")
    print()

print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
