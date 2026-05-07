from datetime import datetime

from pydantic import BaseModel


class LatestPredictionResponse(BaseModel):
    reading_id: int
    batch_id: str | None
    anomaly_score: float | None
    anomaly_label: str | None
    stage_label: str | None
    stage_confidence: str | None
    time_remaining_hours: float | None
    prediction_confidence: str
    prediction_source: str
    insight: str
    prediction_basis: str
    model_version: str
    created_at: datetime


class PredictionHistoryItem(BaseModel):
    prediction_id: int
    reading_id: int
    device_id: str
    batch_id: str | None
    created_at: datetime
    anomaly_label: str | None
    anomaly_score: float | None
    stage_label: str | None
    stage_confidence: str | None
    time_remaining_hours: float | None
    prediction_confidence: str
    prediction_source: str
    insight: str
    prediction_basis: str
    model_version: str


class PredictionHistoryResponse(BaseModel):
    items: list[PredictionHistoryItem]
