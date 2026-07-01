"""ARQ task for background workflow execution.

Port of ``_run_workflow_background`` from workflows.py. Cancellation is
checked via Redis-backed ``tasks/cancel.py`` instead of the in-memory
``_cancel_flags`` dict. Progress events are published via ProgressManager.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Paper, WorkflowExecution
from app.services.progress import (
    EventType,
    ExecutionEvent,
    get_progress_manager,
)
from app.tasks.cancel import clear_cancel, is_cancelled

logger = logging.getLogger(__name__)

STAGE_TIMEOUT_SECONDS = 1800.0
STAGE_DELAY_SECONDS = 15


async def execute_workflow_task(
    ctx: dict,
    execution_id: str,
    user_id: str,
    workflow_id: str,
    original_context: str,
    pdf_bytes: Optional[bytes],
    paper_s2_id: Optional[str],
    topic_query: Optional[str],
    agent_assignments: dict[str, str],
    paper_content: Optional[str] = None,
    paper_id: Optional[str] = None,
    rubric_standard: str = "general",
) -> dict:
    """Execute a multi-stage LangGraph workflow inside an ARQ worker.

    This function mirrors ``_run_workflow_background`` from workflows.py.
    It is a pure function — no FastAPI imports, no BackgroundTasks, no
    request objects.
    """
    # Lazy import to avoid circular dependency
    from app.api.routes.workflows import (
        WORKFLOW_DEFINITIONS,
        _build_stage_context,
        _get_user_config_by_id,
        _next_progress_event_id,
        _run_stage,
    )

    workflow = WORKFLOW_DEFINITIONS[workflow_id]
    start_time = time.time()

    progress_manager = get_progress_manager()
    exec_uuid = UUID(execution_id) if not isinstance(execution_id, UUID) else execution_id
    await progress_manager.create_execution(exec_uuid)

    try:
        async with AsyncSessionLocal() as db:
            stage_results: list[dict[str, Any]] = []
            prior_findings: list[dict[str, str]] = []
            current_dossier: Any = None

            # Load pre-extracted GROBID metadata from Paper.analysis if paper_id is available.
            # Extraction happens once at upload time in asset_tasks.py — never re-extract in workflows.
            grobid_dict: dict = {}
            if paper_id:
                try:
                    paper_result = await db.execute(
                        select(Paper).where(Paper.id == UUID(paper_id))
                    )
                    paper = paper_result.scalar_one_or_none()
                    if paper and paper.analysis and isinstance(paper.analysis, dict):
                        extraction_meta = paper.analysis.get("extraction_meta")
                        if extraction_meta:
                            grobid_dict = extraction_meta
                            logger.info(
                                "Loaded extraction_meta for paper %s: source=%s refs=%d",
                                paper_id,
                                extraction_meta.get("source", "unknown"),
                                len(extraction_meta.get("references", [])),
                            )
                except Exception as exc:
                    logger.warning("Failed to load extraction_meta for paper %s: %s", paper_id, exc)
            elif pdf_bytes:
                logger.info("No paper_id provided, skipping extraction_meta load")

            for i, stage_def in enumerate(workflow["stages"]):
                if await is_cancelled(execution_id):
                    for r in stage_results:
                        if r.get("status") == "pending":
                            r["status"] = "cancelled"
                            r["output"] = "Cancelled by user."
                    stage_results.append({
                        "agent_role": stage_def["role"],
                        "agent_name": "",
                        "status": "cancelled",
                        "output": "Workflow cancelled by user.",
                        "metadata": {},
                    })
                    await progress_manager.complete_execution(exec_uuid, "cancelled")
                    break

                stage_id = stage_def.get("id")
                config_id_str = agent_assignments.get(stage_id)
                if not config_id_str:
                    stage_results.append({
                        "agent_role": stage_def["role"],
                        "agent_name": "",
                        "status": "error",
                        "output": f"Missing agent assignment for stage: {stage_id}",
                        "metadata": {},
                    })
                    continue

                await progress_manager.publish(
                    exec_uuid,
                    ExecutionEvent(
                        event_id=await _next_progress_event_id(progress_manager, exec_uuid),
                        execution_id=exec_uuid,
                        event_type=EventType.STAGE_STARTED,
                        timestamp=datetime.now(timezone.utc),
                        data={
                            "stage_id": stage_id or f"stage-{i}",
                            "stage_index": i,
                            "agent_role": stage_def.get("role", ""),
                            "agent_name": stage_def.get("agent", ""),
                        },
                    ),
                )

                result = await db.execute(
                    select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
                )
                execution = result.scalar_one_or_none()
                if execution:
                    stages_copy = list(execution.stages) if execution.stages else []
                    while len(stages_copy) <= i:
                        stages_copy.append({
                            "agent_role": stage_def["role"],
                            "agent_name": "",
                            "status": "pending",
                            "output": "",
                            "metadata": {},
                        })
                    stages_copy[i] = {
                        "agent_role": stage_def["role"],
                        "agent_name": "",
                        "status": "running",
                        "output": "",
                        "metadata": {},
                    }
                    execution.stages = stages_copy
                    await db.commit()

                stage_config = await _get_user_config_by_id(db, user_id, UUID(config_id_str))
                stage_context = _build_stage_context(
                    original_context,
                    prior_findings,
                    model=str(stage_config.model) if stage_config else None,
                    output_tokens=stage_config.max_tokens if stage_config else 4096,
                    has_separate_paper_content=bool(paper_content),
                )

                stage_start = time.monotonic()
                try:
                    result = await _run_stage(
                        db, user_id, stage_def, stage_context, UUID(config_id_str),
                        pdf_bytes=pdf_bytes, paper_s2_id=paper_s2_id, topic_query=topic_query,
                        paper_content=paper_content, rubric_standard=rubric_standard,
                        research_dossier=current_dossier,
                        grobid_dict=grobid_dict,
                        progress_manager=progress_manager,
                        execution_id=exec_uuid,
                    )
                except Exception as stage_exc:
                    duration_ms = int((time.monotonic() - stage_start) * 1000)
                    await progress_manager.publish(
                        exec_uuid,
                        ExecutionEvent(
                            event_id=await _next_progress_event_id(progress_manager, exec_uuid),
                            execution_id=exec_uuid,
                            event_type=EventType.STAGE_COMPLETED,
                            timestamp=datetime.now(timezone.utc),
                            data={
                                "stage_id": stage_id or f"stage-{i}",
                                "stage_index": i,
                                "status": "failed",
                                "duration_ms": duration_ms,
                                "error": f"{type(stage_exc).__name__}: {str(stage_exc)[:200]}",
                            },
                        ),
                    )
                    raise

                stage_duration_ms = int((time.monotonic() - stage_start) * 1000)
                stage_status = result.get("status", "completed")
                stage_usage = result.get("metadata", {}).get("usage", {})
                await progress_manager.publish(
                    exec_uuid,
                    ExecutionEvent(
                        event_id=await _next_progress_event_id(progress_manager, exec_uuid),
                        execution_id=exec_uuid,
                        event_type=EventType.STAGE_COMPLETED,
                        timestamp=datetime.now(timezone.utc),
                        data={
                            "stage_id": stage_id or f"stage-{i}",
                            "stage_index": i,
                            "status": stage_status,
                            "duration_ms": stage_duration_ms,
                            "usage": stage_usage,
                            "agent_role": result.get("agent_role", stage_def.get("role", "")),
                            "agent_name": result.get("agent_name", ""),
                        },
                    ),
                )
                current_dossier = result.get("research_dossier") or current_dossier
                result_for_stages = result.copy()
                if hasattr(result_for_stages.get("research_dossier"), "model_dump"):
                    result_for_stages["research_dossier"] = result_for_stages["research_dossier"].model_dump(mode="json")
                stage_results.append(result_for_stages)
                prev_output = result.get("output", "")
                if prev_output:
                    prior_findings.append({
                        "stage": stage_def.get("id", f"stage-{i}"),
                        "role": stage_def["role"],
                        "agent_name": result.get("agent_name", ""),
                        "output": prev_output,
                    })

                result_update = await db.execute(
                    select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
                )
                exec_to_update = result_update.scalar_one_or_none()
                if exec_to_update:
                    stages_copy = list(exec_to_update.stages) if exec_to_update.stages else []
                    while len(stages_copy) <= i:
                        stages_copy.append(result_for_stages)
                    stages_copy[i] = result_for_stages
                    exec_to_update.stages = stages_copy
                    await db.commit()

                if i < len(workflow["stages"]) - 1:
                    await asyncio.sleep(STAGE_DELAY_SECONDS)

            duration = time.time() - start_time
            overall_status = "completed"
            if await is_cancelled(execution_id):
                overall_status = "cancelled"
            else:
                for s in stage_results:
                    if s.get("status") in ("timeout", "error"):
                        overall_status = "partial"
                        break

            total_input = sum(s.get("metadata", {}).get("usage", {}).get("input_tokens", 0) for s in stage_results)
            total_output = sum(s.get("metadata", {}).get("usage", {}).get("output_tokens", 0) for s in stage_results)
            total_tokens = sum(s.get("metadata", {}).get("usage", {}).get("total_tokens", 0) for s in stage_results)
            total_cost = sum(s.get("metadata", {}).get("usage", {}).get("cost_usd", 0.0) for s in stage_results)

            final_result = await db.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )
            final_exec = final_result.scalar_one_or_none()
            if final_exec:
                final_exec.stages = stage_results
                final_exec.status = overall_status
                final_exec.duration_seconds = round(duration, 2)
                await db.commit()

            logger.info(
                "Workflow %s [%s] finished: %s (%.1fs) | tokens: %d+%d=%d | cost: $%.6f",
                workflow_id, execution_id, overall_status, duration,
                total_input, total_output, total_tokens, total_cost,
            )

            if overall_status != "cancelled":
                await progress_manager.complete_execution(exec_uuid, "completed")

    except Exception as e:
        logger.error("Background workflow %s failed: %s", execution_id, e)
        try:
            await progress_manager.complete_execution(exec_uuid, "failed")
        except Exception:
            logger.error("Failed to publish EXECUTION_FAILED for %s", execution_id)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
                )
                exec_obj = result.scalar_one_or_none()
                if exec_obj:
                    exec_obj.status = "error"
                    exec_obj.duration_seconds = round(time.time() - start_time, 2)
                    await db.commit()
        except Exception:
            logger.error("Failed to update error status for %s", execution_id)
    finally:
        await clear_cancel(execution_id)

    return {"status": "completed", "execution_id": execution_id}
