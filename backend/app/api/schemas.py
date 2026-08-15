from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from typing import Optional, Any, List
from app.infrastructure.db.models import JobStatusEnum, RoleEnum

# User & Auth Schemas
class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)

class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    role: Optional[RoleEnum] = RoleEnum.VIEWER

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: RoleEnum
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserUpdateRequest(BaseModel):
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)

# AOI Schemas
class AOICreate(BaseModel):
    name: str = Field(..., min_length=1)
    geometry: str = Field(..., description="WKT format geometry polygon")

class AOIResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    geometry: Any
    created_at: Optional[datetime] = None

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
    aoi_name: Optional[str] = None
    created_by: uuid.UUID
    status: JobStatusEnum
    sar_status: Optional[str] = None
    ms_status: Optional[str] = None
    weather_status: Optional[str] = None
    error_message: Optional[str] = None
    event_date: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
