"""ARQ WorkerSettings for asset and workflow workers."""

import logging
from arq.connections import RedisSettings
from app.core.config import settings
from app.tasks.asset_tasks import process_asset_task  # type: ignore[reportMissingImports]
from app.tasks.workflow_tasks import execute_workflow_task  # type: ignore[reportMissingImports]

logger = logging.getLogger(__name__)

_BASE_REDIS_SETTINGS = RedisSettings(
    host=str(settings.REDIS_URL.host or "localhost"),
    port=settings.REDIS_URL.port or 6379,
    database=1,
)


async def _log_job_start(ctx: dict) -> None:
    logger.info("Job started: %s (try %d)", ctx["job_id"], ctx.get("job_try", 1))


async def _log_job_complete(ctx: dict) -> None:
    logger.info("Job completed: %s", ctx["job_id"])


async def _log_job_failed(ctx: dict) -> None:
    logger.error("Job failed: %s (try %d)", ctx["job_id"], ctx.get("job_try", 1))


class AssetWorkerSettings:
    functions = [process_asset_task]
    redis_settings = _BASE_REDIS_SETTINGS
    max_burst_jobs = 2
    job_timeout = 600
    max_retries = 3
    keep_result = 86400
    keep_result_failed = 86400
    poll_delay = 0.5
    on_job_start = _log_job_start
    on_job_complete = _log_job_complete
    on_job_failed = _log_job_failed


class WorkflowWorkerSettings:
    functions = [execute_workflow_task]
    redis_settings = _BASE_REDIS_SETTINGS
    max_burst_jobs = 4
    job_timeout = 3600
    max_retries = 2
    keep_result = 86400
    keep_result_failed = 86400
    poll_delay = 0.5
    on_job_start = _log_job_start
    on_job_complete = _log_job_complete
    on_job_failed = _log_job_failed
