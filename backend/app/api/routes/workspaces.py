from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Workspace, Conversation, Message
from app.schemas import (
    WorkspaceCreate,
    WorkspaceResponse,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


async def _get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    workspace = Workspace(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("/", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Workspace).where(Workspace.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/{workspace_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    workspace_id: UUID,
    data: ConversationCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    ws_result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == current_user.id,
        )
    )
    workspace = ws_result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    conversation = Conversation(
        workspace_id=workspace_id,
        agent_config_id=data.agent_config_id,
        title=data.title,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/{workspace_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    workspace_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Conversation).where(Conversation.workspace_id == workspace_id)
    )
    return result.scalars().all()


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    data: MessageCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    message = Message(
        conversation_id=conversation_id,
        role="user",
        content=data.content,
        extra_metadata=data.extra_metadata or {},
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user = await _get_user(user_id, db)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    )
    return result.scalars().all()
