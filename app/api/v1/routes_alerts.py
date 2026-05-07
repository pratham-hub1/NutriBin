from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Alert
from app.schemas.alerts import AlertOut, AlertsListResponse

router = APIRouter()


@router.get("/latest")
def latest_alerts(db: Session = Depends(get_db)) -> AlertsListResponse:
    rows = db.query(Alert).order_by(desc(Alert.created_at)).limit(20).all()
    return AlertsListResponse(
        items=[
            AlertOut(
                id=row.id,
                type=row.type,
                message=row.message,
                severity=row.severity,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )
