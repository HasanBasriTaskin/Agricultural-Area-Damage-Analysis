import io
import uuid
from typing import List, Dict, Any, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shapely.geometry import mapping
from geoalchemy2.shape import to_shape

from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import AOI, AnalysisJob, WeatherEvent
from app.infrastructure.repositories.sql_repositories import (
    SQLGridCellRepository,
    SQLHotspotRepository,
    SQLAnalysisJobRepository,
    SQLOutputArtifactRepository,
    SQLAOIRepository
)
from app.infrastructure.external.minio_client import MinioStorageClient
from app.infrastructure.external.openmeteo_client import OpenMeteoClient

router = APIRouter(prefix="/jobs", tags=["results"])

def get_grid_repo(db: AsyncSession = Depends(get_db)) -> SQLGridCellRepository:
    return SQLGridCellRepository(db)

def get_hotspot_repo(db: AsyncSession = Depends(get_db)) -> SQLHotspotRepository:
    return SQLHotspotRepository(db)

def get_job_repo(db: AsyncSession = Depends(get_db)) -> SQLAnalysisJobRepository:
    return SQLAnalysisJobRepository(db)

def get_artifact_repo(db: AsyncSession = Depends(get_db)) -> SQLOutputArtifactRepository:
    return SQLOutputArtifactRepository(db)

def get_aoi_repo(db: AsyncSession = Depends(get_db)) -> SQLAOIRepository:
    return SQLAOIRepository(db)

@router.get("/{job_id}/results/grid")
async def get_grid_results(
    job_id: uuid.UUID,
    grid_repo: SQLGridCellRepository = Depends(get_grid_repo)
):
    """
    Returns the H3 hexagonal grid cells and their calculated zonal damage scores for the specified job.
    Formatted as GeoJSON FeatureCollection.
    """
    cells = await grid_repo.list_by_job(job_id)
    
    features = []
    for cell in cells:
        geom_shape = to_shape(cell.geometry)
        features.append({
            "type": "Feature",
            "geometry": mapping(geom_shape),
            "properties": {
                "id": str(cell.id),
                "h3_index": cell.h3_index,
                "damage_score": cell.damage_score,
                "damage_class": cell.damage_class or "Yok"
            }
        })
        
    return {
        "type": "FeatureCollection",
        "job_id": str(job_id),
        "count": len(features),
        "features": features
    }

@router.get("/{job_id}/results/hotspots")
async def get_hotspot_results(
    job_id: uuid.UUID,
    hotspot_repo: SQLHotspotRepository = Depends(get_hotspot_repo)
):
    """
    Returns the Getis-Ord G* hotspot analysis results for the specified job.
    Formatted as GeoJSON FeatureCollection.
    """
    hotspots = await hotspot_repo.list_by_job(job_id)
    
    features = []
    for hs in hotspots:
        geom_shape = to_shape(hs.geometry)
        features.append({
            "type": "Feature",
            "geometry": mapping(geom_shape),
            "properties": {
                "id": str(hs.id),
                "h3_index": hs.h3_index,
                "intensity_z_score": hs.intensity,
                "confidence_p_value": hs.confidence,
                "classification": hs.classification or "Anlamsız (Nötr)"
            }
        })
        
    return {
        "type": "FeatureCollection",
        "job_id": str(job_id),
        "count": len(features),
        "features": features
    }

