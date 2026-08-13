import uuid
from typing import Optional
from sqlalchemy.orm import Session
import json

from app.domain.interfaces.job_repository import IJobRepository
from app.domain.entities.analysis_job import AnalysisJob, JobStatus
from app.domain.value_objects.weight_config import WeightConfig
from app.infrastructure.db.models import AnalysisJob as ModelAnalysisJob, JobStatusEnum

class SQLJobRepository(IJobRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_entity(self, model: ModelAnalysisJob) -> AnalysisJob:
        weights = WeightConfig(**model.weights) if model.weights else WeightConfig()
        return AnalysisJob(
            id=model.id,
            aoi_id=model.aoi_id,
            created_by=model.created_by,
            status=JobStatus(model.status.value),
            event_date=model.event_date,
            weights=weights,
            created_at=model.created_at
        )

    def _to_model(self, entity: AnalysisJob) -> ModelAnalysisJob:
        weights_dict = {
            "sar_weight": entity.weights.sar_weight,
            "ndmi_weight": entity.weights.ndmi_weight,
            "ndre_weight": entity.weights.ndre_weight,
            "precipitation_weight": entity.weights.precipitation_weight,
            "soil_moisture_weight": entity.weights.soil_moisture_weight
        }
        return ModelAnalysisJob(
            id=entity.id,
            aoi_id=entity.aoi_id,
            created_by=entity.created_by,
            status=JobStatusEnum(entity.status.value),
            event_date=entity.event_date,
            weights=weights_dict,
            created_at=entity.created_at
        )

    def create(self, job: AnalysisJob) -> AnalysisJob:
        model_job = self._to_model(job)
        self.session.add(model_job)
        self.session.commit()
        self.session.refresh(model_job)
        return self._to_entity(model_job)

    def get_by_id(self, job_id: uuid.UUID) -> Optional[AnalysisJob]:
        model_job = self.session.query(ModelAnalysisJob).filter_by(id=job_id).first()
        if not model_job:
            return None
        return self._to_entity(model_job)

    def update_status(self, job_id: uuid.UUID, status: JobStatus) -> Optional[AnalysisJob]:
        model_job = self.session.query(ModelAnalysisJob).filter_by(id=job_id).first()
        if not model_job:
            return None
        model_job.status = JobStatusEnum(status.value)
        self.session.commit()
        self.session.refresh(model_job)
        return self._to_entity(model_job)
