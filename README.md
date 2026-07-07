[![CI](https://github.com/AdityaShankar1/AMS_Clinic/actions/workflows/ci.yml/badge.svg)](https://github.com/AdityaShankar1/AMS_Clinic/actions/workflows/ci.yml)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-Deployed-000000?style=flat-square&logo=vercel&logoColor=white)

# Clinic Appointment Management System

**Production-ready scheduling platform** for a real dental clinic (2 dentists + 1 receptionist). Eliminates double-bookings, no-shows, and lost patient context.

**Stack:** FastAPI • PostgreSQL (Supabase) • Vercel

<img width="1467" height="681" alt="Screenshot 2026-07-04 at 9 17 26 PM" src="https://github.com/user-attachments/assets/3bf643f4-ad31-4929-85a5-152863dbe973" />


[Live Demo](https://ams-clinic.vercel.app/) • [Frontend Repo](https://ams-clinic-frontend.vercel.app/)

---

## Problem It Solves
- ❌ No-shows with no tracking → **Status tracking + history**
- ❌ Urgent cases lost in list → **Priority overrides + visit history**
- ❌ Concurrent booking collisions → **Database-level overlap constraint**

---

## Architecture
**Clean 3-layer monolith:** Routers → Services → Repositories → DB

```
Browser → Nginx → FastAPI → PostgreSQL (Supabase)
```

**Key Rules:**
- Double-booking prevention lives in **database** (exclusion constraint)
- 8:30 PM cutoff enforced in **service layer**
- No hard deletes (status = `cancelled` / soft deactivation)
- Age calculated from DOB; visit counts derived from completed appointments

---

## Roles
| Role | Permissions |
|------|-------------|
| **Patient** | View/cancel own appointments |
| **Receptionist** | Book/reschedule/update appointments, manage patients |
| **Doctor** | All receptionist actions + urgency overrides + clinical records |

*Hardcoded credentials for MVP; JWT auth coming soon*

---

## Tech Stack
| Layer | Choice |
|-------|--------|
| Backend | FastAPI + Uvicorn |
| Database | PostgreSQL (Supabase) + `btree_gist` |
| ORM | SQLAlchemy (async) + Alembic |
| Frontend | Jinja2 (Phase 1) → React + Tailwind (Phase 2) |
| Deployment | AWS EC2 + Nginx |

---

## Roadmap
| Phase | Focus |
|-------|-------|
| **1** | ![Phase Complete](https://img.shields.io/badge/Status-Complete-success?style=flat-square) CRUD endpoints + Jinja2 GUI + hardcoded auth |
| **2** | ![Phase Complete](https://img.shields.io/badge/Status-Complete-success?style=flat-square) auth + React frontend + tests |
| **3** | ![Phase In Progress](https://img.shields.io/badge/Status-In_Progress-orange?style=flat-square) NLP booking (`dateparser`) + Redis caching + analytics |
| **4** | ![Phase Complete](https://img.shields.io/badge/Status-Complete-success?style=flat-square) Docker + CI/CD + production hardening |

---

## API Surface
| Resource | Operations |
|----------|------------|
| `/patients` | Create, list, update, soft-deactivate |
| `/appointments` | Book, list, update, cancel |
| `/visit_records` | Create, list, update (never delete) |
| `/doctors` | List (seeded) |

<img width="996" height="630" alt="Screenshot 2026-07-04 at 9 16 51 PM" src="https://github.com/user-attachments/assets/a7277393-2594-45c0-be3a-cfd281d014d6" />

---

## Demo Data
```bash
python seed_demo_data.py
```
Seeds 2 dentists, dummy patients, historical visits, upcoming appointments with varying urgency/treatment phases.

---

## Project Structure
```
app/
├── core/          # Config
├── db/            # Session + base
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic schemas
├── routers/       # API endpoints
├── services/      # Business logic
├── repositories/  # Data access
└── templates/     # Jinja2 views
```

---

## Open Decisions
- Per-sitting vs per-treatment invoicing → Defer to Phase 3
- Weekend schedule → Confirm with clinic
- Fixed vs variable durations → Schema supports both (default 20min)

---

*Phase 1, 2, and 4 (deployment) complete • All paths independently demonstrable*
