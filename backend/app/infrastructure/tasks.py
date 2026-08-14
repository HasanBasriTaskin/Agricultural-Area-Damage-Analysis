import uuid
from typing import Any
import os
import asyncio
import logging
from celery import Celery
from app.infrastructure.external.gee_client import GEESatelliteClient
from app.application.pipelines.sar_pipeline import SarPipelineService
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from shapely import wkb

logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/damage_analysis"
)

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


def _make_session_factory():
    """Create a fresh engine + session factory bound to the CURRENT event loop."""
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return factory, engine


async def _update_job_status(
    session_factory, job_id: uuid.UUID, status: str, error_message: str = None
):
    """Directly update job status using a simple UPDATE."""
    from app.infrastructure.db.models import AnalysisJob

    async with session_factory() as db:
        values = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        stmt = sa_update(AnalysisJob).where(AnalysisJob.id == job_id).values(**values)
        await db.execute(stmt)
        await db.commit()
        logger.info(f"Job {job_id} status updated to {status}")


async def _run_sar_pipeline_async(job_id: uuid.UUID) -> str:
    from app.infrastructure.db.models import AnalysisJob, AOI as ModelAOI

    # Create fresh DB connection for this event loop
    session_factory, engine = _make_session_factory()

    try:
        # 1. Update status to PROCESSING_SAR
        await _update_job_status(session_factory, job_id, "processing_sar")

        # 2. Get Job and AOI data
        async with session_factory() as db:
            stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
            result = await db.execute(stmt)
            db_job = result.scalar_one_or_none()

            if not db_job:
                raise ValueError(f"Job {job_id} not found")

            aoi_id = db_job.aoi_id
            event_date = db_job.event_date

            stmt2 = select(ModelAOI).where(ModelAOI.id == aoi_id)
            result2 = await db.execute(stmt2)
            model_aoi = result2.scalar_one_or_none()

            if not model_aoi:
                raise ValueError(f"AOI {aoi_id} not found")

            geom = wkb.loads(bytes(model_aoi.geometry.data))
            aoi_wkt = geom.wkt

        # 3. Run Pipeline (Sync GEE operations)
        client = GEESatelliteClient()
        pipeline = SarPipelineService(client)
        minio_key = pipeline.run_pipeline(aoi_wkt, event_date)

        # 4. Update status to DONE
        await _update_job_status(session_factory, job_id, "done")

        return minio_key

    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {e}", exc_info=True)
        try:
            await _update_job_status(session_factory, job_id, "failed", str(e)[:500])
        except Exception as update_err:
            logger.error(f"Failed to update job status to failed: {update_err}")
        raise
    finally:
        await engine.dispose()


@celery_app.task(bind=True, name="app.infrastructure.tasks.run_sar_pipeline")
def run_sar_pipeline(self, job_id_str: str) -> dict[str, Any]:
    job_id = uuid.UUID(job_id_str)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        minio_key = loop.run_until_complete(_run_sar_pipeline_async(job_id))
        return {"job_id": job_id_str, "status": "DONE", "result_key": minio_key}
    except Exception as e:
        logger.error(
            f"Celery task run_sar_pipeline failed for {job_id_str}: {e}",
            exc_info=True,
        )
        return {"job_id": job_id_str, "status": "FAILED", "error": str(e)[:500]}
    finally:
        loop.close()
