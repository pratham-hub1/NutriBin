from datetime import datetime, timezone
from typing import Any


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


def predict_stage(current_data: dict, batch_start_time: datetime | None) -> dict[str, str]:
    """
    Deterministic compost stage predictor using temperature and batch age.
    Never raises and always returns stage_label + stage_confidence.
    """
    try:
        if batch_start_time is None:
            return {"stage_label": "UNKNOWN", "stage_confidence": "LOW"}

        temperature = _to_float(current_data.get("temperature"))
        if temperature is None:
            return {"stage_label": "INITIAL", "stage_confidence": "LOW"}

        now_utc = datetime.now(timezone.utc)
        batch_start_utc = _as_utc(batch_start_time)
        days_since_start = (now_utc - batch_start_utc).total_seconds() / 86400.0

        if temperature < 30 and days_since_start >= 10:
            confidence = "MEDIUM" if temperature >= 28 else "HIGH"
            return {"stage_label": "READY", "stage_confidence": confidence}

        if temperature >= 45 and days_since_start >= 2:
            confidence = "MEDIUM" if temperature <= 47 else "HIGH"
            return {"stage_label": "ACTIVE", "stage_confidence": confidence}

        if 30 <= temperature < 45 and days_since_start >= 5:
            confidence = "MEDIUM" if (temperature < 32 or temperature >= 43) else "HIGH"
            return {"stage_label": "CURING", "stage_confidence": confidence}

        return {"stage_label": "INITIAL", "stage_confidence": "LOW"}
    except Exception:
        return {"stage_label": "INITIAL", "stage_confidence": "LOW"}
