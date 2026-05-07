from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models import Alert, Batch, Device, ModelPrediction, Recommendation, SensorReading
from app.services.ai.time_prediction_model import predict_time_remaining


def _reset_runtime_tables() -> None:
    db = SessionLocal()
    try:
        db.query(Alert).delete()
        db.query(Recommendation).delete()
        db.query(ModelPrediction).delete()
        db.query(SensorReading).delete()
        db.query(Batch).delete()
        db.commit()
    finally:
        db.close()


def _default_device_internal_id() -> int:
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.device_id == settings.DEFAULT_DEVICE_ID).first()
        assert device is not None
        return device.id
    finally:
        db.close()


def test_no_batch_returns_none_low_rule() -> None:
    result = predict_time_remaining(
        current_data={"temperature": 45.0, "moisture": 55.0, "gas": 300.0},
        batch_start_time=None,
        device_internal_id=1,
        db_session=None,
    )
    assert result["time_remaining_hours"] is None
    assert result["prediction_confidence"] == "LOW"
    assert result["prediction_source"] == "RULE"
    assert result["insight"] == "No active batch. Start a batch to enable lifecycle tracking"
    assert result["prediction_basis"] == "Batch context not available"


def test_already_ready_returns_zero_high() -> None:
    batch_start = datetime.now(timezone.utc) - timedelta(days=11)
    result = predict_time_remaining(
        current_data={"temperature": 25.0, "moisture": 55.0, "gas": 300.0},
        batch_start_time=batch_start,
        device_internal_id=1,
        db_session=None,
    )
    assert result["time_remaining_hours"] == 0.0
    assert result["prediction_confidence"] == "HIGH"
    assert result["prediction_source"] == "RULE"
    assert result["prediction_basis"] == "Compost has reached readiness conditions"


def test_cooling_trend_uses_slope_high_confidence() -> None:
    init_db()
    _reset_runtime_tables()
    device_id = _default_device_internal_id()

    db = SessionLocal()
    try:
        base = datetime.now(timezone.utc) - timedelta(hours=2)
        temps = [58.0, 56.0, 54.0, 52.0, 50.0]
        for idx, temp in enumerate(temps):
            t = base + timedelta(minutes=30 * idx)
            db.add(
                SensorReading(
                    device_id=device_id,
                    batch_id=None,
                    server_timestamp=t,
                    device_timestamp=t,
                    temperature_c=temp,
                    moisture_pct=55.0,
                    gas_ppm=300.0,
                    quality_status="valid",
                    quality_reasons=[],
                )
            )
        db.commit()

        result = predict_time_remaining(
            current_data={"temperature": 50.0, "moisture": 55.0, "gas": 300.0},
            batch_start_time=datetime.now(timezone.utc) - timedelta(days=4),
            device_internal_id=device_id,
            db_session=db,
        )
        assert result["prediction_source"] == "RULE"
        assert result["prediction_confidence"] == "HIGH"
        assert result["time_remaining_hours"] is not None
        assert result["time_remaining_hours"] > 0
        assert result["prediction_basis"] == "Based on temperature cooling trend over recent readings"
    finally:
        db.close()


def test_no_history_falls_back_to_heuristic_medium() -> None:
    init_db()
    _reset_runtime_tables()
    device_id = _default_device_internal_id()
    db = SessionLocal()
    try:
        result = predict_time_remaining(
            current_data={"temperature": 45.0, "moisture": 55.0, "gas": 300.0},
            batch_start_time=datetime.now(timezone.utc) - timedelta(days=2),
            device_internal_id=device_id,
            db_session=db,
        )
        assert result["prediction_source"] == "RULE"
        assert result["prediction_confidence"] == "MEDIUM"
        assert result["time_remaining_hours"] is not None
        assert result["prediction_basis"] == "Estimated using compost lifecycle heuristics and current conditions"
    finally:
        db.close()


def test_high_moisture_increases_heuristic_time() -> None:
    batch_start = datetime.now(timezone.utc) - timedelta(days=2)
    base = predict_time_remaining(
        current_data={"temperature": 45.0, "moisture": 55.0, "gas": 300.0},
        batch_start_time=batch_start,
        device_internal_id=1,
        db_session=None,
    )
    high_moisture = predict_time_remaining(
        current_data={"temperature": 45.0, "moisture": 80.0, "gas": 300.0},
        batch_start_time=batch_start,
        device_internal_id=1,
        db_session=None,
    )

    assert base["time_remaining_hours"] is not None
    assert high_moisture["time_remaining_hours"] is not None
    assert high_moisture["time_remaining_hours"] > base["time_remaining_hours"]
