from datetime import datetime, timedelta, timezone

from app.services.ai.stage_model import predict_stage


def test_early_days_returns_initial() -> None:
    batch_start = datetime.now(timezone.utc) - timedelta(days=1)
    result = predict_stage({"temperature": 35.0, "moisture": 55.0, "gas": 300.0}, batch_start)
    assert result == {"stage_label": "INITIAL", "stage_confidence": "LOW"}


def test_active_when_high_temp_and_day_ge_2() -> None:
    batch_start = datetime.now(timezone.utc) - timedelta(days=3)
    result = predict_stage({"temperature": 50.0, "moisture": 55.0, "gas": 300.0}, batch_start)
    assert result["stage_label"] == "ACTIVE"
    assert result["stage_confidence"] in {"HIGH", "MEDIUM"}


def test_curing_when_mid_temp_and_day_ge_5() -> None:
    batch_start = datetime.now(timezone.utc) - timedelta(days=6)
    result = predict_stage({"temperature": 37.0, "moisture": 55.0, "gas": 300.0}, batch_start)
    assert result["stage_label"] == "CURING"
    assert result["stage_confidence"] in {"HIGH", "MEDIUM"}


def test_ready_when_low_temp_and_day_ge_10() -> None:
    batch_start = datetime.now(timezone.utc) - timedelta(days=11)
    result = predict_stage({"temperature": 25.0, "moisture": 55.0, "gas": 300.0}, batch_start)
    assert result["stage_label"] == "READY"
    assert result["stage_confidence"] in {"HIGH", "MEDIUM"}


def test_no_batch_returns_unknown() -> None:
    result = predict_stage({"temperature": 45.0, "moisture": 55.0, "gas": 300.0}, None)
    assert result == {"stage_label": "UNKNOWN", "stage_confidence": "LOW"}


def test_invalid_temp_returns_initial_low() -> None:
    batch_start = datetime.now(timezone.utc) - timedelta(days=3)
    result = predict_stage({"temperature": "bad", "moisture": 55.0, "gas": 300.0}, batch_start)
    assert result == {"stage_label": "INITIAL", "stage_confidence": "LOW"}
