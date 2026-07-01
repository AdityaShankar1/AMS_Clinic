from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriorityResult:
    patient_priority_label: str
    severity_level: int
    urgency_level: int
    treatment_phase: str
    priority_score: int
    priority_band: str
    priority_summary: str


def _clamp_int(value: int | None, low: int, high: int, default: int) -> int:
    try:
        value = int(value) if value is not None else default
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


def _normalize_patient_label(label: str | None, completed_visits: int) -> str:
    if label in {"new", "established"}:
        return label
    return "new" if completed_visits == 0 else "established"


def _band_for_score(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "medium"
    return "routine"


def score_priority(
    *,
    completed_visits: int,
    patient_priority_label: str = "auto",
    severity_level: int = 3,
    urgency_level: int = 3,
    treatment_phase: str = "one_time",
    xray_needed: bool = False,
    blood_test_needed: bool = False,
    is_urgent_override: bool = False,
) -> PriorityResult:
    completed_visits = max(0, int(completed_visits or 0))
    severity_level = _clamp_int(severity_level, 1, 5, 3)
    urgency_level = _clamp_int(urgency_level, 1, 5, 3)
    treatment_phase = treatment_phase if treatment_phase in {"one_time", "phased"} else "one_time"

    normalized_label = _normalize_patient_label(patient_priority_label, completed_visits)

    score = 0
    if normalized_label == "new":
        score += 15
    else:
        # Established patients with a regular recall pattern should surface
        # slightly above one-off visits so the clinic can protect continuity.
        score += 8 + min(completed_visits, 6) * 2

    score += severity_level * 6
    score += urgency_level * 7

    if treatment_phase == "phased":
        score += 12
    else:
        score += 4

    if xray_needed:
        score += 3
    if blood_test_needed:
        score += 3
    if is_urgent_override:
        score += 10

    score = max(0, min(100, score))
    band = _band_for_score(score)

    parts: list[str] = [
        "new patient" if normalized_label == "new" else f"established patient ({completed_visits} prior completed visits)",
        f"severity {severity_level}/5",
        f"urgency {urgency_level}/5",
        "phased treatment" if treatment_phase == "phased" else "one-time issue",
    ]
    if xray_needed:
        parts.append("x-ray report required")
    if blood_test_needed:
        parts.append("blood test report required")
    if is_urgent_override:
        parts.append("urgent override")

    return PriorityResult(
        patient_priority_label=normalized_label,
        severity_level=severity_level,
        urgency_level=urgency_level,
        treatment_phase=treatment_phase,
        priority_score=score,
        priority_band=band,
        priority_summary="; ".join(parts),
    )
