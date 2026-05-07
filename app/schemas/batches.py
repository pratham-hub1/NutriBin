from datetime import datetime

from pydantic import BaseModel, Field


class StartBatchRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    start_offset_days: int | None = Field(default=None, ge=0, le=30)


class StartBatchResponse(BaseModel):
    batch_id: str
    start_time: datetime
    status: str


class CompleteBatchResponse(BaseModel):
    batch_id: str
    end_time: datetime
    status: str


class BatchItem(BaseModel):
    batch_id: str
    device_id: str
    start_time: datetime
    end_time: datetime | None
    status: str
    created_at: datetime


class ActiveBatchResponse(BaseModel):
    item: BatchItem | None


class BatchHistoryResponse(BaseModel):
    items: list[BatchItem]
