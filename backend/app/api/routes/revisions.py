import json
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.services.llm_service import PROVIDER_CONFIG
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.models import (
    RevisionSession,
    RevisionMessage,
    WorkflowExecution,
    AgentConfig,
    Paper,
    PaperChunk,
)
from app.schemas import (
    RevisionSessionCreate,
    RevisionSessionResponse,
    RevisionMessageCreate,
    RevisionMessageResponse,
)
from app.agents.revision_agent import RevisionAgent

router = APIRouter()

REVISION_SYSTEM_PROMPT = RevisionAgent.system_prompt


async def _build_workflow_context(
    db: AsyncSession, workflow: WorkflowExecution
) -> str:
    parts: list[str] = []

    if workflow.paper_id:
        paper_result = await db.execute(
            select(Paper).where(Paper.id == workflow.paper_id)
        )
        paper = paper_result.scalar_one_or_none()
        if paper:
            info = f"PAPER METADATA:\nTitle: {paper.title}\n"
            if paper.authors:
                info += f"Authors: {', '.join(paper.authors)}\n"
            if paper.doi:
                info += f"DOI: {paper.doi}\n"
            if paper.year:
                info += f"Year: {paper.year}\n"
            if paper.venue:
                info += f"Venue: {paper.venue}\n"
            if paper.abstract:
                info += f"\nABSTRACT:\n{paper.abstract}\n"
            parts.append(info)

            chunks_result = await db.execute(
                select(PaperChunk)
                .where(PaperChunk.paper_id == workflow.paper_id)
                .order_by(PaperChunk.chunk_index)
            )
            chunks = chunks_result.scalars().all()
            if chunks:
                full_text = "\n\n".join(c.text for c in chunks)
                parts.append(f"PAPER FULL TEXT:\n{full_text}")

    if workflow.input_text:
        parts.append(f"ORIGINAL WORKFLOW INPUT:\n{workflow.input_text}")

    if workflow.stages:
        stage_parts = []
        for i, stage in enumerate(workflow.stages):
            output = stage.get("output", "")
            if output:
                role = stage.get("agent_role", "unknown")
                name = stage.get("agent_name", "")
                label = f"{role}" + (f" \u2014 {name}" if name else "")
                stage_parts.append(f"[Stage {i + 1}: {label}]\n{output}")
        if stage_parts:
            parts.append("WORKFLOW STAGE OUTPUTS:\n" + "\n\n".join(stage_parts))

    return "\n\n---\n\n".join(parts)


async def _stream_llm_response(
    messages: list[dict], model: str, provider: str
):
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    base_url = config["base_url"]
    api_key = config["api_key"]

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "max_tokens": 8192,
            },
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise RuntimeError(
                    f"LLM API error {response.status_code}: {body.decode()}"
                )
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload.strip() == "[DONE]":
                    return
                try:
                    obj = json.loads(payload)
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


@router.post("/sessions", response_model=RevisionSessionResponse)
async def create_revision_session(
    data: RevisionSessionCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == data.workflow_execution_id,
            WorkflowExecution.user_id == user_id,
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    session = RevisionSession(
        id=uuid.uuid4(),
        workflow_execution_id=data.workflow_execution_id,
        user_id=user_id,
        agent_config_id=data.agent_config_id,
        title=data.title or f"Revision: {workflow.workflow_name}",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[RevisionSessionResponse])
async def list_revision_sessions(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RevisionSession)
        .where(RevisionSession.user_id == user_id)
        .order_by(desc(RevisionSession.created_at))
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=RevisionSessionResponse)
async def get_revision_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RevisionSession).where(
            RevisionSession.id == session_id,
            RevisionSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[RevisionMessageResponse],
)
async def list_revision_messages(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RevisionSession).where(
            RevisionSession.id == session_id,
            RevisionSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(RevisionMessage)
        .where(RevisionMessage.revision_session_id == session_id)
        .order_by(RevisionMessage.timestamp)
    )
    return msg_result.scalars().all()


