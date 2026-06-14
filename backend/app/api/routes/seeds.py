from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.seeds.niobe_skills import seed_all

router = APIRouter()


@router.post("/niobe")
async def run_niobe_seed(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await seed_all(db, user_id)
    return {
        "status": "ok",
        "message": f"Seeded {result['skills_created']} skills and {len(result['agent_configs'])} agent configs",
        **result,
    }
