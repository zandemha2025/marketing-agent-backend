"""
FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .core.config import get_settings
from .core.database import get_database_manager
from .api import router as api_router

# Import models to register them with SQLAlchemy before creating tables
from .models import *  # noqa: F401, F403

# Path to frontend dist (relative to project root)
FRONTEND_DIR = "/sessions/blissful-focused-dijkstra/mnt/workflow/frontend/dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    db = get_database_manager()

    # Create tables if they don't exist (safe no-op if already created)
    await db.create_tables()

    yield

    # Shutdown
    await db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered Marketing Campaign Platform",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix="/api")

    # Health check endpoint (before catch-all)
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "2.0.0"}

    # Serve frontend static files if available
    if os.path.exists(FRONTEND_DIR):
        # Mount static assets
        assets_dir = os.path.join(FRONTEND_DIR, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="static")

        # Explicit root route
        @app.get("/")
        async def serve_root():
            """Serve index.html for root path."""
            index_path = os.path.join(FRONTEND_DIR, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return {"error": "Frontend not built"}

        # Catch-all route for SPA - serve index.html for any non-API route
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve the SPA for any non-API routes."""
            # Skip API and system routes
            if full_path.startswith(("api/", "docs", "redoc", "openapi", "health")):
                return {"error": "Not found"}
            # Check if it's a static file
            file_path = os.path.join(FRONTEND_DIR, full_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)
            # Otherwise serve index.html for SPA routing
            index_path = os.path.join(FRONTEND_DIR, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return {"error": "Frontend not built"}

    return app


# Create app instance
app = create_app()
