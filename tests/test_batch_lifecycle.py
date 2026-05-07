from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.main import app
from app.models import Alert, Batch, ModelPrediction, Recommendation, SensorReading


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


def test_batch_start_active_complete_and_history() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    start_res = client.post("/api/v1/batches/start", json={"device_id": settings.DEFAULT_DEVICE_ID})
    assert start_res.status_code == 201
    start_payload = start_res.json()
    batch_code = start_payload["batch_id"]
    assert batch_code.startswith("BATCH_")
    assert start_payload["status"] == "ACTIVE"

    second_start = client.post("/api/v1/batches/start", json={"device_id": settings.DEFAULT_DEVICE_ID})
    assert second_start.status_code == 409

    active_res = client.get(f"/api/v1/batches/active?device_id={settings.DEFAULT_DEVICE_ID}")
    assert active_res.status_code == 200
    assert active_res.json()["item"]["batch_id"] == batch_code

    ingest_res = client.post(
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
    assert ingest_res.status_code == 201

    db = SessionLocal()
    try:
        reading = db.query(SensorReading).order_by(SensorReading.id.desc()).first()
        batch = db.query(Batch).filter(Batch.batch_id == batch_code).first()
        assert reading is not None
        assert batch is not None
        assert reading.batch_id == batch.id
    finally:
        db.close()

    complete_res = client.post(f"/api/v1/batches/{batch_code}/complete")
    assert complete_res.status_code == 200
    complete_payload = complete_res.json()
    assert complete_payload["status"] == "COMPLETED"
    assert complete_payload["batch_id"] == batch_code

    complete_again = client.post(f"/api/v1/batches/{batch_code}/complete")
    assert complete_again.status_code == 400

    active_after = client.get(f"/api/v1/batches/active?device_id={settings.DEFAULT_DEVICE_ID}")
    assert active_after.status_code == 200
    assert active_after.json() == {"item": None}

    history_res = client.get(f"/api/v1/batches/history?device_id={settings.DEFAULT_DEVICE_ID}&limit=100")
    assert history_res.status_code == 200
    items = history_res.json()["items"]
    assert len(items) == 1
    assert items[0]["batch_id"] == batch_code
    assert items[0]["status"] == "COMPLETED"


def test_ingest_without_active_batch_keeps_batch_null() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    ingest_res = client.post(
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
    assert ingest_res.status_code == 201

    db = SessionLocal()
    try:
        reading = db.query(SensorReading).order_by(SensorReading.id.desc()).first()
        assert reading is not None
        assert reading.batch_id is None
    finally:
        db.close()


def _parse_dt(iso_value: str) -> datetime:
    return datetime.fromisoformat(iso_value.replace("Z", "+00:00"))


def test_batch_start_without_offset_uses_current_time() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)
    before = datetime.now(timezone.utc)

    res = client.post("/api/v1/batches/start", json={"device_id": settings.DEFAULT_DEVICE_ID})
    after = datetime.now(timezone.utc)

    assert res.status_code == 201
    payload = res.json()
    start_time = _parse_dt(payload["start_time"])
    assert before - timedelta(seconds=5) <= start_time <= after + timedelta(seconds=5)


def test_batch_start_with_valid_offset_backdates_start_time() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)
    before = datetime.now(timezone.utc)

    res = client.post(
        "/api/v1/batches/start",
        json={"device_id": settings.DEFAULT_DEVICE_ID, "start_offset_days": 2},
    )
    after = datetime.now(timezone.utc)

    assert res.status_code == 201
    payload = res.json()
    start_time = _parse_dt(payload["start_time"])
    expected_before = before - timedelta(days=2, seconds=5)
    expected_after = after - timedelta(days=2) + timedelta(seconds=5)
    assert expected_before <= start_time <= expected_after


def test_batch_start_with_negative_offset_returns_422() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    res = client.post(
        "/api/v1/batches/start",
        json={"device_id": settings.DEFAULT_DEVICE_ID, "start_offset_days": -1},
    )
    assert res.status_code == 422
    payload = res.json()
    assert payload["error_code"] == "INVALID_PAYLOAD"


def test_batch_start_with_offset_above_cap_returns_422() -> None:
    init_db()
    _reset_runtime_tables()
    client = TestClient(app)

    res = client.post(
        "/api/v1/batches/start",
        json={"device_id": settings.DEFAULT_DEVICE_ID, "start_offset_days": 31},
    )
    assert res.status_code == 422
    payload = res.json()
    assert payload["error_code"] == "INVALID_PAYLOAD"
