from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
from app.infrastructure.db.database import get_db
from app.core.config import settings
from app.infrastructure.tasks import celery_app
from typing import Dict, Any

router = APIRouter(prefix="/health", tags=["system"])

@router.get("/", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "database": "unknown",
            "redis": "unknown",
            "celery": "unknown"
        }
    }
    
    # 1. Check PostgreSQL Database
    try:
        await db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 2. Check Redis Broker & Cache
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        ping_res = await r.ping()
        await r.close()
        if ping_res:
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["services"]["redis"] = "unresponsive"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 3. Check Celery Workers
    try:
        inspector = celery_app.control.inspect(timeout=1.0)
        ping_dict = inspector.ping() if inspector else None
        if ping_dict and len(ping_dict) > 0:
            health_status["services"]["celery"] = f"healthy ({len(ping_dict)} workers online)"
        else:
            health_status["services"]["celery"] = "no workers responding"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["celery"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status
