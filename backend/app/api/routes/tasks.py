"""Task queue health and monitoring endpoints."""

import logging
from fastapi import APIRouter, HTTPException
from app.core.arq import get_arq_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/health")
async def tasks_health():
    try:
        pool = await get_arq_pool()
        await pool.ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Task queue unavailable: {e}")


@router.get("/jobs")
async def list_recent_jobs(limit: int = 20, offset: int = 0):
    """List recent job results from ARQ result store.

    ARQ stores completed job IDs in a sorted set ``arq:job:results``
    and individual results at ``arq:result:{job_id}``.
    """
    pool = await get_arq_pool()
    job_ids = await pool.zrevrange("arq:job:results", offset, offset + limit - 1)
    jobs = []
    for job_id in job_ids:
        result_key = f"arq:result:{job_id}"
        result_data = await pool.hgetall(result_key)
        if result_data:
            decoded = {
                (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                for k, v in result_data.items()
            }
            jobs.append({"job_id": job_id, **decoded})
    return {"jobs": jobs, "total": len(job_ids)}
