import uuid
from typing import Any
import os
from celery import Celery
from app.infrastructure.db.database import SessionLocal
from app.infrastructure.repositories.job_repository import SQLJobRepository
from app.infrastructure.external.gee_client import GEESatelliteClient
from app.application.pipelines.sar_pipeline import SarPipelineService
from app.domain.entities.analysis_job import JobStatus
from app.infrastructure.db.models import AOI as ModelAOI
from shapely import wkb

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "damage_analysis",
    broker=redis_url,
    backend=redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,
)

@celery_app.task(bind=True, name="app.infrastructure.tasks.run_sar_pipeline")
def run_sar_pipeline(self, job_id_str: str) -> dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    
    with SessionLocal() as db:
        repo = SQLJobRepository(db)
        
        # 1. Update status to PROCESSING_SAR
        repo.update_status(job_id, JobStatus.PROCESSING_SAR)
        
        try:
            # 2. Get Job and AOI
            job = repo.get_by_id(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
                
            model_aoi = db.query(ModelAOI).filter(ModelAOI.id == job.aoi_id).first()
            if not model_aoi:
                raise ValueError(f"AOI {job.aoi_id} not found")
                
            # geoalchemy2 returns WKBElement, convert to WKT
            geom = wkb.loads(bytes(model_aoi.geometry.data))
            aoi_wkt = geom.wkt
            
            # 3. Run Pipeline
            client = GEESatelliteClient()
            pipeline = SarPipelineService(client)
            minio_key = pipeline.run_pipeline(aoi_wkt, job.event_date)
            
            # 4. Update status to DONE
            repo.update_status(job_id, JobStatus.DONE)
            
            return {"job_id": job_id_str, "status": "DONE", "result_key": minio_key}
            
        except Exception as e:
            repo.update_status(job_id, JobStatus.FAILED)
            raise e
