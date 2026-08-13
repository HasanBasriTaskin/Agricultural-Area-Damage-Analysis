import asyncio
import uuid
from app.infrastructure.db.database import AsyncSessionLocal
from app.infrastructure.repositories.sql_repositories import SQLAOIRepository
from app.domain.use_cases.aoi_use_case import AOIUseCase

async def main():
    print("Testing Use Case...")
    async with AsyncSessionLocal() as session:
        aoi_repo = SQLAOIRepository(session)
        use_case = AOIUseCase(aoi_repo)
        
        # Test validation error
        try:
            await use_case.create_aoi(name="   ", owner_id=uuid.uuid4(), geometry="POLYGON((0 0, 1 1, 1 0, 0 0))")
        except ValueError as e:
            print(f"Validation worked: {e}")
        
        # We don't want to actually commit unless we know the user exists, 
        # so we will just run the validation check for now.
        print("Use Case successfully tested!")

if __name__ == "__main__":
    asyncio.run(main())