@router.post("/sessions/{session_id}/stream")
async def stream_revision_message(
    session_id: uuid.UUID,
    data: RevisionMessageCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RevisionSession)
        .where(
            RevisionSession.id == session_id,
            RevisionSession.user_id == user_id,
        )
        .options(selectinload(RevisionSession.workflow_execution))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = RevisionMessage(
        id=uuid.uuid4(),
        revision_session_id=session_id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)

    model = "google/gemma-4-31b-it:free"
    provider = "openrouter"
    if session.agent_config_id:
        cfg_result = await db.execute(
            select(AgentConfig).where(AgentConfig.id == session.agent_config_id)
        )
        cfg = cfg_result.scalar_one_or_none()
        if cfg:
            model = cfg.model or model
            provider = cfg.provider or provider

    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    workflow_result = await _build_workflow_context(db, session.workflow_execution)

    history_result = await db.execute(
        select(RevisionMessage)
        .where(RevisionMessage.revision_session_id == session_id)
        .order_by(RevisionMessage.timestamp)
    )
    history = history_result.scalars().all()

    llm_messages: list[dict] = [
        {"role": "system", "content": REVISION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"DOCUMENT CONTEXT:\n{workflow_result}\n\n"
                "Please review the above document context. I may ask you to revise, "
                "expand, or improve specific sections of the review."
            ),
        },
    ]
    for m in history:
        llm_messages.append({"role": m.role, "content": m.content})

    async def event_stream():
        full_response = ""
        try:
            async for chunk in _stream_llm_response(llm_messages, model, provider):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            return

        async with AsyncSessionLocal() as save_db:
            assistant_msg = RevisionMessage(
                id=uuid.uuid4(),
                revision_session_id=session_id,
                role="assistant",
                content=full_response,
                extra_metadata={"model": model, "provider": provider},
            )
            save_db.add(assistant_msg)
            await save_db.commit()

        yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_msg.id)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/messages", response_model=RevisionMessageResponse)
async def send_revision_message(
    session_id: uuid.UUID,
    data: RevisionMessageCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.agents.factory import create_agent
    from app.models import AgentRole
    from langchain_core.messages import HumanMessage as LCHumanMessage, AIMessage as LCAIMessage

    result = await db.execute(
        select(RevisionSession)
        .where(
            RevisionSession.id == session_id,
            RevisionSession.user_id == user_id,
        )
        .options(selectinload(RevisionSession.workflow_execution))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = RevisionMessage(
        id=uuid.uuid4(),
        revision_session_id=session_id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)
    await db.flush()

    workflow_result = await _build_workflow_context(db, session.workflow_execution)

    history_result = await db.execute(
        select(RevisionMessage)
        .where(RevisionMessage.revision_session_id == session_id)
        .order_by(RevisionMessage.timestamp)
    )
    history = history_result.scalars().all()

    messages = [LCHumanMessage(content=f"DOCUMENT CONTEXT:\n{workflow_result}\n\n")]
    for m in history:
        if m.role == "user":
            messages.append(LCHumanMessage(content=m.content))
        elif m.role == "assistant":
            messages.append(LCAIMessage(content=m.content))
    messages.append(LCHumanMessage(content=data.content))

    agent_config = None
    if session.agent_config_id:
        cfg_result = await db.execute(
            select(AgentConfig).where(AgentConfig.id == session.agent_config_id)
        )
        agent_config = cfg_result.scalar_one_or_none()

    if agent_config:
        agent = create_agent(
            agent_type=AgentRole.REVISION.value,
            model=agent_config.model,
            provider=agent_config.provider,
            strategy=agent_config.strategy.value if agent_config.strategy else "direct",
            system_prompt=agent_config.system_prompt,
            tools=agent_config.tools or [],
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens,
        )
    else:
        agent = create_agent(
            agent_type=AgentRole.REVISION.value,
            model="google/gemma-4-31b-it:free",
            provider="openrouter",
            strategy="direct",
        )

    agent_result = await agent.run(
        messages=messages,
        context={"workflow_result": workflow_result, "session_id": str(session_id)},
        thread_id=f"revision-{session_id}",
    )

    assistant_content = agent_result.get("output", "")
    if not assistant_content:
        assistant_content = "I apologize, but I was unable to generate a revision. Please try again."

    assistant_msg = RevisionMessage(
        id=uuid.uuid4(),
        revision_session_id=session_id,
        role="assistant",
        content=assistant_content,
        extra_metadata={"agent_type": AgentRole.REVISION.value},
    )
    db.add(assistant_msg)
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(assistant_msg)

    return assistant_msg
