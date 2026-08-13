from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from enum import Enum
from typing import Optional
from app.domain.value_objects.weight_config import WeightConfig

class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PROCESSING_SAR = "processing_sar"
    PROCESSING_MS = "processing_ms"
    VERIFYING_WEATHER = "verifying_weather"
    FUSING = "fusing"
    AGGREGATING = "aggregating"
    DONE = "done"
    FAILED = "failed"

@dataclass
class AnalysisJob:
    aoi_id: uuid.UUID
    event_date: datetime
    created_by: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: JobStatus = JobStatus.QUEUED
    weights: WeightConfig = field(default_factory=WeightConfig)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
