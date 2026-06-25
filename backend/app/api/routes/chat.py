import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.models import AgentConfig, ChatMessage, ChatSession, Paper, User, chat_session_assets_table
from app.schemas import (
    ChatFileUploadResponse,
    ChatForkRequest,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.services.llm_service import get_available_models, get_available_embedding_models, PROVIDER_CONFIG
from app.services.minio_service import minio_service

router = APIRouter()


async def _get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@asynccontextmanager
async def _get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


async def _stream_completion(messages: list[dict], model: str, provider: str):
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    import httpx

    base_url = config["base_url"]
    api_key = config["api_key"]

    async with httpx.AsyncClient(timeout=120.0) as client:
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
                "max_tokens": 4096,
            },
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                raise RuntimeError(
                    f"LLM API error {response.status_code}: {error_body.decode()}"
                )
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    return
                try:
                    obj = json.loads(data)
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    data: ChatSessionCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user(user_id, db)

    # Validate the agent belongs to the user (G1)
    agent_result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.id == data.agent_config_id,
            AgentConfig.user_id == user_id,
        )
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent config not found")

    # Enforce hard cap of 20 assets (R3)
    if len(data.asset_ids) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 assets per chat session",
        )

    # Validate assets (if any) belong to the user
    if data.asset_ids:
        assets_result = await db.execute(
            select(Paper).where(
                Paper.id.in_(data.asset_ids),
                Paper.owner_id == user_id,
            )
        )
        found = {a.id for a in assets_result.scalars().all()}
        missing = [str(aid) for aid in data.asset_ids if aid not in found]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Assets not found or not owned: {missing}",
            )

    session = ChatSession(
        id=uuid.uuid4(),
        user_id=user_id,
        title=data.title,
        model=agent.model,                  # copy from agent — agent wins
        provider=agent.provider,
        system_prompt=data.system_prompt,
        agent_config_id=agent.id,
    )
    db.add(session)

    if data.asset_ids:
        # Insert join rows directly (cheaper than loading Paper objects)
        await db.flush()
        for aid in data.asset_ids:
            await db.execute(
                chat_session_assets_table.insert().values(
                    chat_session_id=session.id,
                    asset_id=aid,
                )
            )

    await db.commit()
    await db.refresh(session)

    # Re-load with attached_assets so the response includes asset_ids
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.attached_assets))
        .where(ChatSession.id == session.id)
    )
    loaded = result.scalar_one()
    return ChatSessionResponse(
        id=loaded.id, title=loaded.title, model=loaded.model,
        provider=loaded.provider, system_prompt=loaded.system_prompt,
        agent_config_id=loaded.agent_config_id,
        asset_ids=[a.id for a in loaded.attached_assets],
        created_at=loaded.created_at, updated_at=loaded.updated_at,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.attached_assets))
        .where(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
    )
    sessions = result.scalars().all()
    return [
        ChatSessionResponse(
            id=s.id, title=s.title, model=s.model, provider=s.provider,
            system_prompt=s.system_prompt,
            agent_config_id=s.agent_config_id,
            asset_ids=[a.id for a in s.attached_assets],
            created_at=s.created_at, updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.attached_assets))
        .where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatSessionResponse(
        id=session.id, title=session.title, model=session.model,
        provider=session.provider, system_prompt=session.system_prompt,
        agent_config_id=session.agent_config_id,
        asset_ids=[a.id for a in session.attached_assets],
        created_at=session.created_at, updated_at=session.updated_at,
    )


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: uuid.UUID,
    data: ChatSessionUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if data.title is not None:
        session.title = data.title
    if data.model is not None:
        session.model = data.model
    if data.provider is not None:
        session.provider = data.provider
    if data.system_prompt is not None:
        session.system_prompt = data.system_prompt
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return {"ok": True}


@router.get(
    "/sessions/{session_id}/messages", response_model=list[ChatMessageResponse]
)
async def list_messages(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp)
    )
    return result.scalars().all()


@router.post(
    "/sessions/{session_id}/messages", response_model=ChatMessageResponse
)
async def create_user_message(
    session_id: uuid.UUID,
    data: ChatMessageCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role="user",
        content=data.content,
        parent_message_id=data.parent_message_id,
    )
    db.add(msg)
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.post("/sessions/{session_id}/stream")
async def stream_chat(
    session_id: uuid.UUID,
    data: ChatMessageCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Load session + agent + assets in one go
    result = await db.execute(
        select(ChatSession)
        .options(
            selectinload(ChatSession.attached_assets),
            selectinload(ChatSession.agent_config).selectinload(AgentConfig.skills),
        )
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Persist user message first (unchanged)
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role="user",
        content=data.content,
        parent_message_id=data.parent_message_id,
    )
    db.add(user_msg)
    await db.flush()

    # Build the message array
    history = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp)
    )
    messages: list[dict] = []
    if session.system_prompt:
        messages.append({"role": "system", "content": session.system_prompt})

    # D6: inject attached assets as a system message prefix per-request
    if session.attached_assets:
        asset_ctx = _build_asset_context(session.attached_assets)
        if asset_ctx:
            messages.append({"role": "system", "content": asset_ctx})

    for m in history.scalars().all():
        messages.append({"role": m.role, "content": m.content})

    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    async def event_stream():
        full_response = ""
        try:
            if session.agent_config is not None:
                # D4: ONE agent per chat, dispatched through the registry
                async for chunk in _stream_via_agent(session, messages, data.content):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            else:
                # D7 fallback: legacy session without agent -> generic LLM call
                async for chunk in _stream_completion(messages, session.model, session.provider):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            return

        async with _get_db_session() as save_db:
            assistant_msg = ChatMessage(
                id=uuid.uuid4(),
                session_id=session_id,
                role="assistant",
                content=full_response,
            )
            save_db.add(assistant_msg)
            await save_db.commit()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _build_asset_context(assets: list[Paper]) -> str:
    """Format attached assets for the LLM. Truncates per-asset to keep token budget sane."""
    parts: list[str] = [
        "The user has attached the following documents for context."
        " Use them when relevant, but do not fabricate details not present in the documents.\n"
    ]
    for i, a in enumerate(assets, start=1):
        abstract = (a.abstract or "").strip()
        if len(abstract) > 1500:
            abstract = abstract[:1500] + "..."
        parts.append(
            f"[{i}] {a.title}"
            + (f" -- {', '.join((a.authors or [])[:3])}" if a.authors else "")
            + (f" ({a.year})" if a.year else "")
            + (f"\n    {abstract}" if abstract else "")
        )
    return "\n".join(parts)


