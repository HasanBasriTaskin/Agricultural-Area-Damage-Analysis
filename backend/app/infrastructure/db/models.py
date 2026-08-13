import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import String, DateTime, Float, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from .database import Base

class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

class JobStatusEnum(str, enum.Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PROCESSING_SAR = "processing_sar"
    PROCESSING_MS = "processing_ms"
    VERIFYING_WEATHER = "verifying_weather"
    FUSING = "fusing"
    AGGREGATING = "aggregating"
    DONE = "done"
    FAILED = "failed"

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), default=RoleEnum.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    aois = relationship("AOI", back_populates="owner")
    jobs = relationship("AnalysisJob", back_populates="created_by_user")

class AOI(Base):
    __tablename__ = "aois"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    geometry: Mapped[Any] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    owner = relationship("User", back_populates="aois")
    jobs = relationship("AnalysisJob", back_populates="aoi")

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aoi_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("aois.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[JobStatusEnum] = mapped_column(Enum(JobStatusEnum), default=JobStatusEnum.QUEUED)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    weights: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    aoi = relationship("AOI", back_populates="jobs")
    created_by_user = relationship("User", back_populates="jobs")
    artifacts = relationship("OutputArtifact", back_populates="job")

class ParcelDamageResult(Base):
    __tablename__ = "parcel_damage_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id"))
    geometry: Mapped[Any] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False))
    damage_score: Mapped[float] = mapped_column(Float)
    damage_class: Mapped[str] = mapped_column(String)

class GridCell(Base):
    __tablename__ = "grid_cells"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id"))
    geometry: Mapped[Any] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False))
    damage_score: Mapped[float] = mapped_column(Float)

class HotspotResult(Base):
    __tablename__ = "hotspot_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id"))
    geometry: Mapped[Any] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False))
    intensity: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)

class WeatherEvent(Base):
    __tablename__ = "weather_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id"))
    precipitation_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)

class OutputArtifact(Base):
    __tablename__ = "output_artifacts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id"))
    file_type: Mapped[str] = mapped_column(String)
    minio_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    job = relationship("AnalysisJob", back_populates="artifacts")
