"""
Lightweight NLP for appointment time extraction.
No LLM. Uses dateparser for date resolution + rule-based
time-of-day mapping for clinic-specific vocabulary.

Clinic schedule:
  Morning : 08:00 – 10:00
  Noon    : 10:00 – 12:00
  (Break  : 12:00 – 16:00)
  Evening : 16:00 – 20:00  (covers "evening" + "night" —
            patients rarely say "tonight" so we merge both)
  Last hr : 20:00 – 21:00  (manual only, excluded from AMS)

Slots are generated every 20 minutes within the resolved window.
"""
from __future__ import annotations
import re
from datetime import date, datetime, time, timedelta, timezone

import dateparser

IST = timezone(timedelta(hours=5, minutes=30))

# ── Clinic constants ───────────────────────────────────────────────────────
SLOT_DURATION = timedelta(minutes=20)

WINDOWS: dict[str, tuple[time, time]] = {
    "morning": (time(8, 0),  time(10, 0)),
    "noon":    (time(10, 0), time(12, 0)),
    "evening": (time(16, 0), time(20, 0)),  # merges "evening" + "night"
    "night":   (time(18, 0), time(20, 0)),
}

# Words that map to a named window
_WINDOW_ALIASES: dict[str, str] = {
    "morning":   "morning",
    "mornings":  "morning",
    "am":        "morning",
    "noon":      "noon",
    "afternoon": "noon",
    "midday":    "noon",
    "mid-day":   "noon",
    "evening":   "evening",
    "evenings":  "evening",
    "tonight":   "evening",
    "night":     "evening",
    "nights":    "evening",
    "pm":        "evening",
    "late":      "evening",
}


# ── Public API ─────────────────────────────────────────────────────────────

class ParseResult:
    def __init__(
        self,
        resolved_date: date | None,
        window_name: str | None,
        window_start: time | None,
        window_end: time | None,
        slots: list[datetime],
        raw_text: str,
        interpretation: str,
    ):
        self.resolved_date = resolved_date
        self.window_name = window_name
        self.window_start = window_start
        self.window_end = window_end
        self.slots = slots
        self.raw_text = raw_text
        self.interpretation = interpretation

    def to_dict(self) -> dict:
        return {
            "resolved_date": self.resolved_date.isoformat() if self.resolved_date else None,
            "window_name": self.window_name,
            "window_start": self.window_start.strftime("%H:%M") if self.window_start else None,
            "window_end": self.window_end.strftime("%H:%M") if self.window_end else None,
            "slots": [s.isoformat() for s in self.slots],
            "interpretation": self.interpretation,
        }


def parse_appointment_request(text: str, today: date | None = None) -> ParseResult:
    """
    Parse natural language into a date + time window + available slot list.

    Examples:
      "I want an appointment today evening"
        → date=today, window=evening, slots=[16:00, 16:20, ..., 19:40]
      "tomorrow morning"
        → date=tomorrow, window=morning, slots=[08:00, ..., 09:40]
      "next Monday"
        → date=next Monday, window=None (full day shown)
    """
    if today is None:
        today = datetime.now(IST).date()

    text_lower = text.lower()

    # ── Step 1: detect time-of-day window ─────────────────────────────────
    window_name: str | None = None
    for alias, name in _WINDOW_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text_lower):
            window_name = name
            break

    # ── Step 2: resolve date using dateparser ──────────────────────────────
    # Strip time-of-day words so dateparser doesn't get confused by them
    clean = text_lower
    for alias in _WINDOW_ALIASES:
        clean = re.sub(rf"\b{re.escape(alias)}\b", "", clean)
    clean = re.sub(r"\b(appointment|appt|booking|slot|visit|i want|i need|book|for|an|a|the|please|can|could|would|like)\b", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    resolved_date: date | None = None
    if clean:
        parsed = dateparser.parse(
            clean,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.combine(today, time(0, 0)),
                "RETURN_AS_TIMEZONE_AWARE": False,
                "DATE_ORDER": "DMY",
            },
        )
        if parsed:
            resolved_date = parsed.date()

    # Fallback: if text had "today" or similar but dateparser missed it
    if resolved_date is None:
        if any(w in text_lower for w in ["today", "now", "tonight", "this evening", "this morning"]):
            resolved_date = today
        elif any(w in text_lower for w in ["tomorrow", "tmrw", "tmr"]):
            resolved_date = today + timedelta(days=1)

    # ── Step 3: build slot list ────────────────────────────────────────────
    slots: list[datetime] = []
    win_start: time | None = None
    win_end: time | None = None

    if resolved_date:
        if window_name and window_name in WINDOWS:
            win_start, win_end = WINDOWS[window_name]
            slots = _generate_slots(resolved_date, win_start, win_end)
        else:
            # No window specified — return all available clinic slots
            for ws, we in [(time(8,0), time(12,0)), (time(16,0), time(20,0))]:
                slots.extend(_generate_slots(resolved_date, ws, we))
            win_start, win_end = time(8, 0), time(20, 0)

        # Drop slots in the past
        now_ist = datetime.now(IST).replace(tzinfo=None)
        slots = [s for s in slots if datetime.combine(resolved_date, s.time()) > now_ist]

    # ── Step 4: build human interpretation ────────────────────────────────
    parts = []
    if resolved_date:
        if resolved_date == today:
            parts.append("today")
        elif resolved_date == today + timedelta(days=1):
            parts.append("tomorrow")
        else:
            parts.append(resolved_date.strftime("%A, %d %b"))
    if window_name:
        parts.append(f"in the {window_name}")
    interpretation = "Showing slots for " + " ".join(parts) if parts else "Could not understand the date — please try again."

    return ParseResult(
        resolved_date=resolved_date,
        window_name=window_name,
        window_start=win_start,
        window_end=win_end,
        slots=slots,
        raw_text=text,
        interpretation=interpretation,
    )


def _generate_slots(d: date, start: time, end: time) -> list[datetime]:
    slots = []
    current = datetime.combine(d, start)
    end_dt = datetime.combine(d, end)
    while current < end_dt:
        slots.append(current)
        current += SLOT_DURATION
    return slots
