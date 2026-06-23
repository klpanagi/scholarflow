from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


class ExecutionEvent(BaseModel):
    event_id: int
    execution_id: UUID
    event_type: str = Field(..., min_length=1, max_length=50)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict = Field(default_factory=dict)


class WorkflowEventResponse(BaseModel):
    id: UUID
    execution_id: UUID
    event_type: str
    event_id: int
    timestamp: datetime
    data: dict

    class Config:
        from_attributes = True


class WorkflowSnapshotResponse(BaseModel):
    execution_id: UUID
    events: list[WorkflowEventResponse]
    last_event_id: int
