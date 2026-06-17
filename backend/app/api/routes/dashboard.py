"""Dashboard statistics endpoint.

Aggregates counts and recent activity for the user dashboard.
Returns lightweight data needed for the landing page without
requiring the frontend to make multiple API calls.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    AgentConfig,
    ChatSession,
    Conversation,
    Paper,
    User,
    Workspace,
    WorkflowExecution,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _get_user(user_id: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.get("/stats")
async def get_dashboard_stats(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate dashboard statistics for the current user."""
    user = await _get_user(user_id, db)
    if not user:
        return {
            "assets_count": 0,
            "conversations_count": 0,
            "workspaces_count": 0,
            "agents_count": 0,
            "workflow_executions_count": 0,
            "recent_assets": [],
            "recent_conversations": [],
            "recent_executions": [],
            "tag_breakdown": [],
            "monthly_activity": [],
        }

    # Counts: assets, workspaces, agent configs, workflow executions
    assets_count = await db.scalar(
        select(func.count(Paper.id)).where(Paper.owner_id == user.id)
    )
    workspaces_count = await db.scalar(
        select(func.count(Workspace.id)).where(Workspace.user_id == user.id)
    )
    agents_count = await db.scalar(
        select(func.count(AgentConfig.id)).where(AgentConfig.user_id == user.id)
    )
    executions_count = await db.scalar(
        select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.user_id == user.id
        )
    )

    # Conversations: top-level ChatSessions + Workspace.Conversations
    chat_sessions_count = await db.scalar(
        select(func.count(ChatSession.id)).where(ChatSession.user_id == user.id)
    )
    # Workspace conversations: count conversations whose workspace belongs to user
    ws_conversations_count = await db.scalar(
        select(func.count(Conversation.id))
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .where(Workspace.user_id == user.id)
    )
    conversations_count = (chat_sessions_count or 0) + (ws_conversations_count or 0)

    # Recent assets (top 5)
    assets_rows = await db.execute(
        select(Paper)
        .where(Paper.owner_id == user.id)
        .order_by(Paper.created_at.desc())
        .limit(5)
    )
    recent_assets = [
        {
            "id": str(p.id),
            "title": p.title,
            "authors": list(p.authors or []),
            "year": p.year,
            "venue": p.venue,
            "doc_type": p.doc_type,
            "tags": list(p.tags or []),
            "analysis": p.analysis,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in assets_rows.scalars()
    ]

    # Recent chat sessions (top 5)
    sessions_rows = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(5)
    )
    recent_sessions = [
        {
            "id": str(s.id),
            "title": s.title,
            "model": s.model,
            "provider": s.provider,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions_rows.scalars()
    ]

    # Recent workspace conversations (top 5)
    ws_convs_rows = await db.execute(
        select(Conversation)
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .where(Workspace.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(5)
    )
    recent_ws_conversations = [
        {
            "id": str(c.id),
            "title": c.title,
            "workspace_id": str(c.workspace_id),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in ws_convs_rows.scalars()
    ]

    # Recent workflow executions (top 5)
    executions_rows = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.user_id == user.id)
        .order_by(WorkflowExecution.created_at.desc())
        .limit(5)
    )
    recent_executions = [
        {
            "id": str(e.id),
            "workflow_id": e.workflow_id,
            "status": e.status,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in executions_rows.scalars()
    ]

    # Tag breakdown: count assets per tag (top 8 tags)
    tag_rows = await db.execute(
        select(Paper.tags).where(Paper.owner_id == user.id)
    )
    tag_counter: dict[str, int] = {}
    for (tags,) in tag_rows:
        for t in tags or []:
            tag_counter[t] = tag_counter.get(t, 0) + 1
    tag_breakdown = [
        {"tag": tag, "count": count}
        for tag, count in sorted(
            tag_counter.items(), key=lambda x: x[1], reverse=True
        )[:8]
    ]

    # Monthly activity: assets added per month for last 6 months
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=180)
    monthly_rows = await db.execute(
        select(Paper.created_at).where(
            Paper.owner_id == user.id, Paper.created_at >= six_months_ago
        )
    )
    monthly_counter: dict[str, int] = {}
    for (created_at,) in monthly_rows:
        if not created_at:
            continue
        key = created_at.strftime("%Y-%m")
        monthly_counter[key] = monthly_counter.get(key, 0) + 1

    # Fill last 6 months with zeros if missing
    monthly_activity = []
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=30 * i)
        key = month_date.strftime("%Y-%m")
        monthly_activity.append(
            {
                "month": key,
                "label": month_date.strftime("%b"),
                "count": monthly_counter.get(key, 0),
            }
        )

    return {
        "assets_count": assets_count or 0,
        "conversations_count": conversations_count,
        "workspaces_count": workspaces_count or 0,
        "agents_count": agents_count or 0,
        "workflow_executions_count": executions_count or 0,
        "recent_assets": recent_assets,
        "recent_sessions": recent_sessions,
        "recent_ws_conversations": recent_ws_conversations,
        "recent_executions": recent_executions,
        "tag_breakdown": tag_breakdown,
        "monthly_activity": monthly_activity,
    }