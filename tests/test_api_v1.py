from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.main import app
from app.models import Alert, Batch, Device, ModelPrediction, Recommendation, SensorReading


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


def _set_readings_old_for_rate_limit() -> None:
    db = SessionLocal()
    try:
        old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        for row in db.query(SensorReading).all():
            row.server_timestamp = old_time
        db.commit()
    finally:
        db.close()


def test_health() -> None:
    init_db()
    client = TestClient(app)
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "ok"


def test_ingest_and_latest_endpoints() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    ingest_payload = {
        "device_id": "ESP32_BIN_01",
        "device_timestamp": "2026-03-31T10:25:35Z",
        "temperature_c": 38.4,
        "moisture_pct": 54.2,
        "gas_ppm": 712.5,
    }
    headers = {"X-Device-Key": "nutribin-dev-key", "X-Device-Id": "ESP32_BIN_01"}
    res = client.post("/api/v1/ingest/v1/readings", json=ingest_payload, headers=headers)
    assert res.status_code == 201
    created = res.json()
    assert created["message"] == "reading_ingested"
    assert created["quality_status"] == "valid"
    assert created["quality_reasons"] == []

    latest_reading = client.get("/api/v1/readings/latest")
    assert latest_reading.status_code == 200
    latest_reading_payload = latest_reading.json()
    assert latest_reading_payload["device_id"] == "ESP32_BIN_01"
    assert latest_reading_payload["quality_status"] == "valid"

    latest_prediction = client.get("/api/v1/predictions/latest")
    assert latest_prediction.status_code == 200
    pred_payload = latest_prediction.json()
    assert pred_payload["reading_id"] == created["reading_id"]
    assert pred_payload["model_version"] == "iforest_v1"


def test_ingest_out_of_range_is_stored_as_invalid() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    ingest_payload = {
        "device_id": "ESP32_BIN_01",
        "device_timestamp": "2026-03-31T10:30:35Z",
        "temperature_c": 120.0,
        "moisture_pct": 54.2,
        "gas_ppm": 712.5,
    }
    headers = {"X-Device-Key": "nutribin-dev-key"}
    res = client.post("/api/v1/ingest/v1/readings", json=ingest_payload, headers=headers)
    assert res.status_code == 201
    payload = res.json()
    assert payload["quality_status"] == "invalid"
    assert "temperature_out_of_range" in payload["quality_reasons"]


def test_ingest_header_device_mismatch() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    ingest_payload = {
        "device_id": "ESP32_BIN_01",
        "device_timestamp": "2026-03-31T10:25:35Z",
        "temperature_c": 38.4,
        "moisture_pct": 54.2,
        "gas_ppm": 712.5,
    }
    headers = {"X-Device-Key": "nutribin-dev-key", "X-Device-Id": "WRONG_ID"}
    res = client.post("/api/v1/ingest/v1/readings", json=ingest_payload, headers=headers)
    assert res.status_code == 400
    payload = res.json()
    assert payload["error_code"] == "DEVICE_ID_MISMATCH"


def test_ingest_rate_limit() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)
    headers = {"X-Device-Key": "nutribin-dev-key"}

    first_payload = {
        "device_id": "ESP32_BIN_01",
        "device_timestamp": "2026-03-31T10:25:35Z",
        "temperature_c": 38.4,
        "moisture_pct": 54.2,
        "gas_ppm": 712.5,
    }
    second_payload = {
        "device_id": "ESP32_BIN_01",
        "device_timestamp": "2026-03-31T10:25:36Z",
        "temperature_c": 39.0,
        "moisture_pct": 53.0,
        "gas_ppm": 720.0,
    }

    first = client.post("/api/v1/ingest/v1/readings", json=first_payload, headers=headers)
    assert first.status_code == 201
    second = client.post("/api/v1/ingest/v1/readings", json=second_payload, headers=headers)
    assert second.status_code == 429