async def _stream_via_agent(
    session: ChatSession, messages: list[dict], user_text: str
):
    """Dispatch through the agent registry. Yields raw text chunks."""
    from app.agents.factory import create_agent
    from app.tools import get_tools_by_names
    from langchain_core.messages import HumanMessage, SystemMessage

    agent_cfg = session.agent_config
    skill_tools: list[str] = list(agent_cfg.tools or [])
    skill_prompts: list[str] = []
    for sk in agent_cfg.skills:
        if sk.prompt_template:
            skill_prompts.append(sk.prompt_template)
        if sk.builtin_tools:
            skill_tools.extend(sk.builtin_tools)

    system_prompt = agent_cfg.system_prompt
    if skill_prompts:
        system_prompt = "\n\n".join(filter(None, [system_prompt] + skill_prompts))

    resolved_tools = get_tools_by_names(skill_tools) if skill_tools else []

    agent = create_agent(
        agent_type=agent_cfg.role.value,
        model=agent_cfg.model,
        provider=agent_cfg.provider,
        strategy=agent_cfg.strategy.value if hasattr(agent_cfg.strategy, "value") else agent_cfg.strategy,
        system_prompt=system_prompt,
        tools=resolved_tools,
        temperature=agent_cfg.temperature,
        max_tokens=agent_cfg.max_tokens,
        variant=agent_cfg.variant.value if hasattr(agent_cfg.variant, "value") else agent_cfg.variant,
    )

    lc_messages = []
    for m in messages:
        if m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))
        elif m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        # assistant/tool messages in history are ignored for v1; agent builds its own

    result = await agent.run(messages=lc_messages, context={}, thread_id=str(session.id))
    output = result.get("output", "")
    # Yield in small chunks to mimic streaming UX (agents don't stream by default)
    chunk_size = 32
    for i in range(0, len(output), chunk_size):
        yield output[i : i + chunk_size]


@router.post("/sessions/{session_id}/fork", response_model=ChatSessionResponse)
async def fork_session(
    session_id: uuid.UUID,
    data: ChatForkRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp)
    )
    all_messages = msg_result.scalars().all()

    fork_idx = None
    for i, m in enumerate(all_messages):
        if m.id == data.from_message_id:
            fork_idx = i
            break

    if fork_idx is None:
        raise HTTPException(
            status_code=404, detail="Message not found in session"
        )

    fork_messages = all_messages[: fork_idx + 1]

    new_title = data.title or f"Fork: {original.title or 'Untitled'}"
    new_session = ChatSession(
        id=uuid.uuid4(),
        user_id=user_id,
        title=new_title,
        model=original.model,
        provider=original.provider,
        system_prompt=original.system_prompt,
        agent_config_id=original.agent_config_id,
    )
    db.add(new_session)
    await db.flush()

    id_map = {}
    for msg in fork_messages:
        new_id = uuid.uuid4()
        id_map[msg.id] = new_id
        new_msg = ChatMessage(
            id=new_id,
            session_id=new_session.id,
            role=msg.role,
            content=msg.content,
            file_key=msg.file_key,
            file_name=msg.file_name,
            parent_message_id=id_map.get(msg.parent_message_id),
            extra_metadata=msg.extra_metadata,
        )
        db.add(new_msg)

    # Copy attached assets from original session
    if original.attached_assets:
        for asset in original.attached_assets:
            await db.execute(
                chat_session_assets_table.insert().values(
                    chat_session_id=new_session.id,
                    asset_id=asset.id,
                )
            )
    await db.commit()
    # Re-load with attached_assets so the response includes asset_ids
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.attached_assets))
        .where(ChatSession.id == new_session.id)
    )
    loaded = result.scalar_one()
    return ChatSessionResponse(
        id=loaded.id, title=loaded.title, model=loaded.model,
        provider=loaded.provider, system_prompt=loaded.system_prompt,
        agent_config_id=loaded.agent_config_id,
        asset_ids=[a.id for a in loaded.attached_assets],
        created_at=loaded.created_at, updated_at=loaded.updated_at,
    )


@router.post(
    "/sessions/{session_id}/upload", response_model=ChatFileUploadResponse
)
async def upload_file(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    object_key = f"chat/{session_id}/{uuid.uuid4().hex}.{ext}"

    content = await file.read()
    await minio_service.upload_file(
        BytesIO(content),
        object_key,
        content_type=file.content_type or "application/octet-stream",
    )

    return ChatFileUploadResponse(file_key=object_key, file_name=file.filename)


@router.get("/models")
async def list_chat_models(
    user_id: str = Depends(get_current_user),
):
    models = await get_available_models()
    return models


@router.get("/embedding-models")
async def list_embedding_models(
    user_id: str = Depends(get_current_user),
):
    models = await get_available_embedding_models()
    return models
