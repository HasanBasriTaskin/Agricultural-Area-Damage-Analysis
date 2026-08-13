import uuid
from datetime import datetime
from typing import Optional
from app.domain.entities.analysis_job import AnalysisJob
from app.domain.interfaces.job_repository import IJobRepository
from app.domain.value_objects.weight_config import WeightConfig

class CreateJobUseCase:
    def __init__(self, job_repo: IJobRepository):
        self.job_repo = job_repo

    def execute(self, aoi_id: uuid.UUID, event_date: datetime, created_by: uuid.UUID, weights_dict: Optional[dict] = None) -> AnalysisJob:
        weights = WeightConfig(**weights_dict) if weights_dict else WeightConfig()
        weights.validate()
        
        job = AnalysisJob(
            aoi_id=aoi_id,
            event_date=event_date,
            created_by=created_by,
            weights=weights
        )
        return self.job_repo.create(job)
