"""Main FastAPI application"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, unipile, supabase, internal, dashboard

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Connect to PostgreSQL database
    from app.db.postgres import db
    try:
        await db.connect()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.warning(f"⚠️ Database connection failed (will retry on first use): {e}")
        # Don't fail startup - database will be lazy-initialized on first access
    
    # Start background worker
    from app.services.worker import start_worker, stop_worker
    start_worker()
    
    yield
    
    # Stop background worker
    stop_worker()
    
    # Disconnect from database
    await db.disconnect()
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(unipile.router)
app.include_router(supabase.router)
app.include_router(internal.router)
app.include_router(dashboard.router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )

