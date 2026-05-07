from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LatestReadingResponse(BaseModel):
    device_id: str
    batch_id: str | None
    server_timestamp: datetime
    device_timestamp: Optional[datetime] = None
    temperature_c: float
    moisture_pct: float
    gas_ppm: float
    quality_status: str
    quality_reasons: list[str]


class ReadingHistoryItem(BaseModel):
    reading_id: int
    device_id: str
    batch_id: str | None
    server_timestamp: datetime
    device_timestamp: Optional[datetime] = None
    temperature_c: float
    moisture_pct: float
    gas_ppm: float
    quality_status: str
    quality_reasons: list[str]


class ReadingHistoryResponse(BaseModel):
    items: list[ReadingHistoryItem]
