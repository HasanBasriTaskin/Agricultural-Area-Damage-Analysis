from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.schemas import JobCreate, JobResponse
from app.infrastructure.db.database import get_db
from app.infrastructure.repositories.sql_repositories import SQLAnalysisJobRepository
from app.application.use_cases.job_use_cases import CreateJobUseCase
from celery import chord
from app.infrastructure.tasks import run_sar_pipeline, run_ms_pipeline, finalize_pipeline

# For now, simulate authenticated user ID
DEMO_USER_ID = uuid.UUID("c2cb63b8-acc5-4384-a09b-47b81de325e6")

router = APIRouter(prefix="/jobs", tags=["jobs"])

def get_job_repo(db: AsyncSession = Depends(get_db)) -> SQLAnalysisJobRepository:
    return SQLAnalysisJobRepository(db)

def get_create_job_use_case(repo: SQLAnalysisJobRepository = Depends(get_job_repo)) -> CreateJobUseCase:
    return CreateJobUseCase(repo)

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    use_case: CreateJobUseCase = Depends(get_create_job_use_case)
):
    try:
        job = await use_case.execute(
            aoi_id=job_in.aoi_id,
            event_date=job_in.event_date,
            created_by=DEMO_USER_ID,
            weights_dict=job_in.weights
        )
        
        job_id_str = str(job.id)
        
        # Trigger Celery Task (Chord: parallel SAR and MS, then finalize)
        chord(
            [run_sar_pipeline.s(job_id_str), run_ms_pipeline.s(job_id_str)]
        )(finalize_pipeline.s(job_id_str))
        
        return job
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, repo: SQLAnalysisJobRepository = Depends(get_job_repo)):
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
