from datetime import datetime, timezone

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": "nutribin-backend",
        "utc_time": datetime.now(timezone.utc).isoformat(),
    }
