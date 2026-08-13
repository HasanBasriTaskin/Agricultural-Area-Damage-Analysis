import uuid
from datetime import datetime
from typing import Optional
from app.domain.entities import AnalysisJobEntity
from app.domain.repositories import AnalysisJobRepository

class CreateJobUseCase:
    def __init__(self, job_repo: AnalysisJobRepository):
        self.job_repo = job_repo

    async def execute(self, aoi_id: uuid.UUID, event_date: datetime, created_by: uuid.UUID, weights_dict: Optional[dict] = None) -> AnalysisJobEntity:
        
        job = AnalysisJobEntity(
            aoi_id=aoi_id,
            event_date=event_date,
            created_by=created_by,
            weights=weights_dict
        )
        return await self.job_repo.create(job)
