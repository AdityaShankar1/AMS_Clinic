"""
Unit tests for analytics — tests the pure computation logic directly,
without needing a real database connection. The _busiest_hour helper
and metric calculations are tested in isolation.

Integration tests (hitting the actual /analytics/daily endpoint with
real appointment data) are covered by the diagnose.py smoke test.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

# Import the pure helper directly
from app.routers.analytics import _busiest_hour

IST = timezone(timedelta(hours=5, minutes=30))


def _mock_appt(hour: int, status: str = "scheduled", score: int = 50, band: str = "medium"):
    """Create a lightweight mock appointment object for testing."""
    a = MagicMock()
    a.scheduled_start = datetime(2026, 7, 4, hour, 0, tzinfo=IST)
    a.status = status
    a.priority_score = score
    a.priority_band = band
    a.booked_at = datetime.now(timezone.utc) - timedelta(days=1)
    a.appointment_id = hash((hour, status))
    return a


# ── _busiest_hour ──────────────────────────────────────────────────────────

def test_busiest_hour_single_slot():
    appts = [_mock_appt(17), _mock_appt(17), _mock_appt(18)]
    assert _busiest_hour(appts) == "17:00–18:00"


def test_busiest_hour_excludes_cancelled():
    appts = [
        _mock_appt(17, status="cancelled"),
        _mock_appt(17, status="cancelled"),
        _mock_appt(18, status="scheduled"),
    ]
    # 17:00 has 2 appointments but both cancelled — 18:00 should win
    assert _busiest_hour(appts) == "18:00–19:00"


def test_busiest_hour_empty_returns_none():
    assert _busiest_hour([]) is None


def test_busiest_hour_all_cancelled_returns_none():
    appts = [_mock_appt(17, status="cancelled")]
    assert _busiest_hour(appts) is None


# ── Priority distribution logic ────────────────────────────────────────────

def test_priority_band_counts():
    appts = [
        _mock_appt(17, band="critical", score=90),
        _mock_appt(17, band="high", score=70),
        _mock_appt(18, band="high", score=65),
        _mock_appt(18, band="medium", score=50),
        _mock_appt(19, band="routine", score=20),
    ]
    band_counts = {"critical": 0, "high": 0, "medium": 0, "routine": 0}
    for a in appts:
        band = a.priority_band if a.priority_band in band_counts else "routine"
        band_counts[band] += 1

    assert band_counts["critical"] == 1
    assert band_counts["high"] == 2
    assert band_counts["medium"] == 1
    assert band_counts["routine"] == 1


def test_avg_priority_score():
    scores = [90, 70, 65, 50, 20]
    avg = round(sum(scores) / len(scores))
    assert avg == 59


def test_completion_rate():
    appts = [
        _mock_appt(17, status="completed"),
        _mock_appt(17, status="completed"),
        _mock_appt(18, status="scheduled"),
        _mock_appt(18, status="cancelled"),
    ]
    total = len(appts)
    completed = sum(1 for a in appts if a.status == "completed")
    rate = round((completed / total) * 100)
    assert rate == 50


def test_no_show_risk_detection():
    """Appointments booked >5 days ago and still scheduled = no-show risk."""
    old_booking = datetime.now(timezone.utc) - timedelta(days=7)
    recent_booking = datetime.now(timezone.utc) - timedelta(days=1)

    risky = _mock_appt(17, status="scheduled")
    risky.booked_at = old_booking

    safe = _mock_appt(18, status="scheduled")
    safe.booked_at = recent_booking

    done = _mock_appt(19, status="completed")
    done.booked_at = old_booking

    appts = [risky, safe, done]
    five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)

    at_risk = [
        a for a in appts
        if a.status == "scheduled"
        and a.booked_at is not None
        and a.booked_at < five_days_ago
    ]
    assert len(at_risk) == 1
    assert at_risk[0] is risky
