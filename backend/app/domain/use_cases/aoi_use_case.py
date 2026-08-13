import uuid
from typing import List, Optional
from app.domain.entities import AOIEntity
from app.domain.repositories import AOIRepository

class AOIUseCase:
    def __init__(self, aoi_repo: AOIRepository):
        self.aoi_repo = aoi_repo

    async def create_aoi(self, name: str, owner_id: uuid.UUID, geometry: str) -> AOIEntity:
        if not name or len(name.strip()) == 0:
            raise ValueError("AOI name cannot be empty")
        
        # Here we could validate the WKT geometry string, but we trust the schema for now
        new_aoi = AOIEntity(
            name=name.strip(),
            owner_id=owner_id,
            geometry=geometry
        )
        return await self.aoi_repo.create(new_aoi)

    async def get_aoi(self, aoi_id: uuid.UUID) -> Optional[AOIEntity]:
        return await self.aoi_repo.get_by_id(aoi_id)

    async def list_user_aois(self, user_id: uuid.UUID) -> List[AOIEntity]:
        return await self.aoi_repo.list_by_user(user_id)
