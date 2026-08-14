import os
from fastapi import APIRouter, Query
from typing import Dict, Any

from app.infrastructure.external.minio_client import MinioStorageClient

router = APIRouter(prefix="/system", tags=["system"])

@router.get("/storage-info")
async def get_storage_info() -> Dict[str, Any]:
    """
    Returns current disk usage in temp_downloads and MinIO object count.
    """
    temp_dir = "temp_downloads"
    local_size_bytes = 0
    local_files_count = 0

    if os.path.exists(temp_dir):
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    local_size_bytes += os.path.getsize(fp)
                    local_files_count += 1
                except Exception:
                    pass

    minio_objects_count = 0
    try:
        client = MinioStorageClient()
        objects = client.client.list_objects(client.bucket_name, recursive=True)
        minio_objects_count = sum(1 for _ in objects)
    except Exception:
        pass

    return {
        "local_temp_files": local_files_count,
        "local_temp_mb": round(local_size_bytes / (1024 * 1024), 2),
        "minio_objects_count": minio_objects_count
    }

@router.post("/cleanup")
async def cleanup_storage(
    clean_minio: bool = Query(False, description="Also clean MinIO bucket artifacts if True")
) -> Dict[str, Any]:
    """
    Manually cleans temporary files from local disk and optionally from MinIO.
    """
    temp_dir = "temp_downloads"
    freed_bytes = 0
    removed_count = 0

    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            fp = os.path.join(temp_dir, f)
            if os.path.isfile(fp):
                try:
                    sz = os.path.getsize(fp)
                    os.remove(fp)
                    freed_bytes += sz
                    removed_count += 1
                except Exception:
                    pass

    minio_removed = 0
    if clean_minio:
        try:
            client = MinioStorageClient()
            objects = client.client.list_objects(client.bucket_name, recursive=True)
            for obj in objects:
                client.client.remove_object(client.bucket_name, obj.object_name)
                minio_removed += 1
        except Exception:
            pass

    return {
        "status": "success",
        "local_files_removed": removed_count,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        "minio_objects_removed": minio_removed
    }
