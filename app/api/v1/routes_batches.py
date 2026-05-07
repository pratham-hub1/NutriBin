from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.batches import (
    ActiveBatchResponse,
    BatchHistoryResponse,
    BatchItem,
    CompleteBatchResponse,
    StartBatchRequest,
    StartBatchResponse,
)
from app.services.batch_service import (
    complete_batch,
    get_active_batch_by_device_code,
    get_batch_history_by_device_code,
    get_device_or_none,
    start_batch,
)

router = APIRouter()


@router.post("/start", response_model=StartBatchResponse, status_code=status.HTTP_201_CREATED)
def start_batch_endpoint(payload: StartBatchRequest, db: Session = Depends(get_db)) -> StartBatchResponse:
    try:
        batch = start_batch(db=db, device_code=payload.device_id, start_offset_days=payload.start_offset_days)
    except ValueError as exc:
        code = str(exc)
        if code == "DEVICE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "RESOURCE_NOT_FOUND", "message": "Device not found", "details": {}},
            )
        if code == "ACTIVE_BATCH_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "ACTIVE_BATCH_EXISTS", "message": "Active batch already exists for device", "details": {}},
            )
        raise

    return StartBatchResponse(batch_id=batch.batch_id, start_time=batch.start_time, status=batch.status)


@router.post("/{batch_id}/complete", response_model=CompleteBatchResponse)
def complete_batch_endpoint(batch_id: str, db: Session = Depends(get_db)) -> CompleteBatchResponse:
    try:
        batch = complete_batch(db=db, batch_code=batch_id)
    except ValueError as exc:
        code = str(exc)
        if code == "BATCH_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "RESOURCE_NOT_FOUND", "message": "Batch not found", "details": {}},
            )
        if code == "BATCH_ALREADY_COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "BATCH_ALREADY_COMPLETED", "message": "Batch is already completed", "details": {}},
            )
        raise

    if batch.end_time is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "REQUEST_FAILED", "message": "Batch completion failed", "details": {}},
        )

    return CompleteBatchResponse(batch_id=batch.batch_id, end_time=batch.end_time, status=batch.status)


@router.get("/active", response_model=ActiveBatchResponse)
def get_active_batch_endpoint(device_id: str = Query(...), db: Session = Depends(get_db)) -> ActiveBatchResponse:
    try:
        batch = get_active_batch_by_device_code(db=db, device_code=device_id)
    except ValueError as exc:
        if str(exc) == "DEVICE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "RESOURCE_NOT_FOUND", "message": "Device not found", "details": {}},
            )
        raise

    if batch is None:
        return ActiveBatchResponse(item=None)

    device = get_device_or_none(db, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "RESOURCE_NOT_FOUND", "message": "Device not found", "details": {}},
        )

    return ActiveBatchResponse(
        item=BatchItem(
            batch_id=batch.batch_id,
            device_id=device.device_id,
            start_time=batch.start_time,
            end_time=batch.end_time,
            status=batch.status,
            created_at=batch.created_at,
        )
    )


@router.get("/history", response_model=BatchHistoryResponse)
def get_batch_history_endpoint(
    device_id: str = Query(...),
    limit: int = Query(default=100, ge=1),
    db: Session = Depends(get_db),
) -> BatchHistoryResponse:
    try:
        rows = get_batch_history_by_device_code(db=db, device_code=device_id, limit=limit)
    except ValueError as exc:
        if str(exc) == "DEVICE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "RESOURCE_NOT_FOUND", "message": "Device not found", "details": {}},
            )
        raise

    return BatchHistoryResponse(
        items=[
            BatchItem(
                batch_id=row.batch_id,
                device_id=device_id,
                start_time=row.start_time,
                end_time=row.end_time,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )
