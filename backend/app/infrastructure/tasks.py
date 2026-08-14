import uuid
from typing import Any, Optional
import os
import asyncio
import logging
from celery import Celery
from app.infrastructure.external.gee_client import GEESatelliteClient
from app.application.pipelines.sar_pipeline import SarPipelineService
from app.application.pipelines.ms_pipeline import MsPipelineService
from app.application.pipelines.weather_pipeline import WeatherPipelineService
from app.infrastructure.external.openmeteo_client import OpenMeteoClient
from app.application.services.weather_verification_service import WeatherVerificationService
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

        # 4. Record OutputArtifact in DB
        from app.infrastructure.db.models import OutputArtifact
        async with session_factory() as db:
            db.add(OutputArtifact(job_id=job_id, file_type="SAR_TIFF", minio_key=minio_key))
            await db.commit()

        # 5. Update sar_status to done
        await _update_job_status(session_factory, job_id, sar_status="done")

        return minio_key

    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {e}", exc_info=True)
        try:
            await _update_job_status(session_factory, job_id, sar_status="failed")
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
        
        # Record OutputArtifact in DB
        from app.infrastructure.db.models import OutputArtifact
        async with session_factory() as db:
            db.add(OutputArtifact(job_id=job_id, file_type="MS_TIFF", minio_key=minio_key))
            await db.commit()

        # Update ms_status to done
        await _update_job_status(session_factory, job_id, ms_status="done")
        
        return minio_key
    except Exception as e:
        logger.error(f"MS Pipeline failed for job {job_id}: {e}", exc_info=True)
        try:
            await _update_job_status(session_factory, job_id, ms_status="failed")
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


async def _run_weather_pipeline_async(job_id: uuid.UUID) -> dict:
    from app.infrastructure.db.models import AnalysisJob, AOI as ModelAOI, WeatherEvent

    session_factory, engine = _make_session_factory()
    try:
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

        # We set weather_status to 'processing'
        await _update_job_status(session_factory, job_id, weather_status="processing")

        client = OpenMeteoClient()
        verification_service = WeatherVerificationService()
        pipeline = WeatherPipelineService(client, verification_service)
        
        weather_result = await pipeline.run_pipeline(job_id, aoi_wkt, event_date)
        
        # Save to DB
        async with session_factory() as db:
            weather_event = WeatherEvent(
                job_id=job_id,
                precipitation_mm=weather_result.get("precipitation_mm"),
                wind_speed_kmh=weather_result.get("wind_speed_kmh"),
                soil_moisture_m3_m3=weather_result.get("soil_moisture_m3_m3"),
                is_anomaly=weather_result.get("is_anomaly")
            )
            db.add(weather_event)
            await db.commit()
            
        await _update_job_status(session_factory, job_id, weather_status="done")
        return weather_result
    except Exception as e:
        logger.error(f"Weather Pipeline failed for job {job_id}: {e}", exc_info=True)
        try:
            await _update_job_status(session_factory, job_id, weather_status="failed")
        except Exception:
            pass
        raise
    finally:
        await engine.dispose()


@celery_app.task(bind=True, name="app.infrastructure.tasks.run_weather_pipeline")
def run_weather_pipeline(self, job_id_str: str) -> dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_run_weather_pipeline_async(job_id))
        return {"job_id": job_id_str, "status": "DONE", "result": result, "pipeline": "Weather"}
    except Exception as e:
        logger.error(f"Celery task run_weather_pipeline failed for {job_id_str}: {e}", exc_info=True)
        return {"job_id": job_id_str, "status": "FAILED", "error": str(e)[:500], "pipeline": "Weather"}
    finally:
        loop.close()


async def _finalize_job_async(job_id: uuid.UUID, results: list) -> None:
    session_factory, engine = _make_session_factory()
    try:
        # Check if any failed
        failed = [r for r in results if r.get("status") == "FAILED"]
        if failed:
            error_msgs = " | ".join([f"{r.get('pipeline')}: {r.get('error')}" for r in failed])
            await _update_job_status(session_factory, job_id, status="failed", error_message=error_msgs[:500])
            return

        # All successful. Change status to fusing
        await _update_job_status(session_factory, job_id, status="fusing")
        
        # Extract inputs for Fusion
        sar_result = next((r for r in results if r.get("pipeline") == "SAR"), None)
        ms_result = next((r for r in results if r.get("pipeline") == "MS"), None)
        
        sar_tif_path = sar_result.get("result_key") if sar_result else None
        ms_tif_path = ms_result.get("result_key") if ms_result else None

        from sqlalchemy import select
        from app.infrastructure.db.models import AnalysisJob, WeatherEvent
        
        async with session_factory() as db:
            # Get weights
            stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()
            weights = job.weights if job and job.weights else {}
            
            # Get weather event
            stmt = select(WeatherEvent).where(WeatherEvent.job_id == job_id).order_by(WeatherEvent.id.desc())
            result = await db.execute(stmt)
            weather = result.scalar_one_or_none()
            
            precip = weather.precipitation_mm if weather and weather.precipitation_mm else 0.0
            sm = weather.soil_moisture_m3_m3 if weather and weather.soil_moisture_m3_m3 else 0.0
            
        if not sar_tif_path or not ms_tif_path:
            raise ValueError("Missing SAR or MS tif path for fusion")

        # Run Fusion
        from app.application.strategies.weighted_fusion_strategy import WeightedFusionStrategy
        from app.application.services.fusion_service import FusionService
        
        strategy = WeightedFusionStrategy()
        fusion_service = FusionService(strategy)
        
        # Run synchronous fusion logic in a thread to avoid blocking async loop
        import asyncio
        fusion_result = await asyncio.to_thread(
            fusion_service.run_fusion,
            job_id, sar_tif_path, ms_tif_path, precip, sm, weights
        )
        
        logger.info(f"Fusion complete for job {job_id}: {fusion_result}")
        
        # Sprint 6: Aggregation (Grid & Hotspot Analysis)
        await _update_job_status(session_factory, job_id, status="aggregating")
        
        from geoalchemy2.shape import to_shape
        from geoalchemy2.elements import WKTElement
        from app.infrastructure.db.models import AOI, GridCell, HotspotResult, OutputArtifact
        from app.application.services.grid_aggregation_service import GridAggregationService
        from app.application.services.hotspot_service import HotspotService

        # Record Fusion OutputArtifact in DB
        async with session_factory() as db:
            db.add(OutputArtifact(
                job_id=job_id,
                file_type="FUSION_TIFF",
                minio_key=fusion_result.get("minio_key", fusion_result.get("fusion_tif_path"))
            ))
            await db.commit()
        
        # Fetch AOI WKT
        async with session_factory() as db:
            stmt = select(AOI).join(AnalysisJob, AnalysisJob.aoi_id == AOI.id).where(AnalysisJob.id == job_id)
            result = await db.execute(stmt)
            aoi = result.scalar_one_or_none()
            if not aoi:
                raise ValueError(f"AOI not found for job {job_id}")
            aoi_wkt = to_shape(aoi.geometry).wkt

        # 1. Run Grid Aggregation in thread
        grid_service = GridAggregationService()
        grid_cells = await asyncio.to_thread(
            grid_service.aggregate_raster_to_grid,
            aoi_wkt,
            fusion_result["fusion_tif_path"]
        )
        logger.info(f"Grid aggregation generated {len(grid_cells)} cells for job {job_id}")

        # 2. Run Hotspot Analysis in thread
        hotspot_service = HotspotService()
        hotspot_results = await asyncio.to_thread(
            hotspot_service.calculate_getis_ord_g_star,
            grid_cells
        )
        logger.info(f"Hotspot analysis computed for {len(hotspot_results)} cells for job {job_id}")

        # 3. Save Grid Cells & Hotspots to DB
        async with session_factory() as db:
            for gc in grid_cells:
                db_grid = GridCell(
                    job_id=job_id,
                    h3_index=gc["h3_index"],
                    geometry=WKTElement(gc["geometry_wkt"], srid=4326),
                    damage_score=gc["damage_score"],
                    damage_class=gc["damage_class"]
                )
                db.add(db_grid)

            for hs in hotspot_results:
                db_hs = HotspotResult(
                    job_id=job_id,
                    h3_index=hs["h3_index"],
                    geometry=WKTElement(hs["centroid_wkt"], srid=4326),
                    intensity=hs["intensity"],
                    confidence=hs["confidence"],
                    classification=hs["classification"]
                )
                db.add(db_hs)

            await db.commit()

        # Mark job as fully DONE
        await _update_job_status(session_factory, job_id, status="done")
        logger.info(f"Job {job_id} successfully finalized and marked as DONE")
    except Exception as e:
        logger.error(f"Finalization failed for job {job_id}: {e}", exc_info=True)
        await _update_job_status(session_factory, job_id, status="failed", error_message=str(e)[:500])
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
