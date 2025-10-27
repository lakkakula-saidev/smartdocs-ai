"""
SmartDocs AI Backend - Simplified Main Application.

Single FastAPI application entry point with direct AI integration,
simplified configuration, and streamlined architecture.
"""

import time
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Import simplified modules
from config import get_settings
from models import ErrorResponse
from storage import get_document_registry, get_vector_store
from security import SecurityMiddleware, get_security_config, validate_openai_api_key
from logging_config import get_logger, get_performance_logger, get_security_logger
import ai

# Import simplified route modules
from routes import health, upload, chat, documents

# Global state for startup time tracking
_startup_time: float = 0

# Initialize application logger
logger = get_logger("main")
performance_logger = get_performance_logger()
security_logger = get_security_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.
    
    Handles service initialization, vector store setup, health checks,
    and graceful shutdown.
    """
    global _startup_time
    
    # Startup
    _startup_time = time.time()
    
    logger.info("Starting SmartDocs AI Backend...")
    
    try:
        # Get settings and ensure configuration is valid
        settings = get_settings()
        logger.info(f"Configuration loaded: {settings.environment} environment")
        
        # Validate critical security configurations
        if settings.has_openai_key and not validate_openai_api_key(settings.openai_api_key):
            logger.warning("OpenAI API key format validation failed")
        
        if settings.is_production:
            logger.info("Production mode: Enhanced security measures enabled")
            if "*" in settings.cors_origins:
                security_logger.logger.warning("Wildcard CORS origins detected in production")
        
        # Initialize storage components
        logger.info("Initializing storage components...")
        vector_store = get_vector_store()
        document_registry = get_document_registry()
        
        # Perform health checks
        print("[startup] Performing startup health checks...")
        
        # Test AI integration
        try:
            ai_health = await ai.health_check()
            if ai_health.get("status") != "healthy":
                logger.warning(f"AI integration health check failed: {ai_health}")
            else:
                logger.info("AI integration health check passed")
        except Exception as e:
            logger.warning(f"AI health check failed: {e}")
        
        # Test vector store
        try:
            vector_health = await vector_store.health_check()
            if vector_health.get("status") != "healthy":
                logger.warning(f"Vector store health check failed: {vector_health}")
            else:
                logger.info("Vector store health check passed")
        except Exception as e:
            logger.warning(f"Vector store health check failed: {e}")
        
        startup_time_ms = int((time.time() - _startup_time) * 1000)
        logger.info(f"SmartDocs AI Backend startup completed in {startup_time_ms}ms")
        
    except Exception as e:
        logger.error(f"Failed to start SmartDocs AI Backend: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down SmartDocs AI Backend...")
    
    try:
        # Perform cleanup operations
        print("[shutdown] Performing graceful shutdown cleanup...")
        
        shutdown_time_ms = int((time.time() - _startup_time) * 1000)
        print(f"[shutdown] SmartDocs AI Backend shutdown completed (uptime: {shutdown_time_ms}ms)")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    logger.info(f"Creating FastAPI application")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Create FastAPI app with lifespan management
    app = FastAPI(
        title="SmartDocs AI Backend",
        version="0.1.0", 
        description="PDF ingestion and retrieval QA service using FastAPI + OpenAI + ChromaDB",
        debug=settings.debug,
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "health",
                "description": "System health and status monitoring"
            },
            {
                "name": "upload", 
                "description": "Document upload and processing"
            },
            {
                "name": "chat",
                "description": "Question answering and chat interactions"
            },
            {
                "name": "documents",
                "description": "Document management and metadata operations"
            }
        ]
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests with timing and status."""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Log request completion
        process_time_ms = int((time.time() - start_time) * 1000)
        
        print(f"[request] {request.method} {request.url.path} -> {response.status_code} ({process_time_ms}ms)")
        
        return response
    
    # Configure security middleware (before CORS)
    security_config = get_security_config()
    if security_config["enable_security_headers"] or security_config["enable_rate_limiting"]:
        app.add_middleware(
            SecurityMiddleware,
            enable_rate_limiting=security_config["enable_rate_limiting"]
        )
        print(f"[app] Security middleware enabled (rate_limiting={security_config['enable_rate_limiting']})")
    
    # Configure trusted hosts for production
    if settings.is_production:
        # Add trusted hosts middleware for production
        trusted_hosts = ["*.railway.app", "*.onrailway.app"]
        if settings.cors_origins:
            # Extract hosts from CORS origins
            for origin in settings.cors_origins:
                if origin.startswith("https://") or origin.startswith("http://"):
                    host = origin.split("//")[1].split("/")[0]
                    if host not in trusted_hosts:
                        trusted_hosts.append(host)
        
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
        print(f"[app] Trusted hosts middleware enabled: {trusted_hosts}")
    
    # Configure CORS middleware
    cors_origins = settings.cors_origins_list
    print(f"[app] Configuring CORS for origins: {cors_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-API-Key"
        ],
        max_age=settings.cors_max_age,
    )
    
    # Set up global exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with secure error responses."""
        # Log security-relevant HTTP exceptions
        if exc.status_code in [400, 401, 403, 404, 429]:
            client_ip = request.headers.get("x-forwarded-for", "").split(",")[0] or \
                       request.headers.get("x-real-ip", "") or \
                       getattr(request.client, "host", "unknown")
            print(f"[security] HTTP {exc.status_code} from {client_ip}: {request.method} {request.url.path}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=True,
                status_code=exc.status_code,
                message=exc.detail,
                error_code="HTTP_ERROR",
                details={"path": str(request.url.path)} if settings.debug else None
            ).dict(),
            headers=getattr(exc, "headers", None)
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors."""
        # Log error securely (don't expose sensitive details)
        error_id = __import__('secrets').token_hex(8)
        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0] or \
                   request.headers.get("x-real-ip", "") or \
                   getattr(request.client, "host", "unknown")
        
        print(f"[error] Unhandled exception [{error_id}] from {client_ip}: {type(exc).__name__}")
        
        # Only include exception details in development
        error_details = None
        if settings.debug:
            error_details = {
                "path": str(request.url.path),
                "error_type": type(exc).__name__,
                "error_id": error_id
            }
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=True,
                status_code=500,
                message="Internal server error occurred",
                error_code="INTERNAL_ERROR",
                details=error_details,
                request_id=error_id
            ).dict()
        )
    
    # Register route modules
    print("[app] Registering API routes")
    app.include_router(health.router)
    app.include_router(upload.router)
    app.include_router(chat.router)
    app.include_router(documents.router)
    
    # Add diagnostic endpoints for development
    if settings.is_development:
        @app.get("/debug/env")
        async def debug_env():
            """Development-only endpoint for environment diagnostics."""
            registry = get_document_registry()
            
            openai_key = os.getenv("OPENAI_API_KEY", "")
            
            return {
                "openai_key_present": bool(openai_key),
                "openai_key_length": len(openai_key),
                "openai_key_prefix": openai_key[:7] + ("***" if openai_key else ""),
                "openai_key_valid_format": validate_openai_api_key(openai_key) if openai_key else False,
                "environment": settings.environment,
                "debug_mode": settings.debug,
                "vector_store_provider": settings.vector_store_provider,
                "document_count": registry.document_count,
                "last_document_id": registry.last_document_id,
                "security_config": get_security_config(),
                "cors_origins": settings.cors_origins_list,
                "cwd": os.getcwd(),
            }
        
        @app.get("/debug/security")
        async def debug_security():
            """Development-only endpoint for security diagnostics."""
            return {
                "security_headers_enabled": settings.enable_security_headers,
                "rate_limiting_enabled": settings.enable_rate_limiting,
                "cors_credentials": settings.cors_allow_credentials,
                "trusted_environment": settings.is_secure_environment,
                "production_mode": settings.is_production
            }
        
        print("[app] Registered development debug endpoints")
    
    # Add application metadata
    app.state.settings = settings
    app.state.startup_time = _startup_time
    
    print(f"[app] FastAPI application created with {len(app.routes)} routes")
    
    return app


# Create the application instance
app = create_app()


def get_app_info():
    """
    Get application information and metadata.
    
    Returns:
        Dictionary with application information
    """
    settings = get_settings()
    uptime_seconds = int(time.time() - _startup_time) if _startup_time > 0 else 0
    
    return {
        "name": "SmartDocs AI Backend",
        "version": "0.1.0",
        "description": "PDF ingestion and retrieval QA service",
        "environment": settings.environment,
        "debug": settings.debug,
        "uptime_seconds": uptime_seconds,
        "startup_time": _startup_time,
        "vector_store_provider": settings.vector_store_provider
    }


# For direct execution (python main.py)
if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    print(f"Starting SmartDocs AI Backend v0.1.0")
    print(f"Environment: {settings.environment}")
    print(f"Server: http://{settings.host}:{settings.port}")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
        access_log=True
    )