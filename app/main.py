"""FastAPI main application entry point for DPYB backend-ai-agent."""

import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.router import api_router
from app.api.v1.memory import router as memory_router
from app.api.v1.memory import vectors_router
from app.api.v1.reports import router as reports_router
from app.api.v1.vision import router as vision_router
from app.core.config import settings
from app.infrastructure.core_api_client import get_core_api_client
from app.infrastructure.redis_session import get_redis_session_manager

# Configure dual logging: console (stdout) + rotating file (logs/app.log)
log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
os.makedirs("logs", exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Add handlers if not already present
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)

if not any(
    isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
    for h in root_logger.handlers
):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

logger = logging.getLogger("backend-ai-agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for external service connections."""
    logger.info("Initializing backend-ai-agent services...")
    # Initialize Redis connection
    redis_mgr = get_redis_session_manager()
    await redis_mgr.connect()

    yield

    logger.info("Shutting down backend-ai-agent services...")
    await redis_mgr.disconnect()
    core_api_client = get_core_api_client()
    await core_api_client.close()
    from app.infrastructure.db.session import get_async_engine

    engine = get_async_engine()
    if engine:
        await engine.dispose()


app = FastAPI(
    title="DPYB AI Agent Service",
    description=(
        "AI Librarian & Personalization RAG Service for 'Don't Paw-get Your Book'.\n\n"
        "- **Persona-driven LangGraph Handoff**: Russian Blue (차분/지적) & Shoebill (열정/1타강사)\n"
        "- **Personalized RAG**: Supabase pgvector scrap_vector strictly partitioned by member_id\n"
        "- **Book Recommendation**: Tavily Web Search + National Library verification + Redis cache"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(api_router)
app.include_router(vision_router)
app.include_router(memory_router)
app.include_router(vectors_router)
app.include_router(reports_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check_root():
    """Root-level health check endpoint for Central .github Keep-Alive."""
    from app.api.router import health_check

    return await health_check()


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root path to Swagger UI documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=(settings.app_env == "development"),
    )
