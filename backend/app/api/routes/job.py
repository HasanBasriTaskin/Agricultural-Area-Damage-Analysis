from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import List, Optional

from app.api.schemas import JobCreate, JobResponse
from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import User, AnalysisJob, AOI
from app.infrastructure.repositories.sql_repositories import SQLAnalysisJobRepository
from app.application.use_cases.job_use_cases import CreateJobUseCase
from celery import chord
from app.infrastructure.tasks import run_sar_pipeline, run_ms_pipeline, run_weather_pipeline, finalize_pipeline
from app.api.deps import get_current_user_or_default, get_optional_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])

def get_job_repo(db: AsyncSession = Depends(get_db)) -> SQLAnalysisJobRepository:
    return SQLAnalysisJobRepository(db)

def get_create_job_use_case(repo: SQLAnalysisJobRepository = Depends(get_job_repo)) -> CreateJobUseCase:
    return CreateJobUseCase(repo)

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    use_case: CreateJobUseCase = Depends(get_create_job_use_case),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db)
):
    try:
        job = await use_case.execute(
            aoi_id=job_in.aoi_id,
            event_date=job_in.event_date,
            created_by=current_user.id,
            weights_dict=job_in.weights
        )
        
        # Fetch AOI name for response
        aoi_stmt = select(AOI.name).where(AOI.id == job_in.aoi_id)
        aoi_res = await db.execute(aoi_stmt)
        aoi_name = aoi_res.scalar_one_or_none()

        job_id_str = str(job.id)
        
        # Trigger Celery Task (Chord: parallel SAR, MS, and Weather, then finalize)
        chord(
            [run_sar_pipeline.s(job_id_str), run_ms_pipeline.s(job_id_str), run_weather_pipeline.s(job_id_str)]
        )(finalize_pipeline.s(job_id_str))
        
        resp = JobResponse.model_validate(job)
        resp.aoi_name = aoi_name
        return resp
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[JobResponse])
async def list_user_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    stmt = (
        select(AnalysisJob, AOI.name.label("aoi_name"))
        .outerjoin(AOI, AnalysisJob.aoi_id == AOI.id)
        .order_by(AnalysisJob.created_at.desc())
    )
    if current_user:
        stmt = stmt.where(AnalysisJob.created_by == current_user.id)
    else:
        stmt = stmt.limit(50)

    result = await db.execute(stmt)
    rows = result.all()

    out = []
    for job, aoi_name in rows:
        item = JobResponse.model_validate(job)
        item.aoi_name = aoi_name or "İsimsiz Parsel"
        out.append(item)
    return out

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(AnalysisJob, AOI.name.label("aoi_name"))
        .outerjoin(AOI, AnalysisJob.aoi_id == AOI.id)
        .where(AnalysisJob.id == job_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    job, aoi_name = row
    item = JobResponse.model_validate(job)
    item.aoi_name = aoi_name or "İsimsiz Parsel"
    return item
