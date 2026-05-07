from fastapi import APIRouter

from app.api.v1 import (
    routes_alerts,
    routes_batches,
    routes_devices,
    routes_health,
    routes_ingest,
    routes_predictions,
    routes_readings,
    routes_recommendations,
)


api_router = APIRouter()
api_router.include_router(routes_health.router, tags=["health"])
api_router.include_router(routes_ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(routes_devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(routes_readings.router, prefix="/readings", tags=["readings"])
api_router.include_router(routes_predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(routes_recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(routes_alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(routes_batches.router, prefix="/batches", tags=["batches"])
