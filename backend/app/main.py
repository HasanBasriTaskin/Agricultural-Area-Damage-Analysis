from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.routes import aoi, job, results, export, system, auth, admin_users, admin_jobs
from app.infrastructure.db.database import AsyncSessionLocal
from app.infrastructure.db.models import User, RoleEnum
from app.core.security import get_password_hash

async def seed_initial_users():
    """
    Seeds default system users on application startup if they don't exist or refreshes their password.
    """
    default_users = [
        {"email": "admin@damage.org", "password": "Admin123!", "role": RoleEnum.ADMIN},
        {"email": "analyst@damage.org", "password": "Analyst123!", "role": RoleEnum.ANALYST},
        {"email": "viewer@damage.org", "password": "Viewer123!", "role": RoleEnum.VIEWER},
    ]

    async with AsyncSessionLocal() as db:
        for u_data in default_users:
            stmt = select(User).where(User.email == u_data["email"])
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                new_user = User(
                    email=u_data["email"],
                    hashed_password=get_password_hash(u_data["password"]),
                    role=u_data["role"],
                    is_active=True
                )
                db.add(new_user)
            else:
                existing.hashed_password = get_password_hash(u_data["password"])
                existing.role = u_data["role"]
                existing.is_active = True
        await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed default users
    try:
        await seed_initial_users()
    except Exception as e:
        print(f"User seeding note: {e}")
    yield

app = FastAPI(
    title="SAR + MS Tarımsal Hasar Analizi API",
    description="Tarımsal Hasar Analizi için FastAPI tabanlı backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")
app.include_router(admin_jobs.router, prefix="/api/v1")
app.include_router(aoi.router, prefix="/api/v1/aoi", tags=["aoi"])
app.include_router(job.router, prefix="/api/v1")
app.include_router(results.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Tarımsal Hasar Analizi API Çalışıyor"}
