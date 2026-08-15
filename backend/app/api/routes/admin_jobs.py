from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.db.database import get_db
from app.infrastructure.db.models import AnalysisJob, AOI, User, RoleEnum, JobStatusEnum
from app.api.deps import require_role
from app.infrastructure.tasks import celery_app

router = APIRouter(
    prefix="/admin",
    tags=["admin-monitoring"],
    dependencies=[Depends(require_role([RoleEnum.ADMIN]))]
)

@router.get("/jobs")
async def list_all_jobs(
    status: Optional[JobStatusEnum] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    List all jobs across all users with enriched AOI and user email details for Admin.
    """
    stmt = (
        select(AnalysisJob, AOI.name.label("aoi_name"), User.email.label("user_email"))
        .outerjoin(AOI, AnalysisJob.aoi_id == AOI.id)
        .outerjoin(User, AnalysisJob.created_by == User.id)
        .order_by(AnalysisJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(AnalysisJob.status == status)

    result = await db.execute(stmt)
    rows = result.all()

    jobs_out = []
    for job, aoi_name, user_email in rows:
        jobs_out.append({
            "id": str(job.id),
            "aoi_id": str(job.aoi_id),
            "aoi_name": aoi_name or "İsimsiz Alan",
            "created_by": str(job.created_by),
            "user_email": user_email or "Bilinmiyor",
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            "sar_status": job.sar_status,
            "ms_status": job.ms_status,
            "weather_status": job.weather_status,
            "event_date": job.event_date.isoformat() if job.event_date else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "error_message": job.error_message
        })
    return jobs_out

@router.get("/queue-stats")
async def get_queue_stats() -> Dict[str, Any]:
    """
    Returns live Celery worker and queue metrics.
    """
    try:
        inspector = celery_app.control.inspect(timeout=1.5)
        active_tasks = inspector.active() or {}
        reserved_tasks = inspector.reserved() or {}
        scheduled_tasks = inspector.scheduled() or {}
        ping_res = inspector.ping() or {}

        total_active = sum(len(tasks) for tasks in active_tasks.values())
        total_reserved = sum(len(tasks) for tasks in reserved_tasks.values())
        total_scheduled = sum(len(tasks) for tasks in scheduled_tasks.values())
        worker_count = len(ping_res)

        return {
            "workers_online": worker_count,
            "active_tasks_count": total_active,
            "reserved_tasks_count": total_reserved,
            "scheduled_tasks_count": total_scheduled,
            "workers": list(ping_res.keys()),
            "details": {
                "active": active_tasks,
                "reserved": reserved_tasks,
            }
        }
    except Exception as e:
        return {
            "workers_online": 0,
            "active_tasks_count": 0,
            "reserved_tasks_count": 0,
            "scheduled_tasks_count": 0,
            "workers": [],
            "error": str(e)
        }
