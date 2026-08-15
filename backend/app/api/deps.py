from typing import List, Optional
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import User, RoleEnum
from app.core.security import decode_access_token

security_bearer = HTTPBearer(auto_error=False)

async def get_optional_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Returns authenticated user if a valid bearer token is provided, or None if guest.
    """
    if not auth or not auth.credentials:
        return None

    token = auth.credentials
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user and user.is_active:
        return user
    return None

async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Strict authentication dependency. Raises 401 if missing or invalid.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama belirteci eksik veya geçersiz.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş belirteç.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Belirteç kullanıcı kimliği içermiyor.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı ID formatı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kullanıcı hesabı devre dışı bırakılmıştır.",
        )

    return user

async def get_current_user_or_default(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Returns the authenticated user if token is present, or falls back to the default
    system user (e.g. analyst@damage.org) for guest/demo interactions.
    """
    optional_user = await get_optional_current_user(auth=auth, db=db)
    if optional_user:
        return optional_user

    # Fallback to default user
    stmt = select(User).where(User.email == "analyst@damage.org")
    result = await db.execute(stmt)
    default_user = result.scalar_one_or_none()

    if not default_user:
        # If not found, get any active user
        stmt_any = select(User).where(User.is_active == True).limit(1)
        res_any = await db.execute(stmt_any)
        default_user = res_any.scalar_one_or_none()

    if not default_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sistemde aktif kullanıcı bulunamadı. Lütfen oturum açınız.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return default_user

def require_roles(allowed_roles: List[RoleEnum]):
    """
    Role-Based Access Control (RBAC) Dependency Guard.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bu işlem için yetkiniz bulunmamaktadır. Gerekli roller: {[r.value for r in allowed_roles]} (Mevcut: {current_user.role.value})"
            )
        return current_user
    return role_checker

require_role = require_roles
