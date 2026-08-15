from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.interfaces.auth_provider import IAuthProvider
from app.domain.entities import UserEntity
from app.infrastructure.db.models import User, RoleEnum
from app.core.security import verify_password, get_password_hash

class LocalAuthProvider(IAuthProvider):
    """
    Local Authentication Strategy implementation using email and password.
    """
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def _get_user_model(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def authenticate(self, credentials: dict) -> Optional[UserEntity]:
        email = credentials.get("email")
        password = credentials.get("password")
        
        if not email or not password:
            return None
            
        user_model = await self._get_user_model(email)
        if not user_model:
            return None
            
        if not verify_password(password, user_model.hashed_password):
            return None
            
        return UserEntity(
            id=user_model.id,
            email=user_model.email,
            hashed_password=user_model.hashed_password,
            role=user_model.role,
            is_active=user_model.is_active,
            created_at=user_model.created_at
        )

    async def create_user(self, data: dict) -> UserEntity:
        hashed_pw = get_password_hash(data["password"])
        role_val = data.get("role", RoleEnum.VIEWER)
        if isinstance(role_val, str):
            role_val = RoleEnum(role_val)

        new_user = User(
            email=data["email"],
            hashed_password=hashed_pw,
            role=role_val,
            is_active=data.get("is_active", True)
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        return UserEntity(
            id=new_user.id,
            email=new_user.email,
            hashed_password=new_user.hashed_password,
            role=new_user.role,
            is_active=new_user.is_active,
            created_at=new_user.created_at
        )

    async def get_user_by_id(self, user_id) -> Optional[UserEntity]:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user_model = result.scalar_one_or_none()
        if not user_model:
            return None
        return UserEntity(
            id=user_model.id,
            email=user_model.email,
            hashed_password=user_model.hashed_password,
            role=user_model.role,
            is_active=user_model.is_active,
            created_at=user_model.created_at
        )
