from fastapi import APIRouter

from app.api.routes import auth, assets, agents, workspaces, settings, chat, skills, workflows, dashboard, revisions, export_import

router = APIRouter(prefix="/api")

router.include_router(auth.router)
router.include_router(assets.router)
router.include_router(agents.router)
router.include_router(workspaces.router)
router.include_router(settings.router)
router.include_router(chat.router, prefix="/chat")
router.include_router(skills.router, prefix="/skills")
router.include_router(workflows.router, prefix="/workflows")
router.include_router(revisions.router, prefix="/revisions")
router.include_router(dashboard.router)
router.include_router(export_import.router)
