from typing import Optional
from passlib.context import CryptContext
from app.domain.interfaces.auth_provider import IAuthProvider
from app.domain.entities import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.db.models import UserModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LocalAuthProvider(IAuthProvider):
    """
    Local Authentication Strategy implementation using email and password.
    """
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def authenticate(self, credentials: dict) -> Optional[User]:
        email = credentials.get("email")
        password = credentials.get("password")
        
        if not email or not password:
            return None
            
        user_model = await self._get_user_model(email)
        if not user_model:
            return None
            
        if not pwd_context.verify(password, user_model.hashed_password):
            return None
            
        return User(
            id=user_model.id,
            email=user_model.email,
            hashed_password=user_model.hashed_password,
            role=user_model.role,
            is_active=user_model.is_active,
            created_at=user_model.created_at
        )

    async def create_user(self, data: dict) -> User:
        hashed_pw = pwd_context.hash(data["password"])
        new_user = UserModel(
            email=data["email"],
            hashed_password=hashed_pw,
            role=data.get("role", "user")
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        return User(
            id=new_user.id,
            email=new_user.email,
            hashed_password=new_user.hashed_password,
            role=new_user.role,
            is_active=new_user.is_active,
            created_at=new_user.created_at
        )

    async def get_user_by_email(self, email: str) -> Optional[User]:
        user_model = await self._get_user_model(email)
        if not user_model:
            return None
            
        return User(
            id=user_model.id,
            email=user_model.email,
            hashed_password=user_model.hashed_password,
            role=user_model.role,
            is_active=user_model.is_active,
            created_at=user_model.created_at
        )
        
    async def _get_user_model(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.db.execute(stmt)
        return result.scalars().first()
