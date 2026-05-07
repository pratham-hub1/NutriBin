from datetime import datetime

from pydantic import BaseModel


class RecommendationOut(BaseModel):
    id: int
    type: str
    message: str
    reason: str
    impact: str
    severity: str
    created_at: datetime


class RecommendationsListResponse(BaseModel):
    items: list[RecommendationOut]
