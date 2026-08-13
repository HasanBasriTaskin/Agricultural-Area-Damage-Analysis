from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from typing import Optional, Any
from app.infrastructure.db.models import JobStatusEnum

# AOI Schemas
class AOICreate(BaseModel):
    name: str = Field(..., min_length=1)
    geometry: str = Field(..., description="WKT format geometry polygon")
    # owner_id will be injected from the current authenticated user in the router

class AOIResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    geometry: Any
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# Job Schemas
class JobCreate(BaseModel):
    aoi_id: uuid.UUID
    event_date: datetime
    weights: Optional[dict] = None

class JobResponse(BaseModel):
    id: uuid.UUID
    aoi_id: uuid.UUID
    created_by: uuid.UUID
    status: JobStatusEnum
    event_date: datetime
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
