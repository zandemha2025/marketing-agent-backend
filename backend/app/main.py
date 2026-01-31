"""
FastAPI application entry point.
"""
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Rate limiting - temporarily disabled (slowapi not installed)
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Implements OWASP recommended security headers:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    - Strict-Transport-Security: Enforces HTTPS (production only)
    - Content-Security-Policy: Controls resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """

    async def dispatch(self, request: Request, call_next):
        # Skip security headers for CORS preflight to avoid conflicts
        if request.method == "OPTIONS":
            return await call_next(request)
        response: Response = await call_next(request)
        
        # Core security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        # Content Security Policy - basic policy allowing self and common CDNs
        # Adjust based on your frontend requirements
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        # HSTS - only in production with HTTPS
        settings = get_settings()
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response

from .core.config import get_settings
from .core.database import get_database_manager
from .core.audit_middleware import AuditMiddleware
from .core.sso_middleware import SSOMiddleware
from .core.gdpr_middleware import GDPRMiddleware
from .api import router as api_router

# Import models to register them with SQLAlchemy before creating tables
from .models import *  # noqa: F401, F403

# Path to frontend dist - configurable via environment
FRONTEND_DIR = os.environ.get("FRONTEND_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))


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

    # Configure rate limiting - temporarily disabled (slowapi not installed)
    # limiter = Limiter(
    #     key_func=get_remote_address,
    #     default_limits=[f"{settings.rate_limit_requests}/minute"]
    # )
    # app.state.limiter = limiter
    # app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add security headers middleware (runs after CORS on response)
    app.add_middleware(SecurityHeadersMiddleware)

    # Add SSO enforcement middleware
    app.add_middleware(SSOMiddleware)

    # Add audit logging middleware
    app.add_middleware(AuditMiddleware)

    # Add GDPR middleware (must be early to set privacy context)
    if settings.gdpr_enabled:
        app.add_middleware(GDPRMiddleware)

    # Configure CORS - MUST be outermost to handle OPTIONS preflight first
    # In Starlette, middleware added LAST runs FIRST on requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        expose_headers=settings.cors_expose_headers,
        max_age=settings.cors_max_age,
    )

    # Include routers
    app.include_router(api_router, prefix="/api")

    # Health check endpoint (before catch-all)
    @app.get("/health")
    async def health_check():
        """Health check endpoint with comprehensive diagnostics."""
        from fastapi.responses import JSONResponse
        settings = get_settings()
        checks = {
            "status": "healthy",
            "version": "2.0.0",
            "python_version": sys.version,
            "environment": settings.environment,
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        # Check database connection
        try:
            db = get_database_manager()
            async with db.session() as session:
                await session.execute(text("SELECT 1"))
            checks["checks"]["database"] = {"status": "connected", "type": "postgresql" if "postgresql" in settings.database_url else "sqlite"}
        except Exception as e:
            checks["checks"]["database"] = {"status": "error", "error": str(e)}
            checks["status"] = "unhealthy"

        # Check required API keys (don't expose values, just presence)
        api_keys = {
            "openrouter_api_key": settings.openrouter_api_key,
            "firecrawl_api_key": settings.firecrawl_api_key,
            "perplexity_api_key": settings.perplexity_api_key,
            "segmind_api_key": settings.segmind_api_key,
            "elevenlabs_api_key": settings.elevenlabs_api_key,
        }

        for key_name, key_value in api_keys.items():
            checks["checks"][key_name] = "set" if key_value else "MISSING"

        # Check OpenRouter connectivity if key is available
        if settings.openrouter_api_key:
            try:
                from .services.ai import OpenRouterService
                llm = OpenRouterService(api_key=settings.openrouter_api_key)
                connection_test = await llm.test_connection()
                checks["checks"]["openrouter_connection"] = connection_test.get("status", "unknown")
                await llm.close()
            except Exception as e:
                checks["checks"]["openrouter_connection"] = f"error: {str(e)}"
        else:
            checks["checks"]["openrouter_connection"] = "skipped (no key)"

        # If critical keys are missing, mark degraded (not unhealthy - app can still work with limited features)
        if not settings.openrouter_api_key:
            checks["status"] = "degraded"
            checks["degraded_reason"] = "OpenRouter API key missing - AI features unavailable"

        # Determine HTTP status code
        status_code = 200 if checks["status"] in ["healthy", "degraded"] else 503

        return JSONResponse(content=checks, status_code=status_code)

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
