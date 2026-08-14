import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# Domain Enums (Shared with DB, but redefined or imported here if strictly separated, 
# for now we will just use strings or re-declare them as python enums)
from app.infrastructure.db.models import RoleEnum, JobStatusEnum

class BaseEntity(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    
    class Config:
        from_attributes = True

class UserEntity(BaseEntity):
    email: str
    role: RoleEnum = RoleEnum.VIEWER
    is_active: bool = True
    created_at: Optional[datetime] = None
    # We purposefully exclude hashed_password from domain entity responses usually,
    # but if needed by auth services it can be here or in a separate model.
    hashed_password: str

class AOIEntity(BaseEntity):
    name: str
    owner_id: uuid.UUID
    geometry: Any  # Can be GeoJSON dict or WKT string depending on layer
    created_at: Optional[datetime] = None

class AnalysisJobEntity(BaseEntity):
    aoi_id: uuid.UUID
    created_by: uuid.UUID
    status: str = "queued"
    sar_status: Optional[str] = "queued"
    ms_status: Optional[str] = "queued"
    weather_status: Optional[str] = "queued"
    event_date: datetime
    weights: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ParcelDamageResultEntity(BaseEntity):
    job_id: uuid.UUID
    geometry: Any
    damage_score: float
    damage_class: str

class GridCellEntity(BaseEntity):
    job_id: uuid.UUID
    h3_index: Optional[str] = None
    geometry: Any
    damage_score: float
    damage_class: Optional[str] = None

class HotspotResultEntity(BaseEntity):
    job_id: uuid.UUID
    h3_index: Optional[str] = None
    geometry: Any
    intensity: float
    confidence: float
    classification: Optional[str] = None

class WeatherEventEntity(BaseEntity):
    job_id: uuid.UUID
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    soil_moisture_m3_m3: Optional[float] = None
    is_anomaly: bool = False

class OutputArtifactEntity(BaseEntity):
    job_id: uuid.UUID
    file_type: str
    minio_key: str
    created_at: Optional[datetime] = None
