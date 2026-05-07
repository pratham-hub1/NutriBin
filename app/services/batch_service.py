from datetime import datetime, timedelta, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Batch, Device


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _batch_prefix(now: datetime) -> str:
    return f"BATCH_{now.strftime('%Y%m%d')}_"


def _generate_batch_external_id(db: Session) -> str:
    now_utc = _utc_now()
    prefix = _batch_prefix(now_utc)
    latest_same_day = db.query(Batch).filter(Batch.batch_id.like(f"{prefix}%")).order_by(desc(Batch.batch_id)).first()

    if latest_same_day is None:
        next_counter = 1
    else:
        try:
            next_counter = int(latest_same_day.batch_id.split("_")[-1]) + 1
        except (ValueError, IndexError):
            next_counter = 1

    return f"{prefix}{next_counter:03d}"


def get_device_or_none(db: Session, device_code: str) -> Device | None:
    """Fetch device by external device_id string."""
    return db.query(Device).filter(Device.device_id == device_code).first()


def get_active_batch_for_device(db: Session, device_internal_id: int) -> Batch | None:
    """Return current active batch for a device if present."""
    return db.query(Batch).filter(Batch.device_id == device_internal_id, Batch.status == "ACTIVE").first()


def start_batch(db: Session, device_code: str, start_offset_days: int | None = None) -> Batch:
    """Start a new batch for a device if no active batch exists."""
    device = get_device_or_none(db, device_code)
    if device is None:
        raise ValueError("DEVICE_NOT_FOUND")

    active = get_active_batch_for_device(db, device.id)
    if active is not None:
        raise ValueError("ACTIVE_BATCH_EXISTS")

    now_utc = _utc_now()
    start_time = now_utc - timedelta(days=start_offset_days) if start_offset_days is not None else now_utc

    batch = Batch(
        batch_id=_generate_batch_external_id(db),
        device_id=device.id,
        start_time=start_time,
        status="ACTIVE",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def complete_batch(db: Session, batch_code: str) -> Batch:
    """Complete an active batch by external batch_id."""
    batch = db.query(Batch).filter(Batch.batch_id == batch_code).first()
    if batch is None:
        raise ValueError("BATCH_NOT_FOUND")
    if batch.status == "COMPLETED":
        raise ValueError("BATCH_ALREADY_COMPLETED")

    batch.end_time = _utc_now()
    batch.status = "COMPLETED"
    db.commit()
    db.refresh(batch)
    return batch


def get_active_batch_by_device_code(db: Session, device_code: str) -> Batch | None:
    """Return active batch for a given external device_id."""
    device = get_device_or_none(db, device_code)
    if device is None:
        raise ValueError("DEVICE_NOT_FOUND")
    return get_active_batch_for_device(db, device.id)


def get_batch_history_by_device_code(db: Session, device_code: str, limit: int) -> list[Batch]:
    """Return batch history for a device ordered by most recent start_time."""
    device = get_device_or_none(db, device_code)
    if device is None:
        raise ValueError("DEVICE_NOT_FOUND")
    effective_limit = min(limit, 1000)
    return (
        db.query(Batch)
        .filter(Batch.device_id == device.id)
        .order_by(desc(Batch.start_time), desc(Batch.id))
        .limit(effective_limit)
        .all()
    )
