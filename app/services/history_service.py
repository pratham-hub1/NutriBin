from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Batch, Device, ModelPrediction, SensorReading

MAX_HISTORY_LIMIT = 1000


def get_readings_history(
    db: Session,
    device_id: str | None,
    limit: int,
    start_time: datetime | None,
    end_time: datetime | None,
) -> list[dict]:
    """Return ordered reading history with optional device and time filters."""
    effective_limit = min(limit, MAX_HISTORY_LIMIT)

    query = (
        db.query(SensorReading, Device, Batch)
        .join(Device, Device.id == SensorReading.device_id)
        .outerjoin(Batch, Batch.id == SensorReading.batch_id)
    )
    if device_id is not None:
        query = query.filter(Device.device_id == device_id)
    if start_time is not None:
        query = query.filter(SensorReading.server_timestamp >= start_time)
    if end_time is not None:
        query = query.filter(SensorReading.server_timestamp <= end_time)

    rows = (
        query.order_by(SensorReading.server_timestamp.asc(), SensorReading.id.asc())
        .limit(effective_limit)
        .all()
    )
    return [
        {
            "reading_id": reading.id,
            "device_id": device.device_id,
            "batch_id": (batch.batch_id if batch else None),
            "server_timestamp": reading.server_timestamp,
            "device_timestamp": reading.device_timestamp,
            "temperature_c": reading.temperature_c,
            "moisture_pct": reading.moisture_pct,
            "gas_ppm": reading.gas_ppm,
            "quality_status": reading.quality_status,
            "quality_reasons": reading.quality_reasons,
        }
        for reading, device, batch in rows
    ]


def get_predictions_history(
    db: Session,
    device_id: str | None,
    limit: int,
    start_time: datetime | None,
    end_time: datetime | None,
) -> list[dict]:
    """Return ordered prediction history with optional device and time filters."""
    effective_limit = min(limit, MAX_HISTORY_LIMIT)

    query = (
        db.query(ModelPrediction, SensorReading, Device, Batch)
        .join(SensorReading, SensorReading.id == ModelPrediction.reading_id)
        .join(Device, Device.id == SensorReading.device_id)
        .outerjoin(Batch, Batch.id == SensorReading.batch_id)
    )
    if device_id is not None:
        query = query.filter(Device.device_id == device_id)
    if start_time is not None:
        query = query.filter(ModelPrediction.created_at >= start_time)
    if end_time is not None:
        query = query.filter(ModelPrediction.created_at <= end_time)

    rows = (
        query.order_by(ModelPrediction.created_at.asc(), ModelPrediction.id.asc())
        .limit(effective_limit)
        .all()
    )
    return [
        {
            "prediction_id": prediction.id,
            "reading_id": prediction.reading_id,
            "device_id": device.device_id,
            "batch_id": (batch.batch_id if batch else None),
            "created_at": prediction.created_at,
            "anomaly_label": prediction.anomaly_label,
            "anomaly_score": prediction.anomaly_score,
            "stage_label": prediction.stage_label,
            "stage_confidence": prediction.stage_confidence,
            "time_remaining_hours": prediction.time_remaining_hours,
            "prediction_confidence": prediction.prediction_confidence,
            "prediction_source": prediction.prediction_source,
            "insight": prediction.insight,
            "prediction_basis": prediction.prediction_basis,
            "model_version": prediction.model_version,
        }
        for prediction, _, device, batch in rows
    ]
