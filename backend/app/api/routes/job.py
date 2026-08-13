from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.api.schemas import JobCreate, JobResponse
from app.infrastructure.db.database import get_db
from app.infrastructure.repositories.job_repository import SQLJobRepository
from app.application.use_cases.job_use_cases import CreateJobUseCase

# For now, simulate authenticated user ID
DEMO_USER_ID = uuid.UUID("c2cb63b8-acc5-4384-a09b-47b81de325e6")

router = APIRouter(prefix="/jobs", tags=["jobs"])

def get_job_repo(db: Session = Depends(get_db)) -> SQLJobRepository:
    return SQLJobRepository(db)

def get_create_job_use_case(repo: SQLJobRepository = Depends(get_job_repo)) -> CreateJobUseCase:
    return CreateJobUseCase(repo)

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: JobCreate,
    use_case: CreateJobUseCase = Depends(get_create_job_use_case)
):
    try:
        job = use_case.execute(
            aoi_id=job_in.aoi_id,
            event_date=job_in.event_date,
            created_by=DEMO_USER_ID,
            weights_dict=job_in.weights
        )
        return job
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
