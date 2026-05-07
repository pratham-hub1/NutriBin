from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_api_key
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


def _count_alerts(alert_type: str, device_internal_id: int) -> int:
    db = SessionLocal()
    try:
        return db.query(Alert).filter(Alert.device_id == device_internal_id, Alert.type == alert_type).count()
    finally:
        db.close()


def _get_default_device_id() -> int:
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.device_id == settings.DEFAULT_DEVICE_ID).first()
        assert device is not None
        return device.id
    finally:
        db.close()


def _ensure_second_device() -> Device:
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.device_id == "ESP32_BIN_02").first()
        if device:
            return device
        device = Device(
            device_id="ESP32_BIN_02",
            name="NutriBin Device 2",
            api_key_hash=hash_api_key("nutribin-dev-key-2"),
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return device
    finally:
        db.close()


def test_alert_created_first_time(monkeypatch) -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.v1.routes_ingest.InferenceService.run",
        lambda current_data, previous_data=None: {
            "anomaly_score": 0.0,
            "anomaly_label": "normal",
            "stage_label": None,
            "stage_confidence": None,
            "time_remaining_hours": None,
            "model_version": "iforest_v1",
        },
    )

    res = client.post(
        "/api/v1/ingest/v1/readings",
        json={
            "device_id": settings.DEFAULT_DEVICE_ID,
            "device_timestamp": "2026-04-04T12:00:00Z",
            "temperature_c": 65.0,
            "moisture_pct": 55.0,
            "gas_ppm": 300.0,
        },
        headers={"X-Device-Key": settings.DEFAULT_DEVICE_API_KEY},
    )
    assert res.status_code == 201
    device_id = _get_default_device_id()
    assert _count_alerts("TEMP_HIGH", device_id) == 1
    db = SessionLocal()
    try:
        latest = db.query(Alert).filter(Alert.device_id == device_id, Alert.type == "TEMP_HIGH").first()
        assert latest is not None
        assert latest.device_id == device_id
    finally:
        db.close()


def test_alert_dedup_skips_within_cooldown(monkeypatch) -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.v1.routes_ingest.InferenceService.run",
        lambda current_data, previous_data=None: {
            "anomaly_score": 0.0,
            "anomaly_label": "normal",
            "stage_label": None,
            "stage_confidence": None,
            "time_remaining_hours": None,
            "model_version": "iforest_v1",
        },
    )

    payload = {
        "device_id": settings.DEFAULT_DEVICE_ID,
        "device_timestamp": "2026-04-04T12:00:00Z",
        "temperature_c": 65.0,
        "moisture_pct": 55.0,
        "gas_ppm": 300.0,
    }
    headers = {"X-Device-Key": settings.DEFAULT_DEVICE_API_KEY}
    first = client.post("/api/v1/ingest/v1/readings", json=payload, headers=headers)
    assert first.status_code == 201

    _set_readings_old_for_rate_limit()
    second = client.post("/api/v1/ingest/v1/readings", json=payload, headers=headers)
    assert second.status_code == 201

    assert _count_alerts("TEMP_HIGH", _get_default_device_id()) == 1


def test_different_type_creates_alert_within_cooldown(monkeypatch) -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.v1.routes_ingest.InferenceService.run",
        lambda current_data, previous_data=None: {
            "anomaly_score": 0.0,
            "anomaly_label": "normal",
            "stage_label": None,
            "stage_confidence": None,
            "time_remaining_hours": None,
            "model_version": "iforest_v1",
        },
    )

    headers = {"X-Device-Key": settings.DEFAULT_DEVICE_API_KEY}
    first = client.post(
        "/api/v1/ingest/v1/readings",
        json={
            "device_id": settings.DEFAULT_DEVICE_ID,
            "device_timestamp": "2026-04-04T12:00:00Z",
            "temperature_c": 65.0,
            "moisture_pct": 55.0,
            "gas_ppm": 300.0,
        },
        headers=headers,
    )
    assert first.status_code == 201

    _set_readings_old_for_rate_limit()
    second = client.post(
        "/api/v1/ingest/v1/readings",
        json={
            "device_id": settings.DEFAULT_DEVICE_ID,
            "device_timestamp": "2026-04-04T12:01:00Z",
            "temperature_c": 45.0,
            "moisture_pct": 55.0,
            "gas_ppm": 700.0,
        },
        headers=headers,
    )
    assert second.status_code == 201

    device_id = _get_default_device_id()
    assert _count_alerts("TEMP_HIGH", device_id) == 1
    assert _count_alerts("GAS_HIGH", device_id) == 1


def test_same_type_different_device_creates_alert(monkeypatch) -> None:
    init_db()
    _reset_runtime_tables()
    second_device = _ensure_second_device()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.api.v1.routes_ingest.InferenceService.run",
        lambda current_data, previous_data=None: {
            "anomaly_score": 0.0,
            "anomaly_label": "normal",
            "stage_label": None,
            "stage_confidence": None,
            "time_remaining_hours": None,
            "model_version": "iforest_v1",
        },
    )

    payload_1 = {
        "device_id": settings.DEFAULT_DEVICE_ID,
        "device_timestamp": "2026-04-04T12:00:00Z",
        "temperature_c": 65.0,
        "moisture_pct": 55.0,
        "gas_ppm": 300.0,
    }
    payload_2 = {
        "device_id": "ESP32_BIN_02",
        "device_timestamp": "2026-04-04T12:00:30Z",
        "temperature_c": 65.0,
        "moisture_pct": 55.0,
        "gas_ppm": 300.0,
    }

    res1 = client.post("/api/v1/ingest/v1/readings", json=payload_1, headers={"X-Device-Key": settings.DEFAULT_DEVICE_API_KEY})
    assert res1.status_code == 201

    res2 = client.post("/api/v1/ingest/v1/readings", json=payload_2, headers={"X-Device-Key": "nutribin-dev-key-2"})
    assert res2.status_code == 201

    assert _count_alerts("TEMP_HIGH", _get_default_device_id()) == 1
    assert _count_alerts("TEMP_HIGH", second_device.id) == 1
