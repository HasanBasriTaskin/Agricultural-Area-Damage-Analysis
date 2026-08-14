import uuid
from typing import Any, Optional
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
    session_factory, job_id: uuid.UUID, status: Optional[str] = None, error_message: str = None, **kwargs
):
    """Directly update job status and other fields using a simple UPDATE."""
    from app.infrastructure.db.models import AnalysisJob

    async with session_factory() as db:
        values = {}
        if status is not None:
            values["status"] = status
        if error_message is not None:
            values["error_message"] = error_message
        
        values.update(kwargs)
        
        if values:
            stmt = sa_update(AnalysisJob).where(AnalysisJob.id == job_id).values(**values)
            await db.execute(stmt)
            await db.commit()
            logger.info(f"Job {job_id} updated: {values}")


async def _run_sar_pipeline_async(job_id: uuid.UUID) -> str:
    from app.infrastructure.db.models import AnalysisJob, AOI as ModelAOI

    # Create fresh DB connection for this event loop
    session_factory, engine = _make_session_factory()

    try:
        # We set sar_status to 'processing'
        await _update_job_status(session_factory, job_id, sar_status="processing")

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

        # 4. Update sar_status to done
        await _update_job_status(session_factory, job_id, sar_status="done")

        return minio_key

    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {e}", exc_info=True)
        try:
            await _update_job_status(session_factory, job_id, status="failed", sar_status="failed", error_message=str(e)[:500])
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
        return {"job_id": job_id_str, "status": "DONE", "result_key": minio_key, "pipeline": "SAR"}
    except Exception as e:
        logger.error(f"Celery task run_sar_pipeline failed for {job_id_str}: {e}", exc_info=True)
        return {"job_id": job_id_str, "status": "FAILED", "error": str(e)[:500], "pipeline": "SAR"}
    finally:
        loop.close()


async def _run_ms_pipeline_async(job_id: uuid.UUID) -> str:
    from app.infrastructure.db.models import AnalysisJob, AOI as ModelAOI
    from app.application.pipelines.ms_pipeline import MsPipelineService

    session_factory, engine = _make_session_factory()
    try:
        await _update_job_status(session_factory, job_id, ms_status="processing")

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

        client = GEESatelliteClient()
        pipeline = MsPipelineService(client)
        minio_key = pipeline.run_pipeline(aoi_wkt, event_date)
        
        # Update ms_status to done
        await _update_job_status(session_factory, job_id, ms_status="done")
        
        return minio_key
    except Exception as e:
        logger.error(f"MS Pipeline failed for job {job_id}: {e}", exc_info=True)
        try:
            await _update_job_status(session_factory, job_id, status="failed", ms_status="failed", error_message=str(e)[:500])
        except Exception as update_err:
            pass
        raise
    finally:
        await engine.dispose()


@celery_app.task(bind=True, name="app.infrastructure.tasks.run_ms_pipeline")
def run_ms_pipeline(self, job_id_str: str) -> dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        minio_key = loop.run_until_complete(_run_ms_pipeline_async(job_id))
        return {"job_id": job_id_str, "status": "DONE", "result_key": minio_key, "pipeline": "MS"}
    except Exception as e:
        logger.error(f"Celery task run_ms_pipeline failed for {job_id_str}: {e}", exc_info=True)
        return {"job_id": job_id_str, "status": "FAILED", "error": str(e)[:500], "pipeline": "MS"}
    finally:
        loop.close()


async def _finalize_job_async(job_id: uuid.UUID, results: list) -> None:
    session_factory, engine = _make_session_factory()
    try:
        # Check if any failed
        failed = [r for r in results if r.get("status") == "FAILED"]
        if failed:
            await _update_job_status(session_factory, job_id, status="failed", error_message="One or more pipelines failed.")
        else:
            await _update_job_status(session_factory, job_id, status="done")
    finally:
        await engine.dispose()


@celery_app.task(bind=True, name="app.infrastructure.tasks.finalize_pipeline")
def finalize_pipeline(self, results: list, job_id_str: str) -> dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_finalize_job_async(job_id, results))
        return {"job_id": job_id_str, "status": "COMPLETED_ALL", "results": results}
    finally:
        loop.close()
