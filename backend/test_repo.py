import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.database import AsyncSessionLocal
from app.domain.entities import UserEntity, AOIEntity
from app.infrastructure.repositories.sql_repositories import SQLUserRepository, SQLAOIRepository

async def main():
    print("Testing Repositories...")
    async with AsyncSessionLocal() as session:
        user_repo = SQLUserRepository(session)
        aoi_repo = SQLAOIRepository(session)
        
        # Create user
        new_user = UserEntity(email="test@example.com", hashed_password="hashedpassword123")
        try:
            created_user = await user_repo.create(new_user)
            print(f"Created User: {created_user.id} - {created_user.email}")
            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"User already exists or error: {e}")
            created_user = await user_repo.get_by_email("test@example.com")
            print(f"Fetched existing User: {created_user.id} - {created_user.email}")

        # Create AOI
        new_aoi = AOIEntity(
            name="Test Field", 
            owner_id=created_user.id,
            geometry="POLYGON((30 10, 40 40, 20 40, 10 20, 30 10))" # WKT string
        )
        created_aoi = await aoi_repo.create(new_aoi)
        print(f"Created AOI: {created_aoi.id} - {created_aoi.name}")
        await session.commit()

        # Fetch AOI
        fetched_aoi = await aoi_repo.get_by_id(created_aoi.id)
        print(f"Fetched AOI: {fetched_aoi.id} - {fetched_aoi.name}")

if __name__ == "__main__":
    asyncio.run(main())
