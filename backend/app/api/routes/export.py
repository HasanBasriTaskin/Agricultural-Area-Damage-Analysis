import uuid
import json
import os
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import AnalysisJob, AOI, WeatherEvent, OutputArtifact
from app.infrastructure.repositories.sql_repositories import (
    SQLGridCellRepository,
    SQLHotspotRepository,
    SQLAnalysisJobRepository,
    SQLOutputArtifactRepository,
    SQLAOIRepository
)
from app.application.services.export_service import ExportService
from app.application.services.pdf_report_service import PdfReportService

router = APIRouter(prefix="/jobs", tags=["export"])

def get_grid_repo(db: AsyncSession = Depends(get_db)) -> SQLGridCellRepository:
    return SQLGridCellRepository(db)

def get_hotspot_repo(db: AsyncSession = Depends(get_db)) -> SQLHotspotRepository:
    return SQLHotspotRepository(db)

def get_job_repo(db: AsyncSession = Depends(get_db)) -> SQLAnalysisJobRepository:
    return SQLAnalysisJobRepository(db)

def get_aoi_repo(db: AsyncSession = Depends(get_db)) -> SQLAOIRepository:
    return SQLAOIRepository(db)

def get_artifact_repo(db: AsyncSession = Depends(get_db)) -> SQLOutputArtifactRepository:
    return SQLOutputArtifactRepository(db)

