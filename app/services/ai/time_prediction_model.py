from datetime import datetime, timezone
import logging
from math import isfinite
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import SensorReading

logger = logging.getLogger(__name__)


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _clamp_hours(value: float) -> float:
    return max(0.0, min(240.0, value))


def _build_insight(temperature: float | None, moisture: float | None, slope: float | None, stage_label: str) -> str:
    if temperature is not None and temperature > 60:
        return "High temperature indicates rapid decomposition"
    if moisture is not None and moisture > 65:
        return "High moisture may be slowing oxygen flow and decomposition"
    if slope is not None and slope < 0 and slope >= -0.5:
        return "Cooling rate is slow, compost maturity may be delayed"
    if stage_label == "CURING":
        return "Compost is stabilizing and nearing readiness"
    return "Composting process is progressing under stable conditions"


def try_ml_prediction(
    current_data: dict,
    batch_start_time: datetime | None,
    device_internal_id: int,
    db_session: Session | None,
) -> dict[str, Any] | None:
    return None


def predict_time_remaining(
    current_data: dict,
    batch_start_time: datetime | None,
    device_internal_id: int,
    db_session: Session | None = None,
) -> dict[str, Any]:
    try:
        if batch_start_time is None:
            return {
                "time_remaining_hours": None,
                "prediction_confidence": "LOW",
                "prediction_source": "RULE",
                "insight": "No active batch. Start a batch to enable lifecycle tracking",
                "prediction_basis": "Batch context not available",
            }

        now_utc = datetime.now(timezone.utc)
        start_utc = _as_utc(batch_start_time)
        days_since_start = (now_utc - start_utc).total_seconds() / 86400.0

        ml_result = try_ml_prediction(
            current_data=current_data,
            batch_start_time=batch_start_time,
            device_internal_id=device_internal_id,
            db_session=db_session,
        )
        if ml_result is not None:
            return ml_result

        temperature = _to_float(current_data.get("temperature"))
        moisture = _to_float(current_data.get("moisture"))
        stage_raw = current_data.get("stage_label")
        stage_label = str(stage_raw or "UNKNOWN")
        if stage_raw is None:
            logger.warning("Time model fallback triggered due to missing stage_label")
        slope: float | None = None
        missing_temp = temperature is None
        missing_moisture = moisture is None
        heuristic_only = missing_temp or missing_moisture
        if missing_temp:
            logger.warning("Time model fallback triggered due to missing temperature")
        if missing_moisture:
            logger.warning("Time model fallback triggered due to missing moisture")

        if not heuristic_only and temperature is not None and temperature < 30 and days_since_start >= 10:
            return {
                "time_remaining_hours": 0.0,
                "prediction_confidence": "HIGH",
                "prediction_source": "RULE",
                "insight": _build_insight(temperature, moisture, slope, stage_label),
                "prediction_basis": "Compost has reached readiness conditions",
            }

        slope_prediction_used = False
        if not heuristic_only and db_session is not None and temperature is not None:
            rows = (
                db_session.query(SensorReading)
                .filter(SensorReading.device_id == device_internal_id)
                .order_by(desc(SensorReading.server_timestamp))
                .limit(5)
                .all()
            )
            if len(rows) >= 5:
                ordered = sorted(rows, key=lambda r: _as_utc(r.server_timestamp))
                oldest = ordered[0]
                newest = ordered[-1]
                span_hours = (_as_utc(newest.server_timestamp) - _as_utc(oldest.server_timestamp)).total_seconds() / 3600.0
                oldest_temp = _to_float(oldest.temperature_c)
                if span_hours >= 1.0 and oldest_temp is not None:
                    slope = (temperature - oldest_temp) / span_hours
                    if isfinite(slope) and slope < 0:
                        slope_prediction_used = True
                        hours_to_target = _clamp_hours((temperature - 30.0) / abs(slope))
                        factor = 1.0
                        if moisture is not None and moisture > 65:
                            factor *= 1.2
                        if stage_label == "ACTIVE" and temperature < 45:
                            factor *= 1.15
                        if 50 <= temperature <= 60 and moisture is not None and 40 <= moisture <= 60:
                            factor *= 0.9
                        hours_to_target = _clamp_hours(hours_to_target * factor)
                        return {
                            "time_remaining_hours": float(hours_to_target),
                            "prediction_confidence": "HIGH",
                            "prediction_source": "RULE",
                            "insight": _build_insight(temperature, moisture, slope, stage_label),
                            "prediction_basis": "Based on temperature cooling trend over recent readings",
                        }

        if heuristic_only:
            logger.warning("Time model fallback triggered to heuristic-only path")

        base_remaining_days = max(0.0, 10.0 - days_since_start)
        if moisture is not None:
            if moisture > 70:
                base_remaining_days *= 1.2
            elif moisture < 40:
                base_remaining_days *= 1.1

        predicted_hours = _clamp_hours(base_remaining_days * 24.0)
        factor = 1.0
        if moisture is not None and moisture > 65:
            factor *= 1.2
        if stage_label == "ACTIVE" and temperature is not None and temperature < 45:
            factor *= 1.15
        if temperature is not None and 50 <= temperature <= 60 and moisture is not None and 40 <= moisture <= 60:
            factor *= 0.9
        predicted_hours = _clamp_hours(predicted_hours * factor)

        return {
            "time_remaining_hours": float(predicted_hours),
            "prediction_confidence": "LOW" if temperature is None else "MEDIUM",
            "prediction_source": "RULE",
            "insight": _build_insight(temperature, moisture, slope, stage_label),
            "prediction_basis": (
                "Based on temperature cooling trend over recent readings"
                if slope_prediction_used
                else "Estimated using compost lifecycle heuristics and current conditions"
            ),
        }
    except Exception:
        return {
            "time_remaining_hours": None,
            "prediction_confidence": "LOW",
            "prediction_source": "RULE",
            "insight": "Composting process is progressing under stable conditions",
            "prediction_basis": "Derived from current conditions and lifecycle heuristics",
        }
