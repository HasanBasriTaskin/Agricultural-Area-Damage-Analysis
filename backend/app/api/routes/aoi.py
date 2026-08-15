from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from typing import List

from app.api.schemas import AOICreate, AOIResponse
from app.domain.use_cases.aoi_use_case import AOIUseCase
from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repositories.sql_repositories import SQLAOIRepository
from app.api.deps import get_current_user_or_default

router = APIRouter()

def get_aoi_use_case(session: AsyncSession = Depends(get_db)) -> AOIUseCase:
    repo = SQLAOIRepository(session)
    return AOIUseCase(repo)

@router.post("/", response_model=AOIResponse, status_code=status.HTTP_201_CREATED)
async def create_aoi(
    aoi_data: AOICreate,
    use_case: AOIUseCase = Depends(get_aoi_use_case),
    current_user: User = Depends(get_current_user_or_default)
):
    try:
        new_aoi = await use_case.create_aoi(
            name=aoi_data.name,
            owner_id=current_user.id,
            geometry=aoi_data.geometry
        )
        return new_aoi
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")

@router.get("/{aoi_id}", response_model=AOIResponse)
async def get_aoi(
    aoi_id: uuid.UUID,
    use_case: AOIUseCase = Depends(get_aoi_use_case)
):
    aoi = await use_case.get_aoi(aoi_id)
    if not aoi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AOI not found")
    return aoi

@router.get("/", response_model=List[AOIResponse])
async def list_aois(
    use_case: AOIUseCase = Depends(get_aoi_use_case),
    current_user: User = Depends(get_current_user_or_default)
):
    return await use_case.list_user_aois(current_user.id)
