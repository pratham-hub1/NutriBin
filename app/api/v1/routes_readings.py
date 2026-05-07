from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Batch, Device, SensorReading
from app.schemas.readings import LatestReadingResponse, ReadingHistoryItem, ReadingHistoryResponse
from app.services.history_service import get_readings_history

router = APIRouter()


@router.get("/latest")
def latest_reading(db: Session = Depends(get_db)) -> LatestReadingResponse:
    reading = db.query(SensorReading).order_by(desc(SensorReading.server_timestamp)).first()
    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "RESOURCE_NOT_FOUND", "message": "No latest reading found", "details": {}},
        )

    device = db.query(Device).filter(Device.id == reading.device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "RESOURCE_NOT_FOUND", "message": "Device not found for reading", "details": {}},
        )

    batch_code: str | None = None
    if reading.batch_id is not None:
        batch = db.query(Batch).filter(Batch.id == reading.batch_id).first()
        batch_code = batch.batch_id if batch else None

    return LatestReadingResponse(
        device_id=device.device_id,
        batch_id=batch_code,
        server_timestamp=reading.server_timestamp,
        device_timestamp=reading.device_timestamp,
        temperature_c=reading.temperature_c,
        moisture_pct=reading.moisture_pct,
        gas_ppm=reading.gas_ppm,
        quality_status=reading.quality_status,
        quality_reasons=reading.quality_reasons,
    )


@router.get("/history", response_model=ReadingHistoryResponse)
def readings_history(
    device_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ReadingHistoryResponse:
    items = get_readings_history(
        db=db,
        device_id=device_id,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )
    return ReadingHistoryResponse(items=[ReadingHistoryItem(**item) for item in items])
