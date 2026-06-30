# Daily Build Log — Clinic AMS

*Purpose: track what was built, what broke, and how it was fixed — day by day. This log plus the Git commit history together give a complete, traceable picture of how this project was actually built, useful both for debugging (was this a local environment issue or a logic bug?) and for demonstrating consistent, disciplined progress over time.*

---

## 2026-06-29 — Phase 0: Planning & System Design

**Built:**
- Defined the problem space: digitizing a real dental clinic (2 dentists — ortho + perio — and 1 receptionist) currently running entirely on a paper diary.
- Identified core pain points to solve: no-shows, lack of urgency/priority handling, and concurrent-booking collisions (two people trying to book the same slot at once).
- Scoped functional and non-functional requirements for an MVP, explicitly deciding against unnecessary complexity (no multi-region, no microservices, no horizontal scaling — single-clinic scale doesn't need it).
- Designed the full database schema: `patients`, `doctors`, `appointments`, `visit_records`, with `invoices`/`payments` included in the schema but deliberately left dormant until a later phase.
- Worked through key data-modeling decisions: storing `date_of_birth` instead of a static age field; deriving `num_of_prev_visits` from appointment history instead of storing a running count; using soft-deletes/status changes instead of hard deletes for any medical or financial record.
- Designed the double-booking prevention mechanism: a Postgres `EXCLUDE USING gist` constraint that prevents overlapping appointments for the same doctor, with a deliberate carve-out for staff-flagged "urgent override" bookings that are allowed to bypass it.
- Separated the appointment cutoff-time rule (hard 8:00–8:30 PM limit, no exceptions) from the overlap rule — cutoff lives in application code as business policy; overlap prevention lives in the database as a data-integrity guarantee.
- Decided on a layered architecture (routers → services → repositories → database) — lightweight SOLID/GRASP alignment without over-engineering for a solo project at this scale.
- Evaluated and selected the tech stack: FastAPI (over Django/Flask, based on a fit-vs-ease tradeoff analysis) + PostgreSQL via Supabase (confirmed `btree_gist` and `pgvector` support, needed for the overlap constraint and future RAG work respectively) + React/Tailwind frontend (deferred to Phase 2) + AWS EC2 for deployment.
- Defined the 4-phase roadmap (P1: barebones MVP, P2: auth + security + polish + real frontend, P3: ML/NLP + caching + compliance, P4: CI/CD + final deployment), with the explicit requirement that every phase boundary (P1→P4, P1→P2→P4, P1→P2→P3→P4) must be a valid, demoable stopping point.

**Issues faced:** None — this was a planning-only day, no code written yet.

**Resolution:** N/A

**Status:** Phase 0 complete. Schema, architecture, and stack locked. Ready to start implementation.

---

## 2026-06-30 — Phase 1: Project Scaffolding & Database Connection

**Built:**
- Scaffolded the full project structure (`app/core`, `app/db`, `app/models`, `app/schemas`, `app/routers`, `app/services`, `app/repositories`, `app/templates`, `alembic/`, `tests/`) following the layered architecture decided in Phase 0.
- Initialized Git repository, connected to GitHub remote (`AdityaShankar1/AMS_Clinic`).
- Set up Python virtual environment (Python 3.14.0) and installed core dependencies: FastAPI, SQLAlchemy (async), asyncpg, Alembic, python-dotenv.
- Created a Supabase project (Postgres, region ap-south-1/Mumbai, standard Postgres engine — not the alpha OrioleDB option) for managed database hosting. Left automatic Row Level Security disabled, since access control is handled at the FastAPI service layer, not via Supabase's per-row policies — this architecture never lets a frontend talk to the DB directly.
- Verified raw DB connectivity with a standalone `asyncpg.connect()` test script before involving the app or Alembic, to isolate connection issues from application-level issues.
- Wrote `app/core/config.py` (settings loader), `app/db/session.py` (async engine + session factory), `app/db/base.py` (SQLAlchemy declarative base).
- Wrote the first model, `Patient` (`app/models/patient.py`) — chosen first because it has no foreign keys, making it the simplest possible test of the full migration pipeline.
- Wrote `app/main.py` with a `/health` endpoint to verify FastAPI can reach Supabase independently of Alembic.
- Initialized Alembic with the async template (`alembic init -t async alembic`).
- Patched `alembic/env.py` to read the database URL from `app.core.config.settings` (rather than a hardcoded value in `alembic.ini`) and to point `target_metadata` at `Base.metadata`, so `--autogenerate` could detect the `Patient` model.
- Generated and applied the first migration (`create patients table`) — confirmed the `patients` table now exists live in the Supabase table editor.

**Issues faced:**
1. A pasted multi-line `touch` command failed with "No such file or directory" because the preceding `mkdir -p` step hadn't actually executed in the same paste block — the directories the `touch` commands targeted didn't exist yet.
2. `alembic init -t async alembic` failed with "Directory alembic already exists and is not empty" — leftover from an earlier manual `mkdir -p alembic/versions` scaffold step that pre-created the folder Alembic needs to generate fresh.
3. `alembic revision --autogenerate` failed with `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:driver` — caused by `alembic.ini`'s placeholder connection string (`driver://user:pass@localhost/dbname`) never being overridden with the real Supabase URL.
4. Open question (not yet hit, flagged proactively): Supabase's direct connection (port 5432) can be IPv6-only on the free tier, which fails to resolve on some networks. Connection succeeded in this case, but the pooler connection (port 6543) is noted as the fallback if this resurfaces.

**Resolution:**
1. Restructured the command into a single chained paste (`mkdir -p ... && touch ...`) so directory creation is guaranteed to complete before file creation is attempted.
2. Deleted the pre-existing empty `alembic/` directory (`rm -rf alembic`) and re-ran `alembic init -t async alembic` against a clean path.
3. Patched `alembic/env.py` to explicitly call `config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)` before any migration logic runs, sourcing the real URL from the app's own config module instead of relying on `alembic.ini`'s static value — this also keeps the DB password out of a file that could accidentally get committed.
4. Verified via a standalone connection test script that the direct connection works on the current network; pooler swap deferred unless this breaks on a different network (e.g. deployment environment).

**Status:** Database connectivity is fully verified end-to-end — model definition → migration generation → migration applied → confirmed live in Supabase. This is the foundation the rest of Phase 1 builds on.

**Next up:**
- `Doctor`, `Appointment`, `VisitRecord` models + migration
- Repository layer (`PatientRepository`, `AppointmentRepository`)
- `booking_service` — overlap constraint + 8:30 PM cutoff logic, with pytest cases written first (TDD for this one component specifically, since the expected behavior is already fully locked from Phase 0 design)
- Minimal single-password route gate (correction to the original plan — needed in P1, not deferred to P2, since P1 must be safely deployable on its own if P2 onward doesn't happen)
- REST routers for all 4 resources
- Basic Jinja2 click-button GUI
- Manual end-to-end walkthrough: book → appears on dashboard → mark complete → appears in visit history

---
