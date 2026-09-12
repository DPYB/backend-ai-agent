"""FastAPI main application entry point for DPYB backend-ai-agent."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.router import api_router
from app.api.v1.vision import router as vision_router
from app.core.config import settings
from app.infrastructure.core_api_client import get_core_api_client
from app.infrastructure.redis_session import get_redis_session_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
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


app = FastAPI(
    title="DPYB AI Agent Service",
    description=(
        "AI Librarian & Personalization RAG Service for 'Don't Paw-get Your Book'.\n\n"
        "- **Persona-driven LangGraph Handoff**: Russian Blue (차분/지적) & Shoebill (열정/1타강사)\n"
        "- **Personalized RAG**: Supabase pgvector scrap_vector strictly partitioned by member_id\n"
        "- **Book Recommendation**: Tavily Web Search + core-api book metadata + Redis cache"
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
