from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Device
from app.schemas.devices import DeviceOut, DevicesListResponse

router = APIRouter()


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/")
def list_devices(db: Session = Depends(get_db)) -> DevicesListResponse:
    rows = db.query(Device).all()
    now_utc = datetime.now(timezone.utc)
    online_cutoff = now_utc - timedelta(seconds=settings.ONLINE_WINDOW_SECONDS)
    return DevicesListResponse(
        items=[
            DeviceOut(
                device_id=row.device_id,
                name=row.name,
                last_seen_at=row.last_seen_at,
                is_online=bool(row.last_seen_at and _as_utc(row.last_seen_at) >= online_cutoff),
            )
            for row in rows
        ]
    )
