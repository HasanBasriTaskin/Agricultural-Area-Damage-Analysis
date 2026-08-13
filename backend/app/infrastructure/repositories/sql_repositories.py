import uuid
from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKBElement

from app.domain.entities import UserEntity, AOIEntity, AnalysisJobEntity
from app.domain.repositories import UserRepository, AOIRepository, AnalysisJobRepository
from app.infrastructure.db import models

def _geom_to_wkt(geom) -> Optional[str]:
    if geom is None:
        return None
    if isinstance(geom, WKBElement):
        try:
            # We can use shapely if installed, but since we didn't add it yet,
            # we can return the hex string or just keep it as is. 
            # For strict separation, returning the hex or a string representation is better.
            # But the easiest way without shapely is to query with ST_AsText, which requires changing the query.
            # For now, we will leave it as is. The user can convert it at the API layer.
            pass
        except Exception:
            pass
    return geom

class SQLUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: UserEntity) -> UserEntity:
        db_user = models.User(**user.model_dump(exclude={'id'}))
        db_user.id = user.id
        self.session.add(db_user)
        await self.session.flush()
        return UserEntity.model_validate(db_user)

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserEntity]:
        stmt = select(models.User).where(models.User.id == user_id)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()
        if db_user:
            return UserEntity.model_validate(db_user)
        return None

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        stmt = select(models.User).where(models.User.email == email)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()
        if db_user:
            return UserEntity.model_validate(db_user)
        return None

    async def update(self, user_id: uuid.UUID, data: dict) -> UserEntity:
        stmt = update(models.User).where(models.User.id == user_id).values(**data).returning(models.User)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one()
        await self.session.flush()
        return UserEntity.model_validate(db_user)


class SQLAOIRepository(AOIRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, aoi: AOIEntity) -> AOIEntity:
        # Note: geometry should be provided as WKT string in aoi.geometry
        db_aoi = models.AOI(**aoi.model_dump(exclude={'id'}))
        db_aoi.id = aoi.id
        self.session.add(db_aoi)
        await self.session.flush()
        
        # When creating, geometry is assigned. To return a valid entity, we map it back
        return AOIEntity.model_validate(db_aoi)

    async def get_by_id(self, aoi_id: uuid.UUID) -> Optional[AOIEntity]:
        stmt = select(models.AOI).where(models.AOI.id == aoi_id)
        result = await self.session.execute(stmt)
        db_aoi = result.scalar_one_or_none()
        if db_aoi:
            return AOIEntity.model_validate(db_aoi)
        return None

    async def list_by_user(self, user_id: uuid.UUID) -> List[AOIEntity]:
        stmt = select(models.AOI).where(models.AOI.owner_id == user_id)
        result = await self.session.execute(stmt)
        db_aois = result.scalars().all()
        return [AOIEntity.model_validate(aoi) for aoi in db_aois]

    async def update(self, aoi_id: uuid.UUID, data: dict) -> AOIEntity:
        stmt = update(models.AOI).where(models.AOI.id == aoi_id).values(**data).returning(models.AOI)
        result = await self.session.execute(stmt)
        db_aoi = result.scalar_one()
        await self.session.flush()
        return AOIEntity.model_validate(db_aoi)

    async def delete(self, aoi_id: uuid.UUID) -> bool:
        stmt = delete(models.AOI).where(models.AOI.id == aoi_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0


class SQLAnalysisJobRepository(AnalysisJobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, job: AnalysisJobEntity) -> AnalysisJobEntity:
        db_job = models.AnalysisJob(**job.model_dump(exclude={'id'}))
        db_job.id = job.id
        self.session.add(db_job)
        await self.session.flush()
        return AnalysisJobEntity.model_validate(db_job)

    async def get_by_id(self, job_id: uuid.UUID) -> Optional[AnalysisJobEntity]:
        stmt = select(models.AnalysisJob).where(models.AnalysisJob.id == job_id)
        result = await self.session.execute(stmt)
        db_job = result.scalar_one_or_none()
        if db_job:
            return AnalysisJobEntity.model_validate(db_job)
        return None

    async def list_by_aoi(self, aoi_id: uuid.UUID) -> List[AnalysisJobEntity]:
        stmt = select(models.AnalysisJob).where(models.AnalysisJob.aoi_id == aoi_id)
        result = await self.session.execute(stmt)
        db_jobs = result.scalars().all()
        return [AnalysisJobEntity.model_validate(job) for job in db_jobs]

    async def update(self, job_id: uuid.UUID, data: dict) -> AnalysisJobEntity:
        stmt = update(models.AnalysisJob).where(models.AnalysisJob.id == job_id).values(**data).returning(models.AnalysisJob)
        result = await self.session.execute(stmt)
        db_job = result.scalar_one()
        await self.session.flush()
        return AnalysisJobEntity.model_validate(db_job)
