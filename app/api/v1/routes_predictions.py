from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Batch, ModelPrediction, SensorReading
from app.schemas.predictions import LatestPredictionResponse, PredictionHistoryItem, PredictionHistoryResponse
from app.services.history_service import get_predictions_history

router = APIRouter()


@router.get("/latest")
def latest_predictions(db: Session = Depends(get_db)) -> LatestPredictionResponse:
    prediction = db.query(ModelPrediction).order_by(desc(ModelPrediction.created_at)).first()
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "RESOURCE_NOT_FOUND", "message": "No latest prediction found", "details": {}},
        )

    reading = db.query(SensorReading).filter(SensorReading.id == prediction.reading_id).first()
    batch_code: str | None = None
    if reading and reading.batch_id is not None:
        batch = db.query(Batch).filter(Batch.id == reading.batch_id).first()
        batch_code = batch.batch_id if batch else None

    return LatestPredictionResponse(
        reading_id=prediction.reading_id,
        batch_id=batch_code,
        anomaly_score=prediction.anomaly_score,
        anomaly_label=prediction.anomaly_label,
        stage_label=prediction.stage_label,
        stage_confidence=prediction.stage_confidence,
        time_remaining_hours=prediction.time_remaining_hours,
        prediction_confidence=prediction.prediction_confidence,
        prediction_source=prediction.prediction_source,
        insight=prediction.insight,
        prediction_basis=prediction.prediction_basis,
        model_version=prediction.model_version,
        created_at=prediction.created_at,
    )


@router.get("/history", response_model=PredictionHistoryResponse)
def predictions_history(
    device_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PredictionHistoryResponse:
    items = get_predictions_history(
        db=db,
        device_id=device_id,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )
    return PredictionHistoryResponse(items=[PredictionHistoryItem(**item) for item in items])
