from typing import Protocol, Optional
import uuid
from app.domain.entities.analysis_job import AnalysisJob, JobStatus

class IJobRepository(Protocol):
    def create(self, job: AnalysisJob) -> AnalysisJob:
        ...

    def get_by_id(self, job_id: uuid.UUID) -> Optional[AnalysisJob]:
        ...

    def update_status(self, job_id: uuid.UUID, status: JobStatus) -> Optional[AnalysisJob]:
        ...
