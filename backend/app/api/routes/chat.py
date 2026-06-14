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
from app.models import ChatMessage, ChatSession, User
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
    session = ChatSession(
        id=uuid.uuid4(),
        user_id=user_id,
        title=data.title,
        model=data.model,
        provider=data.provider,
        system_prompt=data.system_prompt,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
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
    return session


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
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .options(selectinload(ChatSession.messages))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role="user",
        content=data.content,
        parent_message_id=data.parent_message_id,
    )
    db.add(user_msg)
    await db.flush()

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp)
    )
    messages = []
    if session.system_prompt:
        messages.append({"role": "system", "content": session.system_prompt})
    for m in history_result.scalars().all():
        messages.append({"role": m.role, "content": m.content})

    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    provider = session.provider
    model = session.model

    async def event_stream():
        full_response = ""
        try:
            async for chunk in _stream_completion(messages, model, provider):
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

    await db.commit()
    await db.refresh(new_session)
    return new_session


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
