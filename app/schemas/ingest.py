from datetime import datetime

from pydantic import BaseModel, Field


class SensorReadingIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    device_timestamp: datetime
    temperature_c: float
    moisture_pct: float
    gas_ppm: float


class IngestReadingResponse(BaseModel):
    message: str
    reading_id: int
    device_id: str
    server_timestamp: datetime
    quality_status: str
    quality_reasons: list[str]