@router.get("/{job_id}/export/pdf")
async def export_pdf_report(
    job_id: uuid.UUID,
    job_repo: SQLAnalysisJobRepository = Depends(get_job_repo),
    aoi_repo: SQLAOIRepository = Depends(get_aoi_repo),
    grid_repo: SQLGridCellRepository = Depends(get_grid_repo),
    hotspot_repo: SQLHotspotRepository = Depends(get_hotspot_repo),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates and downloads official PDF Agricultural Damage Assessment Report.
    """
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    aoi = await aoi_repo.get_by_id(job.aoi_id)
    cells = await grid_repo.list_by_job(job_id)
    hotspots = await hotspot_repo.list_by_job(job_id)

    weather_stmt = select(WeatherEvent).where(WeatherEvent.job_id == job_id).order_by(WeatherEvent.id.desc())
    weather_res = await db.execute(weather_stmt)
    weather = weather_res.scalar_one_or_none()

    scores = [float(c.damage_score) for c in cells]
    mean_score = sum(scores) / len(scores) if scores else 0.0

    distribution = {"Yok": 0, "Hafif": 0, "Orta": 0, "Ağır": 0}
    for c in cells:
        cls = c.damage_class or "Yok"
        distribution[cls] = distribution.get(cls, 0) + 1

    hotspot_count = sum(1 for h in hotspots if "Hotspot" in (h.classification or ""))
    coldspot_count = sum(1 for h in hotspots if "Coldspot" in (h.classification or ""))

    summary_data = {
        "total_cells": len(cells),
        "mean_damage_score": mean_score,
        "distribution": distribution,
        "hotspot_cells_count": hotspot_count,
        "coldspot_cells_count": coldspot_count,
        "weather": {
            "precipitation_mm": weather.precipitation_mm if weather else 0.0,
            "soil_moisture_m3_m3": weather.soil_moisture_m3_m3 if weather else 0.0,
            "is_anomaly": weather.is_anomaly if weather else False
        } if weather else None
    }

    # Calculate approx area in ha
    area_ha = 0.0
    if aoi:
        import shapely.wkt
        import math
        try:
            geom = shapely.wkt.loads(aoi.geometry)
            bounds = geom.bounds
            avg_lat = (bounds[1] + bounds[3]) / 2.0
            lat_m = 111132.954 - 559.822 * math.cos(2 * math.radians(avg_lat))
            lng_m = 111412.84 * math.cos(math.radians(avg_lat))
            area_ha = (geom.area * lat_m * lng_m) / 10000.0
        except Exception:
            area_ha = len(cells) * 1.5

    pdf_service = PdfReportService()
    pdf_bytes = pdf_service.generate_damage_report(
        job_id=job_id,
        aoi_name=aoi.name if aoi else "Belirtilmedi",
        aoi_area_ha=area_ha,
        event_date=job.event_date.strftime("%d.%m.%Y") if hasattr(job.event_date, 'strftime') else str(job.event_date),
        summary_data=summary_data,
        weather_data=summary_data["weather"],
        weights=job.weights
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=hasar_tespit_raporu_{job_id}.pdf"}
    )

@router.get("/{job_id}/export/geojson")
async def export_geojson(
    job_id: uuid.UUID,
    grid_repo: SQLGridCellRepository = Depends(get_grid_repo),
    hotspot_repo: SQLHotspotRepository = Depends(get_hotspot_repo)
):
    """
    Exports H3 grid cells and hotspot statistics as a standard GeoJSON file.
    """
    cells = await grid_repo.list_by_job(job_id)
    hotspots = await hotspot_repo.list_by_job(job_id)

    export_service = ExportService()
    geojson_data = export_service.generate_geojson(cells, hotspots)

    return Response(
        content=json.dumps(geojson_data, ensure_ascii=False, indent=2),
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=hasar_grid_{job_id}.geojson"}
    )

@router.get("/{job_id}/export/csv")
async def export_csv(
    job_id: uuid.UUID,
    grid_repo: SQLGridCellRepository = Depends(get_grid_repo),
    hotspot_repo: SQLHotspotRepository = Depends(get_hotspot_repo)
):
    """
    Exports H3 grid cell records and stats as an Excel-compatible CSV file.
    """
    cells = await grid_repo.list_by_job(job_id)
    hotspots = await hotspot_repo.list_by_job(job_id)

    export_service = ExportService()
    csv_str = export_service.generate_csv(cells, hotspots)

    return Response(
        content=csv_str,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=hasar_verileri_{job_id}.csv"}
    )

@router.get("/{job_id}/export/shapefile")
async def export_shapefile(
    job_id: uuid.UUID,
    grid_repo: SQLGridCellRepository = Depends(get_grid_repo),
    hotspot_repo: SQLHotspotRepository = Depends(get_hotspot_repo)
):
    """
    Exports H3 grid cells and attributes as a zipped ESRI Shapefile (.zip).
    """
    cells = await grid_repo.list_by_job(job_id)
    hotspots = await hotspot_repo.list_by_job(job_id)

    if not cells:
        raise HTTPException(status_code=400, detail="No grid cells found to export")

    export_service = ExportService()
    zip_bytes = export_service.generate_shapefile_zip(cells, hotspots)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=hasar_shapefile_{job_id}.zip"}
    )

@router.get("/{job_id}/export/geopackage")
async def export_geopackage(
    job_id: uuid.UUID,
    grid_repo: SQLGridCellRepository = Depends(get_grid_repo),
    hotspot_repo: SQLHotspotRepository = Depends(get_hotspot_repo)
):
    """
    Exports spatial layers to an OGC standard GeoPackage (.gpkg) file.
    """
    cells = await grid_repo.list_by_job(job_id)
    hotspots = await hotspot_repo.list_by_job(job_id)

    if not cells:
        raise HTTPException(status_code=400, detail="No grid cells found to export")

    export_service = ExportService()
    gpkg_bytes = export_service.generate_geopackage(cells, hotspots)

    return Response(
        content=gpkg_bytes,
        media_type="application/geopackage+sqlite3",
        headers={"Content-Disposition": f"attachment; filename=hasar_geopackage_{job_id}.gpkg"}
    )

@router.get("/{job_id}/export/geotiff")
async def export_geotiff(
    job_id: uuid.UUID,
    layer: str = Query("fusion", description="Layer type: fusion, sar, or ms"),
    artifact_repo: SQLOutputArtifactRepository = Depends(get_artifact_repo)
):
    """
    Downloads or redirects to the GeoTIFF raster file for the specified layer.
    """
    artifacts = await artifact_repo.list_by_job(job_id)
    export_service = ExportService()
    info = export_service.get_raster_download_info(job_id, layer, artifacts)

    minio_key = info.get("minio_key")
    if minio_key:
        try:
            from fastapi.responses import StreamingResponse
            from app.infrastructure.external.minio_client import MinioStorageClient
            client = MinioStorageClient()
            minio_obj = client.get_object(minio_key)
            return StreamingResponse(
                minio_obj.stream(32 * 1024),
                media_type="image/tiff",
                headers={"Content-Disposition": f"attachment; filename={layer}_{job_id}.tif"}
            )
        except Exception:
            pass

    local_path = info.get("local_path")
    if local_path and os.path.exists(local_path):
        return FileResponse(
            path=local_path,
            media_type="image/tiff",
            filename=f"{layer}_{job_id}.tif"
        )

    raise HTTPException(status_code=404, detail=f"GeoTIFF for layer '{layer}' not found")