def test_ingest_passes_stage_into_time_model(monkeypatch) -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)
    captured_stage_labels: list[str] = []
    stage_sequence = ["ACTIVE", "CURING"]

    def fake_stage_model(current_data, batch_start_time):
        label = stage_sequence.pop(0)
        return {"stage_label": label, "stage_confidence": "HIGH"}

    monkeypatch.setattr("app.api.v1.routes_ingest.predict_stage", fake_stage_model)

    def fake_time_model(current_data, batch_start_time, device_internal_id, db_session=None):
        captured_stage_labels.append(str(current_data.get("stage_label")))
        return {
            "time_remaining_hours": 12.0 if current_data.get("stage_label") == "ACTIVE" else 48.0,
            "prediction_confidence": "MEDIUM",
            "prediction_source": "RULE",
            "insight": "ok",
            "prediction_basis": "test",
        }

    monkeypatch.setattr("app.api.v1.routes_ingest.predict_time_remaining", fake_time_model)

    start_batch = client.post("/api/v1/batches/start", json={"device_id": settings.DEFAULT_DEVICE_ID})
    assert start_batch.status_code == 201

    res = client.post(
        "/api/v1/ingest/v1/readings",
        json={
            "device_id": settings.DEFAULT_DEVICE_ID,
            "device_timestamp": "2026-04-04T12:00:00Z",
            "temperature_c": 45.0,
            "moisture_pct": 55.0,
            "gas_ppm": 300.0,
        },
        headers={"X-Device-Key": settings.DEFAULT_DEVICE_API_KEY},
    )
    assert res.status_code == 201

    _set_readings_old_for_rate_limit()
    res2 = client.post(
        "/api/v1/ingest/v1/readings",
        json={
            "device_id": settings.DEFAULT_DEVICE_ID,
            "device_timestamp": "2026-04-04T12:01:00Z",
            "temperature_c": 45.0,
            "moisture_pct": 55.0,
            "gas_ppm": 300.0,
        },
        headers={"X-Device-Key": settings.DEFAULT_DEVICE_API_KEY},
    )
    assert res2.status_code == 201
    assert captured_stage_labels == ["ACTIVE", "CURING"]

    db = SessionLocal()
    try:
        preds = db.query(ModelPrediction).order_by(ModelPrediction.id.asc()).all()
        assert len(preds) == 2
        assert preds[0].time_remaining_hours == 12.0
        assert preds[1].time_remaining_hours == 48.0
    finally:
        db.close()


def test_gas_thresholds_anomaly_severity_and_quality() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)
    headers = {"X-Device-Key": settings.DEFAULT_DEVICE_API_KEY}

    medium = client.post(
        "/api/v1/ingest/v1/readings",
        json={
            "device_id": settings.DEFAULT_DEVICE_ID,
            "device_timestamp": "2026-04-04T12:00:00Z",
            "temperature_c": 45.0,
            "moisture_pct": 55.0,
            "gas_ppm": 1500.0,
        },
        headers=headers,
    )
    assert medium.status_code == 201
    medium_quality = medium.json()
    assert medium_quality["quality_status"] == "valid"
    medium_pred = client.get("/api/v1/predictions/latest")
    assert medium_pred.status_code == 200
    assert medium_pred.json()["anomaly_label"] == "anomaly"
    assert 0.6 <= medium_pred.json()["anomaly_score"] <= 0.75

    _set_readings_old_for_rate_limit()
    high = client.post(
        "/api/v1/ingest/v1/readings",
        json={
            "device_id": settings.DEFAULT_DEVICE_ID,
            "device_timestamp": "2026-04-04T12:01:00Z",
            "temperature_c": 45.0,
            "moisture_pct": 55.0,
            "gas_ppm": 2500.0,
        },
        headers=headers,
    )
    assert high.status_code == 201
    high_pred = client.get("/api/v1/predictions/latest")
    assert high_pred.status_code == 200
    assert high_pred.json()["anomaly_label"] == "anomaly"
    assert 0.85 <= high_pred.json()["anomaly_score"] <= 1.0

    _set_readings_old_for_rate_limit()
    invalid = client.post(
        "/api/v1/ingest/v1/readings",
        json={
            "device_id": settings.DEFAULT_DEVICE_ID,
            "device_timestamp": "2026-04-04T12:02:00Z",
            "temperature_c": 45.0,
            "moisture_pct": 55.0,
            "gas_ppm": 11000.0,
        },
        headers=headers,
    )
    assert invalid.status_code == 201
    invalid_payload = invalid.json()
    assert invalid_payload["quality_status"] == "invalid"
    assert "gas_out_of_range" in invalid_payload["quality_reasons"]


def test_latest_reading_allows_null_device_timestamp() -> None:
    init_db()
    _reset_runtime_tables()
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.device_id == settings.DEFAULT_DEVICE_ID).first()
        assert device is not None
        db.add(
            SensorReading(
                device_id=device.id,
                batch_id=None,
                server_timestamp=datetime(2026, 4, 4, 12, 30, tzinfo=timezone.utc),
                device_timestamp=None,
                temperature_c=40.0,
                moisture_pct=50.0,
                gas_ppm=300.0,
                quality_status="valid",
                quality_reasons=[],
            )
        )
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    res = client.get("/api/v1/readings/latest")
    assert res.status_code == 200
    assert res.json()["device_timestamp"] is None
