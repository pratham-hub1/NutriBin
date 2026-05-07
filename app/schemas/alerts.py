from datetime import datetime

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: int
    type: str
    message: str
    severity: str
    status: str
    created_at: datetime


class AlertsListResponse(BaseModel):
    items: list[AlertOut]
