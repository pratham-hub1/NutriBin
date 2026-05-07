from datetime import datetime

from pydantic import BaseModel


class DeviceOut(BaseModel):
    device_id: str
    name: str
    last_seen_at: datetime | None
    is_online: bool


class DevicesListResponse(BaseModel):
    items: list[DeviceOut]
