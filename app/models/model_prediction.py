from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("sensor_readings.id"), nullable=False, index=True)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=True)
    anomaly_label: Mapped[str] = mapped_column(String(24), nullable=True)
    stage_label: Mapped[str] = mapped_column(String(64), nullable=True)
    stage_confidence: Mapped[str] = mapped_column(String(16), nullable=True)
    time_remaining_hours: Mapped[float] = mapped_column(Float, nullable=True)
    prediction_confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="LOW")
    prediction_source: Mapped[str] = mapped_column(String(16), nullable=False, default="RULE")
    insight: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="Composting process is progressing under stable conditions",
    )
    prediction_basis: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="Derived from current conditions and lifecycle heuristics",
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
