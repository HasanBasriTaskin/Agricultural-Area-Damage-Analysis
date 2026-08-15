from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException, status

from app.infrastructure.db.models import User, RoleEnum
from app.core.security import get_password_hash
from app.api.schemas import UserUpdateRequest, UserRegisterRequest

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        stmt = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, user_data: UserRegisterRequest) -> User:
        stmt = select(User).where(User.email == user_data.email)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu e-posta adresi zaten kullanımda."
            )

        new_user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role or RoleEnum.VIEWER,
            is_active=True
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def update_user(
        self,
        user_id: uuid.UUID,
        update_data: UserUpdateRequest,
        requesting_admin: User
    ) -> User:
        target_user = await self.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kullanıcı bulunamadı."
            )

        # Self-lockout protection
        if target_user.id == requesting_admin.id:
            if update_data.role is not None and update_data.role != RoleEnum.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Kendi yönetici (admin) rolünüzü düşüremezsiniz (Self-Lockout Koruması)."
                )
            if update_data.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Kendi hesabınızı devre dışı bırakamazsınız."
                )

        if update_data.role is not None:
            target_user.role = update_data.role
        if update_data.is_active is not None:
            target_user.is_active = update_data.is_active
        if update_data.password:
            target_user.hashed_password = get_password_hash(update_data.password)

        await self.db.commit()
        await self.db.refresh(target_user)
        return target_user

    async def delete_user(self, user_id: uuid.UUID, requesting_admin: User) -> bool:
        if user_id == requesting_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kendi yönetici hesabınızı silemezsiniz."
            )

        target_user = await self.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kullanıcı bulunamadı."
            )

        await self.db.delete(target_user)
        await self.db.commit()
        return True
