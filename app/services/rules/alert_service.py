from datetime import datetime, timedelta, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Alert

ALERT_COOLDOWN_MINUTES = 30


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def should_create_alert(device_id: int, alert_type: str, db_session: Session) -> bool:
    latest_alert = (
        db_session.query(Alert)
        .filter(Alert.device_id == device_id, Alert.type == alert_type)
        .order_by(desc(Alert.created_at))
        .first()
    )
    if latest_alert is None:
        return True

    now_utc = datetime.now(timezone.utc)
    cooldown_threshold = now_utc - timedelta(minutes=ALERT_COOLDOWN_MINUTES)
    return _as_utc(latest_alert.created_at) < cooldown_threshold
