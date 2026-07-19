"""
NLP appointment parsing endpoint.
No auth required — patient-facing, public endpoint.
"""
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.nlp_service import parse_appointment_request

router = APIRouter(prefix="/nlp", tags=["nlp"])


class ParseRequest(BaseModel):
    text: str
    today: date | None = None  # optional override for testing


class SlotOption(BaseModel):
    iso: str          # full ISO datetime string for API use
    display: str      # "4:00 PM" for UI


class ParseResponse(BaseModel):
    interpretation: str
    resolved_date: str | None
    window_name: str | None
    slots: list[SlotOption]
    understood: bool


@router.post("/parse-appointment", response_model=ParseResponse)
async def parse_appointment(payload: ParseRequest):
    """
    Parse natural language appointment request into structured slots.

    Input:  {"text": "I want an appointment today evening"}
    Output: interpretation + list of available 20-min slots in that window

    No LLM — uses dateparser + clinic-specific time-of-day vocabulary.
    """
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=422, detail="Text cannot be empty.")

    if len(payload.text) > 200:
        raise HTTPException(status_code=422, detail="Text too long — keep it under 200 characters.")

    result = parse_appointment_request(payload.text, today=payload.today)

    slots = [
        SlotOption(
            iso=s.isoformat(),
            display=s.strftime("%-I:%M %p"),
        )
        for s in result.slots
    ]

    return ParseResponse(
        interpretation=result.interpretation,
        resolved_date=result.resolved_date.isoformat() if result.resolved_date else None,
        window_name=result.window_name,
        slots=slots,
        understood=result.resolved_date is not None,
    )
