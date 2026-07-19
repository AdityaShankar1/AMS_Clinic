"""
Unit tests for NLP appointment parsing.
All tests run without DB or network — pure logic.
"""
from datetime import date, time
from app.services.nlp_service import parse_appointment_request, WINDOWS


TODAY = date(2026, 7, 19)  # fixed reference date


def test_today_evening_resolves():
    r = parse_appointment_request("I want an appointment today evening", today=TODAY)
    assert r.resolved_date == TODAY
    assert r.window_name == "evening"
    assert r.window_start == time(16, 0)
    assert r.window_end == time(20, 0)


def test_tomorrow_morning_resolves():
    from datetime import timedelta
    r = parse_appointment_request("tomorrow morning", today=TODAY)
    assert r.resolved_date == TODAY + timedelta(days=1)
    assert r.window_name == "morning"


def test_slots_are_20_min_apart():
    r = parse_appointment_request("today morning", today=TODAY)
    if len(r.slots) >= 2:
        delta = r.slots[1] - r.slots[0]
        assert delta.seconds == 1200  # 20 minutes


def test_evening_window_is_4_to_8():
    start, end = WINDOWS["evening"]
    assert start == time(16, 0)
    assert end == time(20, 0)


def test_morning_window_is_8_to_10():
    start, end = WINDOWS["morning"]
    assert start == time(8, 0)
    assert end == time(10, 0)


def test_no_slots_in_break_time():
    """Lunch break 12–16 should produce no slots."""
    r = parse_appointment_request("today noon", today=TODAY)
    for slot in r.slots:
        assert slot.hour < 12 or slot.hour >= 16, f"Slot {slot} is in break time"


def test_tonight_maps_to_evening():
    r = parse_appointment_request("tonight", today=TODAY)
    assert r.window_name == "evening"


def test_unknown_date_returns_not_understood():
    r = parse_appointment_request("xyzzy frobble", today=TODAY)
    assert r.resolved_date is None
    assert "Could not understand" in r.interpretation


def test_no_window_returns_full_day_slots():
    r = parse_appointment_request("tomorrow", today=TODAY)
    if r.resolved_date and r.slots:
        hours = {s.hour for s in r.slots}
        # Should include both morning and evening hours
        assert any(h < 12 for h in hours)
        assert any(h >= 16 for h in hours)
