from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_api_key
from app.db.session import get_db
from app.models import Alert, Device, ModelPrediction, Recommendation, SensorReading
from app.schemas.ingest import IngestReadingResponse, SensorReadingIn
from app.services.ai.inference_service import InferenceService
from app.services.ai.stage_model import predict_stage
from app.services.ai.time_prediction_model import predict_time_remaining
from app.services.batch_service import get_active_batch_for_device
from app.services.rules.alert_service import should_create_alert
from app.services.rules.rule_engine import generate_recommendations
from app.services.validation_service import ValidationService

router = APIRouter()
logger = logging.getLogger(__name__)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("/v1/readings", response_model=IngestReadingResponse, status_code=status.HTTP_201_CREATED)
def ingest_reading(
    payload: SensorReadingIn,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
) -> IngestReadingResponse:
    if not x_device_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized device credentials")

    if x_device_id and x_device_id != payload.device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "DEVICE_ID_MISMATCH",
                "message": "X-Device-Id does not match payload device_id",
                "details": {},
            },
        )

    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not registered")

    if not verify_api_key(x_device_key, device.api_key_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized device credentials")

    latest = (
        db.query(SensorReading)
        .filter(SensorReading.device_id == device.id)
        .order_by(desc(SensorReading.server_timestamp))
        .first()
    )
    if latest:
        cutoff = _as_utc(latest.server_timestamp) + timedelta(seconds=settings.INGEST_RATE_LIMIT_SECONDS)
        now_utc = datetime.now(timezone.utc)
        if now_utc < cutoff:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Ingestion rate limit exceeded",
            )
    else:
        now_utc = datetime.now(timezone.utc)

    quality_status, quality_reasons = ValidationService.classify_reading(
        temperature_c=payload.temperature_c,
        moisture_pct=payload.moisture_pct,
        gas_ppm=payload.gas_ppm,
    )

    device_ts = payload.device_timestamp
    if device_ts.tzinfo is None:
        device_ts = device_ts.replace(tzinfo=timezone.utc)
    active_batch = get_active_batch_for_device(db, device.id)

    reading = SensorReading(
        device_id=device.id,
        batch_id=(active_batch.id if active_batch else None),
        server_timestamp=now_utc,
        device_timestamp=device_ts,
        temperature_c=payload.temperature_c,
        moisture_pct=payload.moisture_pct,
        gas_ppm=payload.gas_ppm,
        quality_status=quality_status,
        quality_reasons=quality_reasons,
    )
    db.add(reading)
    db.flush()

    model_current_data = {
        "temperature": payload.temperature_c,
        "moisture": payload.moisture_pct,
        "gas": payload.gas_ppm,
    }

    inference_result = InferenceService.run(
        model_current_data,
        previous_data=(
            {
                "temperature": latest.temperature_c,
                "moisture": latest.moisture_pct,
                "gas": latest.gas_ppm,
            }
            if latest
            else None
        ),
    )
    stage_result = predict_stage(
        current_data=model_current_data,
        batch_start_time=(active_batch.start_time if active_batch else None),
    )
    stage_label = stage_result.get("stage_label") if isinstance(stage_result, dict) else None
    stage_confidence = stage_result.get("stage_confidence") if isinstance(stage_result, dict) else None
    if stage_label is None:
        stage_label = "UNKNOWN"
        logger.warning("Missing stage_label from stage model; defaulting to UNKNOWN")
    if stage_confidence is None:
        stage_confidence = "LOW"
        logger.warning("Missing stage_confidence from stage model; defaulting to LOW")
    model_current_data["stage_label"] = stage_label

    if "temperature" not in model_current_data or model_current_data.get("temperature") is None:
        logger.warning("Time model fallback triggered due to missing temperature")
    if "moisture" not in model_current_data or model_current_data.get("moisture") is None:
        logger.warning("Time model fallback triggered due to missing moisture")
    logger.debug("Stage passed to time model: %s", stage_label)

    time_result = predict_time_remaining(
        current_data=model_current_data,
        batch_start_time=(active_batch.start_time if active_batch else None),
        device_internal_id=device.id,
        db_session=db,
    )

    prediction = ModelPrediction(
        reading_id=reading.id,
        anomaly_score=inference_result["anomaly_score"],
        anomaly_label=inference_result["anomaly_label"],
        stage_label=stage_label,
        stage_confidence=stage_confidence,
        time_remaining_hours=time_result["time_remaining_hours"],
        prediction_confidence=time_result["prediction_confidence"],
        prediction_source=time_result["prediction_source"],
        insight=time_result["insight"],
        prediction_basis=time_result["prediction_basis"],
        model_version=inference_result["model_version"],
    )
    db.add(prediction)

    recommendations = generate_recommendations(
        current_data={
            "temperature": payload.temperature_c,
            "moisture": payload.moisture_pct,
            "gas": payload.gas_ppm,
        },
        anomaly_status=inference_result["anomaly_label"] or "anomaly",
        reading_id=reading.id,
        stage_label=stage_label,
        time_remaining_hours=time_result["time_remaining_hours"],
    )
    for rec in recommendations:
        db.add(
            Recommendation(
                reading_id=reading.id,
                type=rec["type"],
                message=rec["message"],
                reason=rec["reason"],
                impact=rec["impact"],
                severity=rec["severity"],
            )
        )
        if should_create_alert(device_id=device.id, alert_type=rec["type"], db_session=db):
            db.add(
                Alert(
                    device_id=device.id,
                    reading_id=reading.id,
                    type=rec["type"],
                    message=rec["message"],
                    severity=rec["severity"],
                    status="active",
                )
            )

    device.last_seen_at = now_utc
    db.commit()

    return IngestReadingResponse(
        message="reading_ingested",
        reading_id=reading.id,
        device_id=payload.device_id,
        server_timestamp=now_utc,
        quality_status=quality_status,
        quality_reasons=quality_reasons,
    )
