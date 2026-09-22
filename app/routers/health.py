"""Health check and system status routes"""
from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Health check endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@router.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": "2025-10-13T00:00:00Z"  # Will be replaced with actual timestamp
    }


