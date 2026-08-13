import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import UserEntity, AOIEntity, AnalysisJobEntity

class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: UserEntity) -> UserEntity:
        pass

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserEntity]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        pass

    @abstractmethod
    async def update(self, user_id: uuid.UUID, data: dict) -> UserEntity:
        pass


class AOIRepository(ABC):
    @abstractmethod
    async def create(self, aoi: AOIEntity) -> AOIEntity:
        pass

    @abstractmethod
    async def get_by_id(self, aoi_id: uuid.UUID) -> Optional[AOIEntity]:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: uuid.UUID) -> List[AOIEntity]:
        pass

    @abstractmethod
    async def update(self, aoi_id: uuid.UUID, data: dict) -> AOIEntity:
        pass

    @abstractmethod
    async def delete(self, aoi_id: uuid.UUID) -> bool:
        pass


class AnalysisJobRepository(ABC):
    @abstractmethod
    async def create(self, job: AnalysisJobEntity) -> AnalysisJobEntity:
        pass

    @abstractmethod
    async def get_by_id(self, job_id: uuid.UUID) -> Optional[AnalysisJobEntity]:
        pass

    @abstractmethod
    async def list_by_aoi(self, aoi_id: uuid.UUID) -> List[AnalysisJobEntity]:
        pass

    @abstractmethod
    async def update(self, job_id: uuid.UUID, data: dict) -> AnalysisJobEntity:
        pass
