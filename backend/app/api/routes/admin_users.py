from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import User, RoleEnum
from app.api.schemas import UserResponse, UserRegisterRequest, UserUpdateRequest
from app.application.services.user_service import UserService
from app.api.deps import require_role

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_role([RoleEnum.ADMIN]))]
)

def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service)
):
    users = await service.list_users(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserRegisterRequest,
    service: UserService = Depends(get_user_service)
):
    user = await service.create_user(data)
    return UserResponse.model_validate(user)

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdateRequest,
    service: UserService = Depends(get_user_service),
    current_admin: User = Depends(require_role([RoleEnum.ADMIN]))
):
    user = await service.update_user(user_id=user_id, update_data=data, requesting_admin=current_admin)
    return UserResponse.model_validate(user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
    current_admin: User = Depends(require_role([RoleEnum.ADMIN]))
):
    await service.delete_user(user_id=user_id, requesting_admin=current_admin)
    return None