@router.get("/{job_id}/results/summary")
async def get_results_summary(
    job_id: uuid.UUID,
    job_repo: SQLAnalysisJobRepository = Depends(get_job_repo),
    grid_repo: SQLGridCellRepository = Depends(get_grid_repo),
    hotspot_repo: SQLHotspotRepository = Depends(get_hotspot_repo),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns high-level statistical summary of the analysis results.
    """
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    cells = await grid_repo.list_by_job(job_id)
    hotspots = await hotspot_repo.list_by_job(job_id)
    
    weather_stmt = select(WeatherEvent).where(WeatherEvent.job_id == job_id).order_by(WeatherEvent.id.desc())
    weather_res = await db.execute(weather_stmt)
    weather = weather_res.scalar_one_or_none()
    
    scores = [c.damage_score for c in cells]
    mean_score = sum(scores) / len(scores) if scores else 0.0
    
    distribution = {"Yok": 0, "Hafif": 0, "Orta": 0, "Ağır": 0}
    for c in cells:
        cls = c.damage_class or "Yok"
        distribution[cls] = distribution.get(cls, 0) + 1
        
    hotspot_count = sum(1 for h in hotspots if "Hotspot" in (h.classification or ""))
    coldspot_count = sum(1 for h in hotspots if "Coldspot" in (h.classification or ""))
    
    return {
        "job_id": str(job_id),
        "status": job.status if isinstance(job.status, str) else str(job.status),
        "total_cells": len(cells),
        "mean_damage_score": round(mean_score, 4),
        "distribution": distribution,
        "hotspot_cells_count": hotspot_count,
        "coldspot_cells_count": coldspot_count,
        "weather": {
            "precipitation_mm": weather.precipitation_mm if weather else 0.0,
            "soil_moisture_m3_m3": weather.soil_moisture_m3_m3 if weather else 0.0,
            "is_anomaly": weather.is_anomaly if weather else False
        } if weather else None
    }

def _to_shapely(geom_input: Any):
    if geom_input is None:
        return None
    if isinstance(geom_input, str):
        import shapely.wkt
        return shapely.wkt.loads(geom_input)
    try:
        from geoalchemy2.shape import to_shape
        return to_shape(geom_input)
    except Exception:
        import shapely.wkt
        return shapely.wkt.loads(str(geom_input))

@router.get("/{job_id}/results/timeseries")
async def get_results_timeseries(
    job_id: uuid.UUID,
    job_repo: SQLAnalysisJobRepository = Depends(get_job_repo),
    aoi_repo: SQLAOIRepository = Depends(get_aoi_repo)
):
    """
    Returns 30-day daily precipitation, soil moisture, and temperature time series for the job location.
    """
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    aoi = await aoi_repo.get_by_id(job.aoi_id)
    if not aoi or not aoi.geometry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AOI geometry not found")

    geom_shape = _to_shapely(aoi.geometry)
    cent = geom_shape.centroid
    ev_date = job.event_date if isinstance(job.event_date, date) else job.event_date.date()

    client = OpenMeteoClient()
    try:
        timeseries = await client.get_30day_timeseries(lat=cent.y, lon=cent.x, event_date=ev_date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch weather time series: {str(e)}")

    return {
        "job_id": str(job_id),
        "event_date": ev_date.strftime("%Y-%m-%d"),
        "centroid": {"lat": cent.y, "lon": cent.x},
        "count": len(timeseries),
        "timeseries": timeseries
    }

@router.get("/{job_id}/layers/bounds")
async def get_layer_bounds(
    job_id: uuid.UUID,
    job_repo: SQLAnalysisJobRepository = Depends(get_job_repo),
    aoi_repo: SQLAOIRepository = Depends(get_aoi_repo)
):
    """
    Returns geographical bounding box [[min_lat, min_lon], [max_lat, max_lon]] for map overlays.
    """
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    aoi = await aoi_repo.get_by_id(job.aoi_id)
    if not aoi or not aoi.geometry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AOI geometry not found")

    geom_shape = _to_shapely(aoi.geometry)
    b = geom_shape.bounds # min_lon, min_lat, max_lon, max_lat
    return {
        "job_id": str(job_id),
        "bounds": [
            [b[1], b[0]], # South-West: [min_lat, min_lon]
            [b[3], b[2]]  # North-East: [max_lat, max_lon]
        ]
    }

@router.get("/{job_id}/artifacts")
async def get_job_artifacts(
    job_id: uuid.UUID,
    artifact_repo: SQLOutputArtifactRepository = Depends(get_artifact_repo)
):
    """
    Returns all output artifacts produced for this job with MinIO presigned download URLs.
    """
    artifacts = await artifact_repo.list_by_job(job_id)
    minio_client = MinioStorageClient()
    
    result = []
    for art in artifacts:
        download_url = None
        try:
            download_url = minio_client.get_presigned_download_url(art.minio_key, expires_seconds=3600)
        except Exception:
            pass

        result.append({
            "id": str(art.id),
            "job_id": str(art.job_id),
            "file_type": art.file_type,
            "minio_key": art.minio_key,
            "download_url": download_url,
            "created_at": art.created_at
        })
        
    return {
        "job_id": str(job_id),
        "count": len(result),
        "artifacts": result
    }
