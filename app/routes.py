from fastapi import APIRouter

from app.handlers import health, jobs

router = APIRouter()

# Include routers from handlers
router.include_router(health.router)
router.include_router(jobs.router)
