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

## 2026-06-30 (continued) — Migration Tracking Desync: Root Cause & Fix

**Context:** While cleaning up a redundant empty migration (`ee92aa6b12e2` — a duplicate, no-op revision created by accidentally running `alembic revision` twice), attempted to roll it back and delete it.

**Issue faced:**
1. Ran `alembic downgrade faf2c35cd6ee && rm <empty migration file> && alembic current` as three commands in sequence (not chained with `&&`, but pasted as separate lines). The `downgrade` command failed immediately with `ValueError: the greenlet library is required to use this function` — the `greenlet` package, a runtime dependency of SQLAlchemy's async engine, had never been explicitly installed (it's normally pulled in as a transitive dependency, but was missing here).
2. Because the three commands weren't actually dependent on each other succeeding (each ran independently), the `rm` command executed anyway even though `downgrade` had failed — deleting the empty migration file from disk.
3. This left the system in a broken, inconsistent state: Postgres's internal `alembic_version` tracking table still pointed at `ee92aa6b12e2` (the deleted revision), but no file on disk defined that revision anymore. Every subsequent `alembic` command (`downgrade`, `current`) failed with `Can't locate revision identified by 'ee92aa6b12e2'`, since Alembic had no way to resolve a revision ID it couldn't find a corresponding file for.

**Root cause:** Alembic tracks migration state in two places that must always agree: the migration files on disk, and a single-row `alembic_version` table inside the actual Postgres database. Deleting a migration file does not automatically update that tracking table — if the deleted revision was the one currently marked as "applied," Alembic loses the ability to navigate forward or backward at all, since it tracks revisions as a linked chain (each migration points to the one before it) and a missing link breaks the chain.

**Resolution:**
1. Installed the missing `greenlet` dependency (`pip install greenlet`) to fix the underlying error that triggered the desync in the first place.
2. Since the empty migration (`ee92aa6b12e2`) never contained any real schema changes — its `upgrade()`/`downgrade()` were both just `pass` — there was nothing destructive to actually undo. The fix was to directly correct the `alembic_version` tracking table via a manual SQL update, rather than trying to use Alembic's own downgrade machinery (which couldn't run without the missing file):
   ```sql
   UPDATE alembic_version SET version_num = 'faf2c35cd6ee' WHERE version_num = 'ee92aa6b12e2';
   ```
3. Verified the fix with `alembic current`, which correctly reported `faf2c35cd6ee (head)` — confirming the filesystem, Alembic's internal state, and the live database were all back in agreement.

**Lesson learned:** When deleting or modifying Alembic migration files, always run the downgrade command **first** and confirm it succeeds before removing the file — never delete a migration file speculatively or in parallel with the downgrade attempt. If a desync happens anyway, correcting the `alembic_version` table directly is a safe fix *only* when the affected migration made no real schema changes (which was true here) — for a migration that actually altered the schema, the correct recovery path would be to manually reverse those specific schema changes via SQL, not just edit the tracking table.

**Status:** Migration state fully synced. Ready to verify the overlap exclusion constraint itself with a live insert test, then move to the repository layer.

---

## 2026-06-30 (continued) — Overlap Exclusion Constraint: A Chain of Six Root Causes

**Context:** Verifying the double-booking prevention constraint (`EXCLUDE USING gist` on `appointments`) actually rejects overlapping bookings, as designed in Phase 0. This took significantly longer than expected — six distinct, real bugs surfaced in sequence, each masking the next until fixed. Documenting all of them since this is a genuinely instructive trace through how migration state, Postgres internals, and async tooling can silently diverge.

**Bug 1 — missing `greenlet` dependency.** `alembic downgrade` failed with `ValueError: the greenlet library is required`. SQLAlchemy's async engine depends on `greenlet` at runtime; it's normally pulled in transitively but was missing here. Fixed with `pip install greenlet`.

**Bug 2 — Alembic/database tracking desync after deleting a migration file.** A redundant empty migration was deleted from disk without first confirming its `downgrade()` had succeeded (it failed due to Bug 1, but the file was deleted anyway since the commands weren't chained with `&&`). This left Postgres's `alembic_version` table pointing at a revision ID with no corresponding file, breaking every subsequent Alembic command. Fixed by directly correcting `alembic_version` via SQL, since the deleted migration had no real schema changes to undo.

**Bug 3 — `server_default` never applied despite editing the model.** Patched `app/models/patient.py` and `app/models/appointment.py` to add `server_default` to several boolean/status columns, generated a migration, applied it — but the live database showed no defaults had actually changed. Root cause: an earlier attempt to edit these files used a tool that had no access to the actual local filesystem, so the edits silently never landed on disk in the first place. Confirmed via `grep` that the file still showed the old code, then rewrote the files correctly via `cat`.

**Bug 4 — Alembic's autogenerate ignores `server_default` changes by default.** Even with the model correctly edited, `alembic revision --autogenerate` produced an empty migration (`upgrade(): pass`). Root cause: Alembic does not compare `server_default` values between model and database unless explicitly told to via `compare_server_default=True` in `context.configure(...)`. This flag was missing from `alembic/env.py` entirely. Added it to both the offline and online `context.configure(...)` calls (the async template has two separate call sites — an initial fix only patched one, due to differing formatting between the two blocks).

**Bug 5 — `tsrange()` does not support `timestamptz` columns.** With the exclusion constraint migration (written back in Phase 0 design) finally being applied for the first time, it failed with `function tsrange(timestamp with time zone, timestamp with time zone) does not exist`. Root cause: `scheduled_start` is `DateTime(timezone=True)` (i.e. `timestamptz`), and Postgres's `tsrange` type only accepts plain `timestamp` (no timezone) — the correct function for timezone-aware ranges is `tstzrange`. Also discovered in the process: this exact failure had silently occurred the *first* time this migration was marked "applied" days earlier — because Alembic runs each migration inside a transaction, the failed `ALTER TABLE` rolled back the `CREATE EXTENSION` statement that preceded it in the same migration, leaving no trace except an Alembic history entry that falsely claimed success.

**Bug 6 — GiST exclusion constraints require `IMMUTABLE` functions, and timestamp+interval arithmetic isn't immutable.** Switching to `tstzrange` fixed the function-not-found error, but produced a new one: `functions in index expression must be marked IMMUTABLE`. Root cause: the constraint computed each appointment's end time inline (`scheduled_start + duration_minutes * interval '1 minute'`), and Postgres classifies timestamp-interval arithmetic as `STABLE`, not `IMMUTABLE`, since interval semantics can depend on session settings — this is a well-documented limitation of GiST indexes specifically.

**Final fix:** Added a real `scheduled_end` column to `appointments` instead of computing the end time inline. A Postgres trigger (`set_scheduled_end()`, fired `BEFORE INSERT OR UPDATE OF scheduled_start, duration_minutes`) keeps it automatically in sync, so neither the application layer nor any future raw SQL insert needs to remember to compute it manually — the database guarantees consistency. The exclusion constraint was rewritten to use `tstzrange(scheduled_start, scheduled_end)`, referencing only the two plain columns, satisfying the immutability requirement.

**Verification:** Ran a live test — inserted one appointment, attempted a second overlapping appointment for the same doctor, confirmed Postgres correctly raised `ExclusionViolationError: conflicting key value violates exclusion constraint "no_overlap_for_regular_bookings"`. This is the actual, verified behavior the system was designed around in Phase 0 — not assumed, not just "migration ran without error."

**Lesson learned:** A migration reporting success in `alembic upgrade head` output is not sufficient proof that its intended effect actually exists in the database — transactional rollback on a later statement in the same migration can silently undo an earlier one. From this point forward, any constraint or trigger added via migration gets an explicit follow-up query against `pg_constraint`/`pg_trigger` (or equivalent) to confirm it actually exists, not just that the migration command exited cleanly.

**Status:** Double-booking prevention is now fully implemented and verified end-to-end: schema, migration, and live behavior all agree. This was the last unverified piece of the core Phase 1 data-integrity design. Moving to the repository layer next.

---

## 2026-06-30 (continued) — Test Suite: venv PATH Resolution + pytest-asyncio Config

**Context:** Converted the manual overlap-constraint test script into a proper pytest suite (`tests/test_booking_constraints.py`), adding a second test for the boundary case (back-to-back appointments that touch but don't overlap).

**Issue faced:** Running `pytest tests/ -v` failed both tests with "async def functions are not natively supported," even after confirming `pytest-asyncio` was installed (`pip show pytest-asyncio` found it correctly inside the venv) and after adding `pytest.ini` with `asyncio_mode = auto` — which itself produced a `PytestConfigWarning: Unknown config option: asyncio_mode`, meaning that specific pytest process didn't recognize the plugin's config at all.

**Root cause:** `which pytest` revealed the actual command being run resolved to a **global** Python 3.14 installation (`/Library/Frameworks/Python.framework/...`), not the project's venv — despite the shell prompt showing `(venv)` as active and `which python3` correctly pointing into the venv. The global pytest installation had no knowledge of `pytest-asyncio`, since that package was only ever installed inside the venv. This is a known class of issue: venv activation modifies `PATH`, but if a tool was already cached/resolved by the shell, or installed in a location that takes precedence, the "active" venv doesn't guarantee every command resolves into it.

**Resolution:** Ran the test suite via `venv/bin/python -m pytest tests/ -v` instead of the bare `pytest` command — explicitly invoking pytest as a module of the venv's own Python interpreter guarantees the correct environment is used, regardless of what `PATH` resolves a bare `pytest` command to.

**Result:** Both tests passed, including the boundary case — confirming `tstzrange`'s default `[)` bounds (inclusive start, exclusive end) correctly allow one appointment to start exactly when a previous one for the same doctor ends, while still correctly rejecting genuine overlaps. This was an important sanity check: a constraint that's stricter than intended would have quietly prevented the clinic from ever booking back-to-back appointments.

**Lesson learned:** Prefer `python -m <tool>` over a bare tool command inside any virtual environment context going forward — it sidesteps an entire class of PATH-resolution bugs where the "active" environment indicator (the `(venv)` prompt prefix) doesn't actually guarantee every command resolves correctly into that environment.

**Status:** Phase 1's core data-integrity guarantee (no-double-booking) is now fully implemented, migrated, and test-covered with both pytest-asyncio config and the venv/PATH issue resolved. Test suite runs cleanly via `venv/bin/python -m pytest tests/ -v`. Ready to move to the repository layer.

---

## 2026-06-30 (continued) — Repository Layer, Booking Service, and Full Test Suite

**Built:**
- `app/repositories/patient_repository.py` — create, get-by-id, search (name/phone), partial update, and `get_previous_visit_count` (derived from completed appointments, never stored — per the project's core design rule).
- `app/repositories/appointment_repository.py` — create, get-by-id, list (filterable by doctor/date/status), status updates, `reschedule_appointment`, `link_reschedule` (marks an original appointment as rescheduled and links it to its replacement, per the urgent-override design from Phase 0), and `check_overlap_exists` (a pre-flight courtesy check — explicitly documented as NOT the source of truth, since only the database's EXCLUDE constraint is race-condition-safe under concurrent requests).
- `app/services/booking_service.py` — the one place the two Phase 0 booking rules live: cutoff time (17:00–20:30, applies to every booking including urgent overrides, no exceptions) and overlap orchestration (skipped for urgent overrides, backed by both a repository pre-check and a try/except around the database's IntegrityError as the final safety net).
- `tests/test_booking_constraints.py` — direct database-level tests for the exclusion constraint (already covered in the earlier debugging arc).
- `tests/test_booking_service.py` — five tests covering the service layer specifically: cutoff rejection, urgent override still respecting cutoff (the one rule with zero exceptions), opening-time rejection, a happy-path booking, and confirmation that urgent override bypasses overlap but nothing else.

**Issues faced:**
1. `pytest-asyncio`'s default per-test event loop conflicted with the shared SQLAlchemy `engine`'s connection pool, which holds asyncpg connections bound to whatever loop was active when first opened. Symptom: `InterfaceError: cannot perform operation: another operation is in progress` on the second test onward.
2. `NoReferencedTableError: Foreign key associated with column 'appointments.doctor_id' could not find table 'doctors'` — occurred only when `Doctor` was never directly imported by the test file or repository module exercising the commit, even though the table genuinely existed in Postgres.

**Resolution:**
1. Set `asyncio_default_fixture_loop_scope = session` and `asyncio_default_test_loop_scope = session` in `pytest.ini`, so all async tests in a run share a single event loop, matching the lifetime of the engine's connection pool.
2. Root cause: SQLAlchemy resolves string-based ForeignKey references (e.g. `"doctors.doctor_id"`) lazily, only when a table is actually needed during a flush/commit — and only models that have been imported somewhere in the running process get registered onto `Base.metadata`. Fixed by centralizing all model imports in `app/models/__init__.py`, then importing that module at the bottom of `app/db/base.py` — guaranteeing every model is registered the moment `Base` itself is touched, regardless of which specific model any individual file happens to import directly.

**Result:** Full test suite (7 tests across both files) passes cleanly via `venv/bin/python -m pytest tests/ -v`. This closes out verification of every Phase 0 system-behavior requirement: no double-booking (database-enforced), cutoff time with no exceptions (application-enforced), and urgent-override correctly bypassing overlap only, never cutoff.

**Lesson learned:** SQLAlchemy's lazy FK string resolution means model registration order/completeness matters in ways that are easy to overlook when each file imports only what it directly references — a central "import everything" module touched early (at `Base` definition) is a standard, low-cost way to close this gap permanently rather than hitting it repeatedly across different test files.

**Status:** Repository layer and booking service complete and fully test-covered. Ready to build REST routers — the layer that exposes this logic over HTTP.

---
