import uuid
from typing import Any
import os
import asyncio
from celery import Celery
from app.infrastructure.db.database import AsyncSessionLocal
from app.infrastructure.repositories.sql_repositories import SQLAnalysisJobRepository
from app.infrastructure.external.gee_client import GEESatelliteClient
from app.application.pipelines.sar_pipeline import SarPipelineService
from app.infrastructure.db.models import JobStatusEnum
from app.infrastructure.db.models import AOI as ModelAOI
from sqlalchemy import select
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

async def _run_sar_pipeline_async(job_id: uuid.UUID) -> str:
    async with AsyncSessionLocal() as db:
        repo = SQLAnalysisJobRepository(db)
        
        # 1. Update status to PROCESSING_SAR
        await repo.update(job_id, {"status": "processing_sar"})
        
        try:
            # 2. Get Job and AOI
            job = await repo.get_by_id(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
                
            stmt = select(ModelAOI).where(ModelAOI.id == job.aoi_id)
            result = await db.execute(stmt)
            model_aoi = result.scalar_one_or_none()
            
            if not model_aoi:
                raise ValueError(f"AOI {job.aoi_id} not found")
                
            # geoalchemy2 returns WKBElement, convert to WKT
            geom = wkb.loads(bytes(model_aoi.geometry.data))
            aoi_wkt = geom.wkt
            
            # 3. Run Pipeline (Sync call)
            # Since pipeline.run_pipeline is sync, we can just call it, 
            # or ideally run it in a threadpool if it blocks too much. 
            # For MVP, it's fine.
            client = GEESatelliteClient()
            pipeline = SarPipelineService(client)
            minio_key = pipeline.run_pipeline(aoi_wkt, job.event_date)
            
            # 4. Update status to DONE
            await repo.update(job_id, {"status": "done"})
            
            return minio_key
            
        except Exception as e:
            await repo.update(job_id, {"status": "failed", "error_message": str(e)})
            raise e


@celery_app.task(bind=True, name="app.infrastructure.tasks.run_sar_pipeline")
def run_sar_pipeline(self, job_id_str: str) -> dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    
    # Run the async pipeline function in a new event loop
    loop = asyncio.get_event_loop()
    minio_key = loop.run_until_complete(_run_sar_pipeline_async(job_id))
    
    return {"job_id": job_id_str, "status": "DONE", "result_key": minio_key}
