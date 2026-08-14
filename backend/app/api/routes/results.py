from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import List, Dict, Any
from shapely.geometry import mapping
from geoalchemy2.shape import to_shape

from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import AnalysisJob, GridCell, HotspotResult, WeatherEvent

router = APIRouter(prefix="/jobs", tags=["results"])

@router.get("/{job_id}/results/grid")
async def get_grid_results(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns the H3 hexagonal grid cells and their calculated zonal damage scores for the specified job.
    Formatted as GeoJSON FeatureCollection.
    """
    stmt = select(GridCell).where(GridCell.job_id == job_id)
    result = await db.execute(stmt)
    cells = result.scalars().all()
    
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
async def get_hotspot_results(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns the Getis-Ord G* hotspot analysis results for the specified job.
    Formatted as GeoJSON FeatureCollection.
    """
    stmt = select(HotspotResult).where(HotspotResult.job_id == job_id)
    result = await db.execute(stmt)
    hotspots = result.scalars().all()
    
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
async def get_results_summary(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns high-level statistical summary of the analysis results.
    """
    # 1. Fetch Job
    job_stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    # 2. Fetch Grid Cells
    grid_stmt = select(GridCell).where(GridCell.job_id == job_id)
    grid_res = await db.execute(grid_stmt)
    cells = grid_res.scalars().all()
    
    # 3. Fetch Hotspots
    hs_stmt = select(HotspotResult).where(HotspotResult.job_id == job_id)
    hs_res = await db.execute(hs_stmt)
    hotspots = hs_res.scalars().all()
    
    # 4. Fetch Weather
    weather_stmt = select(WeatherEvent).where(WeatherEvent.job_id == job_id).order_by(WeatherEvent.id.desc())
    weather_res = await db.execute(weather_stmt)
    weather = weather_res.scalar_one_or_none()
    
    scores = [c.damage_score for c in cells]
    mean_score = sum(scores) / len(scores) if scores else 0.0
    
    # Distribution
    distribution = {"Yok": 0, "Hafif": 0, "Orta": 0, "Ağır": 0}
    for c in cells:
        cls = c.damage_class or "Yok"
        distribution[cls] = distribution.get(cls, 0) + 1
        
    hotspot_count = sum(1 for h in hotspots if "Hotspot" in (h.classification or ""))
    coldspot_count = sum(1 for h in hotspots if "Coldspot" in (h.classification or ""))
    
    return {
        "job_id": str(job_id),
        "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
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
