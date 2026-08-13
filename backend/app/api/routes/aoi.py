from fastapi import APIRouter, Depends, HTTPException
import uuid
from typing import List

from app.api.schemas import AOICreate, AOIResponse
from app.domain.use_cases.aoi_use_case import AOIUseCase
from app.infrastructure.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repositories.sql_repositories import SQLAOIRepository

router = APIRouter()

# Simple Dependency wiring for the Use Case
def get_aoi_use_case(session: AsyncSession = Depends(get_db)) -> AOIUseCase:
    repo = SQLAOIRepository(session)
    return AOIUseCase(repo)

# For testing without auth, we just use a dummy user_id
DUMMY_USER_ID = uuid.UUID("c2cb63b8-acc5-4384-a09b-47b81de325e6")

@router.post("/", response_model=AOIResponse)
async def create_aoi(
    aoi_data: AOICreate,
    use_case: AOIUseCase = Depends(get_aoi_use_case)
):
    try:
        # Pass DUMMY_USER_ID since we don't have auth yet
        new_aoi = await use_case.create_aoi(
            name=aoi_data.name,
            owner_id=DUMMY_USER_ID,
            geometry=aoi_data.geometry
        )
        return new_aoi
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{aoi_id}", response_model=AOIResponse)
async def get_aoi(
    aoi_id: uuid.UUID,
    use_case: AOIUseCase = Depends(get_aoi_use_case)
):
    aoi = await use_case.get_aoi(aoi_id)
    if not aoi:
        raise HTTPException(status_code=404, detail="AOI not found")
    return aoi

@router.get("/", response_model=List[AOIResponse])
async def list_aois(
    use_case: AOIUseCase = Depends(get_aoi_use_case)
):
    return await use_case.list_user_aois(DUMMY_USER_ID)
