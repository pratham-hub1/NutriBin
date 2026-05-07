from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Recommendation
from app.schemas.recommendations import RecommendationOut, RecommendationsListResponse

router = APIRouter()


@router.get("/latest")
def latest_recommendations(db: Session = Depends(get_db)) -> RecommendationsListResponse:
    rows = db.query(Recommendation).order_by(desc(Recommendation.created_at)).limit(20).all()
    return RecommendationsListResponse(
        items=[
            RecommendationOut(
                id=row.id,
                type=row.type,
                message=row.message,
                reason=row.reason,
                impact=row.impact,
                severity=row.severity,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )
