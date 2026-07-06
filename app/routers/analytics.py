"""
Analytics endpoint — computes daily operational metrics from existing
appointment data. No new tables, no schema changes — pure aggregation
over what already exists.

Designed for the frontend's collapsible analytics strip.
"""
from datetime import datetime, date, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.appointment import Appointment
from app.core.security import staff_only, UserRole

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/daily")
async def daily_analytics(
    on_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """
    Returns operational metrics for a given date (defaults to today IST).
    All metrics are computed live from the appointments table.
    """
    # Default to today in IST
    if on_date is None:
        ist = timezone(timedelta(hours=5, minutes=30))
        on_date = datetime.now(ist).date()

    day_start = datetime.combine(on_date, datetime.min.time()).replace(
        tzinfo=timezone(timedelta(hours=5, minutes=30))
    )
    day_end = datetime.combine(on_date, datetime.max.time()).replace(
        tzinfo=timezone(timedelta(hours=5, minutes=30))
    )

    try:
        # All appointments for the day
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.scheduled_start >= day_start,
                    Appointment.scheduled_start <= day_end,
                )
            )
        )
        appts = result.scalars().all()

        # Status breakdown
        status_counts = {}
        for a in appts:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1

        # Priority band distribution
        band_counts = {"critical": 0, "high": 0, "medium": 0, "routine": 0}
        scores = []
        for a in appts:
            band = a.priority_band if a.priority_band in band_counts else "routine"
            band_counts[band] += 1
            scores.append(a.priority_score)

        avg_score = round(sum(scores) / len(scores)) if scores else 0

        # No-show risk: scheduled appointments booked more than 5 days ago
        # that haven't been completed — proxy for likelihood of no-show
        five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
        no_show_risk = [
            a for a in appts
            if a.status == "scheduled"
            and a.booked_at is not None
            and a.booked_at < five_days_ago
        ]

        # Completion rate
        total = len(appts)
        completed = status_counts.get("completed", 0)
        completion_rate = round((completed / total) * 100) if total > 0 else 0

        # Doctor load distribution
        doctor_load = {}
        for a in appts:
            if a.status != "cancelled":
                doctor_load[a.doctor_id] = doctor_load.get(a.doctor_id, 0) + 1

        return {
            "date": on_date.isoformat(),
            "total": total,
            "status_breakdown": {
                "scheduled": status_counts.get("scheduled", 0),
                "completed": status_counts.get("completed", 0),
                "cancelled": status_counts.get("cancelled", 0),
                "no_show": status_counts.get("no_show", 0),
            },
            "priority_distribution": band_counts,
            "avg_priority_score": avg_score,
            "completion_rate_pct": completion_rate,
            "no_show_risk_count": len(no_show_risk),
            "no_show_risk_ids": [a.appointment_id for a in no_show_risk],
            "doctor_load": doctor_load,
            "busiest_hour": _busiest_hour(appts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics query failed: {e}")


def _busiest_hour(appts) -> str | None:
    """Returns the busiest clinic hour as a readable string e.g. '17:00–18:00'."""
    if not appts:
        return None
    hour_counts = {}
    for a in appts:
        if a.status != "cancelled":
            ist = timezone(timedelta(hours=5, minutes=30))
            hour = a.scheduled_start.astimezone(ist).hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
    if not hour_counts:
        return None
    busiest = max(hour_counts, key=hour_counts.get)
    return f"{busiest:02d}:00–{busiest+1:02d}:00"
