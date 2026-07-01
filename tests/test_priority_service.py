from app.services.priority_service import score_priority


def test_new_high_severity_urgent_phased_case_scores_critical():
    result = score_priority(
        completed_visits=0,
        patient_priority_label="auto",
        severity_level=5,
        urgency_level=5,
        treatment_phase="phased",
        xray_needed=True,
        blood_test_needed=True,
    )

    assert result.patient_priority_label == "new"
    assert result.priority_band == "critical"
    assert result.priority_score >= 75
    assert "x-ray report required" in result.priority_summary
    assert "blood test report required" in result.priority_summary


def test_established_regular_patients_get_history_boost():
    regular = score_priority(
        completed_visits=5,
        patient_priority_label="auto",
        severity_level=2,
        urgency_level=2,
        treatment_phase="one_time",
    )
    new_patient = score_priority(
        completed_visits=0,
        patient_priority_label="new",
        severity_level=2,
        urgency_level=2,
        treatment_phase="one_time",
    )

    assert regular.patient_priority_label == "established"
    assert regular.priority_score > new_patient.priority_score
    assert "established patient" in regular.priority_summary


def test_manual_label_and_override_are_reflected():
    result = score_priority(
        completed_visits=3,
        patient_priority_label="established",
        severity_level=3,
        urgency_level=4,
        treatment_phase="phased",
        is_urgent_override=True,
    )

    assert result.patient_priority_label == "established"
    assert result.priority_band in {"high", "critical"}
    assert "urgent override" in result.priority_summary
