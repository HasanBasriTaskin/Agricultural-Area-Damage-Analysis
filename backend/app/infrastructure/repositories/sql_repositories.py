import uuid
from typing import List, Optional, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKBElement

from app.domain.entities import (
    UserEntity, AOIEntity, AnalysisJobEntity,
    ParcelDamageResultEntity, GridCellEntity, HotspotResultEntity, OutputArtifactEntity
)
from app.domain.repositories import (
    UserRepository, AOIRepository, AnalysisJobRepository,
    GridCellRepository, HotspotRepository, OutputArtifactRepository
)
from app.infrastructure.db import models

def _convert_geom(geom: Any) -> Any:
    if isinstance(geom, WKBElement):
        try:
            return to_shape(geom).wkt
        except Exception:
            return str(geom)
    return geom

class SQLUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: UserEntity) -> UserEntity:
        db_user = models.User(**user.model_dump(exclude={'id'}))
        db_user.id = user.id
        self.session.add(db_user)
        await self.session.commit()
        return UserEntity(
            id=db_user.id,
            email=db_user.email,
            role=db_user.role,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            hashed_password=db_user.hashed_password
        )

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
        await self.session.commit()
        return UserEntity.model_validate(db_user)


class SQLAOIRepository(AOIRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, aoi: AOIEntity) -> AOIEntity:
        db_aoi = models.AOI(**aoi.model_dump(exclude={'id'}))
        db_aoi.id = aoi.id
        self.session.add(db_aoi)
        await self.session.commit()
        return AOIEntity(
            id=db_aoi.id,
            name=db_aoi.name,
            owner_id=db_aoi.owner_id,
            geometry=aoi.geometry,
            created_at=db_aoi.created_at
        )

    async def get_by_id(self, aoi_id: uuid.UUID) -> Optional[AOIEntity]:
        stmt = select(models.AOI).where(models.AOI.id == aoi_id)
        result = await self.session.execute(stmt)
        db_aoi = result.scalar_one_or_none()
        if db_aoi:
            return AOIEntity(
                id=db_aoi.id,
                name=db_aoi.name,
                owner_id=db_aoi.owner_id,
                geometry=_convert_geom(db_aoi.geometry),
                created_at=db_aoi.created_at
            )
        return None

    async def list_by_user(self, user_id: uuid.UUID) -> List[AOIEntity]:
        stmt = select(models.AOI).where(models.AOI.owner_id == user_id)
        result = await self.session.execute(stmt)
        db_aois = result.scalars().all()
        return [
            AOIEntity(
                id=aoi.id,
                name=aoi.name,
                owner_id=aoi.owner_id,
                geometry=_convert_geom(aoi.geometry),
                created_at=aoi.created_at
            )
            for aoi in db_aois
        ]

    async def update(self, aoi_id: uuid.UUID, data: dict) -> AOIEntity:
        stmt = update(models.AOI).where(models.AOI.id == aoi_id).values(**data).returning(models.AOI)
        result = await self.session.execute(stmt)
        db_aoi = result.scalar_one()
        await self.session.commit()
        return AOIEntity(
            id=db_aoi.id,
            name=db_aoi.name,
            owner_id=db_aoi.owner_id,
            geometry=_convert_geom(db_aoi.geometry),
            created_at=db_aoi.created_at
        )

    async def delete(self, aoi_id: uuid.UUID) -> bool:
        stmt = delete(models.AOI).where(models.AOI.id == aoi_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0


class SQLAnalysisJobRepository(AnalysisJobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, job: AnalysisJobEntity) -> AnalysisJobEntity:
        db_job = models.AnalysisJob(**job.model_dump(exclude={'id'}))
        db_job.id = job.id
        self.session.add(db_job)
        await self.session.commit()
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
        await self.session.commit()
        return AnalysisJobEntity.model_validate(db_job)


class SQLGridCellRepository(GridCellRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_many(self, cells: List[GridCellEntity]) -> List[GridCellEntity]:
        db_cells = [models.GridCell(**c.model_dump(exclude={'id'}), id=c.id) for c in cells]
        self.session.add_all(db_cells)
        await self.session.commit()
        return [GridCellEntity.model_validate(c) for c in db_cells]

    async def list_by_job(self, job_id: uuid.UUID) -> List[models.GridCell]:
        stmt = select(models.GridCell).where(models.GridCell.job_id == job_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class SQLHotspotRepository(HotspotRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_many(self, hotspots: List[HotspotResultEntity]) -> List[HotspotResultEntity]:
        db_hotspots = [models.HotspotResult(**h.model_dump(exclude={'id'}), id=h.id) for h in hotspots]
        self.session.add_all(db_hotspots)
        await self.session.commit()
        return [HotspotResultEntity.model_validate(h) for h in db_hotspots]

    async def list_by_job(self, job_id: uuid.UUID) -> List[models.HotspotResult]:
        stmt = select(models.HotspotResult).where(models.HotspotResult.job_id == job_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class SQLOutputArtifactRepository(OutputArtifactRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, artifact: OutputArtifactEntity) -> OutputArtifactEntity:
        db_art = models.OutputArtifact(**artifact.model_dump(exclude={'id'}), id=artifact.id)
        self.session.add(db_art)
        await self.session.commit()
        return OutputArtifactEntity.model_validate(db_art)

    async def list_by_job(self, job_id: uuid.UUID) -> List[models.OutputArtifact]:
        stmt = select(models.OutputArtifact).where(models.OutputArtifact.job_id == job_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_job_and_type(self, job_id: uuid.UUID, file_type: str) -> Optional[models.OutputArtifact]:
        stmt = select(models.OutputArtifact).where(
            models.OutputArtifact.job_id == job_id,
            models.OutputArtifact.file_type == file_type
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
