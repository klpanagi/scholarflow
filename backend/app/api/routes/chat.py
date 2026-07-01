import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import get_user
from app.core.security import get_current_user
from app.models import AgentConfig, ChatMessage, ChatSession, Paper, PaperChunk, chat_session_assets_table
from app.schemas import (
    ChatFileUploadResponse,
    ChatForkRequest,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.services.document_extraction import chunk_text, count_tokens, extract_text
from app.services.llm_service import (
    get_available_embedding_models,
    get_available_models,
    stream_completion,
)
from app.services.minio_service import minio_service
from app.services.search_service import search_service
from app.services.system_settings import get_setting

router = APIRouter()


@asynccontextmanager
async def _get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    data: ChatSessionCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_user(user_id, db)

    # Validate the agent config is accessible (global or user's own)
    agent_result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.id == data.agent_config_id,
            (AgentConfig.user_id.is_(None)) | (AgentConfig.user_id == user_id),
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
    if data.agent_config_id is not None:
        agent_result = await db.execute(
            select(AgentConfig).where(
                AgentConfig.id == data.agent_config_id,
                (AgentConfig.user_id.is_(None)) | (AgentConfig.user_id == user_id),
            )
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent config not found")
        session.agent_config_id = agent.id
        session.model = agent.model
        session.provider = agent.provider
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


@router.delete("/sessions")
async def delete_all_sessions(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete every chat session owned by the current user in a single transaction.

    Used by the frontend "Clear all conversations" action. Returns the number of
    sessions that were deleted so the UI can give an accurate success message.
    """
    result = await db.execute(
        delete(ChatSession).where(ChatSession.user_id == user_id)
    )
    deleted = result.rowcount or 0
    await db.commit()
    return {"deleted": deleted}


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

    # D6: inject attached assets via hybrid direct/RAG (respects token budget)
    try:
        budget_str = await get_setting(db, "context_token_budget")
        token_budget = int(budget_str) if budget_str else DEFAULT_TOKEN_BUDGET
    except Exception:
        token_budget = DEFAULT_TOKEN_BUDGET

    if session.attached_assets:
        asset_ctx = await _build_asset_context(
            session.attached_assets,
            db,
            token_budget=token_budget,
            user_query=data.content,
            user_id=user_id,
        )
        if asset_ctx:
            messages.append({"role": "system", "content": asset_ctx})

    for m in history.scalars().all():
        messages.append({"role": m.role, "content": m.content})

    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    async def event_stream():
        full_response = ""
        # Emit 'thinking' immediately so the frontend can show a loading state
        # before any tokens arrive (the agent may take 10-30s to respond).
        yield f"data: {json.dumps({'type': 'thinking'})}\n\n"
        try:
            if session.agent_config is not None:
                try:
                    # D4: ONE agent per chat, dispatched through the registry
                    async for chunk in _stream_via_agent(session, messages, data.content):
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                except Exception as agent_err:
                    # Agent dispatch failed (e.g. unknown role, missing registry entry).
                    # Fall back to generic LLM completion so the user gets a response.
                    logger.warning("Agent dispatch failed, falling back to generic completion: %s", agent_err)
                    async for chunk in stream_completion(session.model, messages, provider=session.provider):
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            else:
                # D7 fallback: legacy session without agent -> generic LLM call
                async for chunk in stream_completion(session.model, messages, provider=session.provider):
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


DEFAULT_TOKEN_BUDGET = 8000
CONTEXT_RESERVE = 2000  # tokens reserved for system prompt + user/assistant history


async def _build_asset_context(
    assets: list[Paper],
    db: AsyncSession,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    user_query: str = "",
    user_id: str | None = None,
) -> str:
    """Inject paper content into LLM context using a hybrid direct/RAG strategy.

    - Loads PaperChunks from the database.
    - If total chunk size is within budget → direct injection.
    - If too large AND a user query is available → RAG via Elasticsearch chunks index.
    - Fallback → truncated direct injection (in paper+chunk order).
    - If no chunks exist → falls back to abstract-only format.
    """
    content_budget = max(500, token_budget - CONTEXT_RESERVE)

    result = await db.execute(
        select(PaperChunk)
        .where(PaperChunk.paper_id.in_([a.id for a in assets]))
        .order_by(PaperChunk.paper_id, PaperChunk.chunk_index)
    )
    all_chunks: list[PaperChunk] = list(result.scalars().all())

    if not all_chunks:
        return _abstracts_only(assets)

    total_estimate = sum(count_tokens(c.text) for c in all_chunks)

    # RAG path: content too large for direct + we have a searchable query
    if total_estimate > content_budget and user_query and user_id:
        try:
            return await _rag_context(assets, user_query, user_id, content_budget)
        except Exception as exc:
            logger.warning("RAG context build failed, falling back to direct: %s", exc)

    # Direct injection (with truncation if needed)
    return _chunks_context(assets, all_chunks, content_budget)


def _abstracts_only(assets: list[Paper]) -> str:
    """Fallback when no PaperChunks exist — format only metadata + abstract."""
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


def _chunks_context(assets: list[Paper], chunks: list[PaperChunk], budget: int) -> str:
    """Format paper chunks into a single context string, truncating to budget."""
    paper_map = {str(a.id): a for a in assets}
    chunks_by_paper: dict[str, list[PaperChunk]] = {}
    for c in chunks:
        chunks_by_paper.setdefault(str(c.paper_id), []).append(c)

    consumed = 0
    sections: list[str] = []
    header = (
        "The user has attached the following documents for context."
        " Use them when relevant, but do not fabricate details not present in the documents.\n"
    )

    for idx, (pid, cks) in enumerate(chunks_by_paper.items(), start=1):
        asset = paper_map.get(pid)
        label = f"[{idx}] {asset.title}" if asset else f"[{idx}] Paper"
        if asset and asset.authors:
            label += f" -- {', '.join(asset.authors[:3])}"
        if asset and asset.year:
            label += f" ({asset.year})"

        chunk_parts: list[str] = []
        for c in cks:
            token_count = count_tokens(c.text)
            if consumed + token_count > budget:
                break
            chunk_parts.append(c.text)
            consumed += token_count
            if consumed >= budget:
                break

        if chunk_parts:
            sections.append(label + "\n" + "\n\n".join(chunk_parts))

        if consumed >= budget:
            break

    if not sections:
        return _abstracts_only(assets)

    return header + "\n---\n".join(sections)


async def _rag_context(assets: list[Paper], user_query: str, user_id: str, budget: int) -> str:
    """Build context via RAG: search relevant chunks in Elasticsearch."""
    header = (
        "The user has attached the following documents for context."
        " Use them when relevant, but do not fabricate details not present in the documents.\n"
    )
    paper_map = {str(a.id): a for a in assets}

    # Generate embedding for the user's query
    embedding = await search_service.embed_text(user_query)

    # Search the chunks index, filtered to these assets
    es_results = await search_service.search(
        query=user_query,
        index=settings.ELASTICSEARCH_PAPERS_INDEX,
        limit=20,
        owner_filter=user_id,
        embedding=embedding,
    )

    snippets: list[str] = []
    seen = set()
    consumed = 0
    for hit in es_results:
        doc = hit["document"]
        chunk_text = doc.get("content") or doc.get("text") or ""
        asset_id = doc.get("asset_id", "")
        # Deduplicate by content hash
        content_key = chunk_text[:100]
        if content_key in seen:
            continue
        seen.add(content_key)

        asset = paper_map.get(asset_id)
        label = f"[{len(snippets) + 1}] {asset.title}" if asset else f"[{len(snippets) + 1}]"
        if asset and asset.authors:
            label += f" -- {', '.join(asset.authors[:3])}"

        token_count = count_tokens(chunk_text)
        if consumed + token_count > budget:
            break

        snippets.append(label + "\n" + chunk_text)
        consumed += token_count

    if not snippets:
        return ""

    return header + "\n---\n".join(snippets)


async def _stream_via_agent(
    session: ChatSession, messages: list[dict], user_text: str
):
    """Dispatch through the agent registry. Yields raw text chunks."""
    from app.agents.factory import build_agent_from_config
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    agent, _ = build_agent_from_config(session.agent_config)

    lc_messages = []
    for m in messages:
        if m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))
        elif m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

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

    # Extract text content and store as a system message for LLM context
    extracted = extract_text(content, file.filename)
    if extracted:
        chunks = chunk_text(extracted)
        for i, chunk in enumerate(chunks):
            file_msg = ChatMessage(
                id=uuid.uuid4(),
                session_id=session_id,
                role="system",
                content=chunk,
                file_key=object_key,
                file_name=file.filename,
                extra_metadata={
                    "type": "file_content",
                    "content_chunk": True,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            db.add(file_msg)
        await db.commit()
        logger.info(
            "Extracted %d chars from %s -> %d chunks",
            len(extracted), file.filename, len(chunks),
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
