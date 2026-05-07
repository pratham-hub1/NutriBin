from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_api_key
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.main import app
from app.models import Alert, Batch, Device, ModelPrediction, Recommendation, SensorReading


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


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


def _ensure_device(device_code: str, key: str) -> Device:
    db = SessionLocal()
    try:
        existing = db.query(Device).filter(Device.device_id == device_code).first()
        if existing:
            return existing
        row = Device(device_id=device_code, name=device_code, api_key_hash=hash_api_key(key))
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


def _seed_history_data() -> None:
    db = SessionLocal()
    try:
        device_a = db.query(Device).filter(Device.device_id == settings.DEFAULT_DEVICE_ID).first()
        device_b = db.query(Device).filter(Device.device_id == "ESP32_BIN_02").first()
        assert device_a is not None and device_b is not None

        reading_a1 = SensorReading(
            device_id=device_a.id,
            server_timestamp=_dt("2026-04-04T10:00:00Z"),
            device_timestamp=_dt("2026-04-04T09:59:58Z"),
            temperature_c=40.0,
            moisture_pct=50.0,
            gas_ppm=300.0,
            quality_status="valid",
            quality_reasons=[],
        )
        reading_a2 = SensorReading(
            device_id=device_a.id,
            server_timestamp=_dt("2026-04-04T10:10:00Z"),
            device_timestamp=_dt("2026-04-04T10:09:58Z"),
            temperature_c=41.0,
            moisture_pct=51.0,
            gas_ppm=301.0,
            quality_status="valid",
            quality_reasons=[],
        )
        reading_b1 = SensorReading(
            device_id=device_b.id,
            server_timestamp=_dt("2026-04-04T10:05:00Z"),
            device_timestamp=_dt("2026-04-04T10:04:58Z"),
            temperature_c=42.0,
            moisture_pct=52.0,
            gas_ppm=302.0,
            quality_status="valid",
            quality_reasons=[],
        )
        db.add_all([reading_a1, reading_a2, reading_b1])
        db.flush()

        pred_a1 = ModelPrediction(
            reading_id=reading_a1.id,
            anomaly_score=0.0,
            anomaly_label="normal",
            stage_label=None,
            stage_confidence=None,
            time_remaining_hours=None,
            model_version="iforest_v1",
            created_at=_dt("2026-04-04T10:00:05Z"),
        )
        pred_a2 = ModelPrediction(
            reading_id=reading_a2.id,
            anomaly_score=1.0,
            anomaly_label="anomaly",
            stage_label=None,
            stage_confidence=None,
            time_remaining_hours=None,
            model_version="iforest_v1",
            created_at=_dt("2026-04-04T10:10:05Z"),
        )
        pred_b1 = ModelPrediction(
            reading_id=reading_b1.id,
            anomaly_score=0.0,
            anomaly_label="normal",
            stage_label=None,
            stage_confidence=None,
            time_remaining_hours=None,
            model_version="iforest_v1",
            created_at=_dt("2026-04-04T10:05:05Z"),
        )
        db.add_all([pred_a1, pred_a2, pred_b1])
        db.commit()
    finally:
        db.close()


def test_history_endpoints_empty_items() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    r1 = client.get("/api/v1/readings/history")
    r2 = client.get("/api/v1/predictions/history")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == {"items": []}
    assert r2.json() == {"items": []}


def test_readings_history_filters_order_and_limit() -> None:
    init_db()
    _reset_runtime_tables()
    _ensure_device("ESP32_BIN_02", "nutribin-dev-key-2")
    _seed_history_data()
    client = TestClient(app)

    res_all = client.get("/api/v1/readings/history?limit=5000")
    assert res_all.status_code == 200
    items = res_all.json()["items"]
    assert len(items) == 3
    assert [row["server_timestamp"] for row in items] == sorted([row["server_timestamp"] for row in items])

    res_device = client.get(f"/api/v1/readings/history?device_id={settings.DEFAULT_DEVICE_ID}")
    assert res_device.status_code == 200
    d_items = res_device.json()["items"]
    assert len(d_items) == 2
    assert all(row["device_id"] == settings.DEFAULT_DEVICE_ID for row in d_items)

    res_time = client.get(
        "/api/v1/readings/history?start_time=2026-04-04T10:05:00Z&end_time=2026-04-04T10:10:00Z"
    )
    assert res_time.status_code == 200
    t_items = res_time.json()["items"]
    assert len(t_items) == 2
    assert t_items[0]["server_timestamp"].startswith("2026-04-04T10:05:00")
    assert t_items[1]["server_timestamp"].startswith("2026-04-04T10:10:00")


def test_predictions_history_filters_and_validation() -> None:
    init_db()
    _reset_runtime_tables()
    _ensure_device("ESP32_BIN_02", "nutribin-dev-key-2")
    _seed_history_data()
    client = TestClient(app)

    res_device = client.get(f"/api/v1/predictions/history?device_id={settings.DEFAULT_DEVICE_ID}")
    assert res_device.status_code == 200
    items = res_device.json()["items"]
    assert len(items) == 2
    assert all(row["device_id"] == settings.DEFAULT_DEVICE_ID for row in items)
    assert [row["created_at"] for row in items] == sorted([row["created_at"] for row in items])

    res_time = client.get(
        "/api/v1/predictions/history?start_time=2026-04-04T10:05:05Z&end_time=2026-04-04T10:10:05Z"
    )
    assert res_time.status_code == 200
    t_items = res_time.json()["items"]
    assert len(t_items) == 2
    assert t_items[0]["created_at"].startswith("2026-04-04T10:05:05")
    assert t_items[1]["created_at"].startswith("2026-04-04T10:10:05")

    bad_limit = client.get("/api/v1/predictions/history?limit=0")
    bad_dt = client.get("/api/v1/readings/history?start_time=not-a-date")
    assert bad_limit.status_code == 422
    assert bad_dt.status_code == 422
