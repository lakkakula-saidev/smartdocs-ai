"""
SmartDocs AI Backend - Modular FastAPI Application Factory.

This module provides the main FastAPI application factory with proper
dependency injection, configuration management, and modular architecture.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .logger import setup_logging, get_logger, LogContext
from .exceptions import setup_exception_handlers
from .db.vector_store import get_vector_store, get_document_registry
from .routes import health, upload, chat, rename, documents

# Global state for startup time tracking
_startup_time: float = 0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.
    
    Handles:
    - Service initialization
    - Vector store setup
    - Health checks
    - Graceful shutdown
    """
    global _startup_time
    logger = get_logger("lifespan")
    
    # Startup
    _startup_time = time.time()
    
    with LogContext(stage="startup"):
        logger.info("Starting SmartDocs AI Backend...")
        
        try:
            # Get settings and ensure configuration is valid
            settings = get_settings()
            logger.info(
                "Configuration loaded successfully",
                extra={
                    "environment": settings.environment.value,
                    "vector_store": settings.vector_store_provider.value,
                    "debug": settings.debug
                }
            )
            
            # Initialize vector store and document registry
            logger.info("Initializing vector store...")
            vector_store = get_vector_store()
            document_registry = get_document_registry()
            
            # Perform health checks
            logger.info("Performing startup health checks...")
            vector_health = await vector_store.health_check()
            registry_health = await document_registry.health_check()
            
            if vector_health.get("status") != "healthy":
                logger.warning(
                    "Vector store health check failed",
                    extra=vector_health
                )
            
            startup_time_ms = int((time.time() - _startup_time) * 1000)
            logger.info(
                "SmartDocs AI Backend startup completed successfully",
                extra={
                    "startup_time_ms": startup_time_ms,
                    "vector_store_status": vector_health.get("status"),
                    "document_count": registry_health.get("document_count", 0)
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to start SmartDocs AI Backend",
                extra={"error": str(e)},
                exc_info=True
            )
            raise
    
    yield
    
    # Shutdown
    with LogContext(stage="shutdown"):
        logger.info("Shutting down SmartDocs AI Backend...")
        
        try:
            # Perform cleanup operations
            logger.info("Performing graceful shutdown cleanup...")
            
            # Additional cleanup can be added here
            # For example: closing database connections, saving state, etc.
            
            shutdown_time_ms = int((time.time() - _startup_time) * 1000)
            logger.info(
                "SmartDocs AI Backend shutdown completed",
                extra={"total_uptime_ms": shutdown_time_ms}
            )
            
        except Exception as e:
            logger.error(
                "Error during shutdown",
                extra={"error": str(e)},
                exc_info=True
            )


def create_app(settings: Settings = None) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    This is the main application factory that:
    - Sets up logging
    - Configures middleware
    - Registers routes
    - Sets up exception handlers
    - Configures dependency injection
    
    Args:
        settings: Optional settings override (useful for testing)
        
    Returns:
        Configured FastAPI application instance
    """
    # Use provided settings or load from environment
    if settings is None:
        settings = get_settings()
    
    # Setup logging first
    setup_logging(
        log_level=settings.log_level.value,
        log_format=settings.log_format
    )
    
    logger = get_logger("app_factory")
    
    with LogContext(component="app_factory"):
        logger.info(
            "Creating FastAPI application",
            extra={
                "app_name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment.value
            }
        )
        
        # Create FastAPI app with lifespan management
        app = FastAPI(
            title=settings.app_name,
            version=settings.app_version,
            description=settings.app_description,
            debug=settings.debug,
            lifespan=lifespan,
            # OpenAPI configuration
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
            
            logger.info(
                f"{request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time_ms": process_time_ms,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            )
            
            return response
        
        # Configure CORS middleware
        logger.info(
            "Configuring CORS middleware",
            extra={
                "allowed_origins": settings.cors_origins,
                "allow_credentials": settings.cors_allow_credentials
            }
        )
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Set up exception handlers
        logger.info("Setting up exception handlers")
        setup_exception_handlers(app)
        
        # Register route modules
        logger.info("Registering API routes")
        app.include_router(health.router)
        app.include_router(upload.router)
        app.include_router(chat.router)
        app.include_router(rename.router)
        app.include_router(documents.router)
        
        # Add diagnostic endpoints for development
        if settings.is_development:
            @app.get("/debug/env")
            async def debug_env():
                """
                Development-only endpoint for environment diagnostics.
                Returns masked diagnostics about configuration state.
                """
                import os
                from .db.vector_store import get_document_registry
                
                key = os.getenv("OPENAI_API_KEY", "")
                registry = get_document_registry()
                
                return {
                    "openai_key_present": bool(key),
                    "openai_key_length": len(key),
                    "openai_key_prefix": key[:7] + ("***" if key else ""),
                    "environment": settings.environment.value,
                    "debug_mode": settings.debug,
                    "vector_store_provider": settings.vector_store_provider.value,
                    "document_count": registry.document_count,
                    "last_document_id": registry.last_document_id,
                    "cwd": os.getcwd(),
                }
            
            logger.info("Registered development debug endpoints")
        
        # Add application metadata
        app.state.settings = settings
        app.state.startup_time = _startup_time
        
        logger.info(
            "FastAPI application created successfully",
            extra={
                "routes_count": len(app.routes),
                "debug_mode": settings.debug
            }
        )
        
        return app


# Application instance cache for module-level access
_app_cache: FastAPI = None


def get_application() -> FastAPI:
    """
    Get the configured FastAPI application instance.
    
    This function provides a single point of access to the application
    and can be used by ASGI servers like Uvicorn. Uses caching to prevent
    duplicate app creation during imports.
    
    Returns:
        Configured FastAPI application
    """
    global _app_cache
    if _app_cache is None:
        _app_cache = create_app()
    return _app_cache


# Create the application instance for module-level access (lazy)
app = get_application()


def get_app_info() -> Dict[str, Any]:
    """
    Get application information and metadata.
    
    Returns:
        Dictionary with application information
    """
    settings = get_settings()
    uptime_seconds = int(time.time() - _startup_time) if _startup_time > 0 else 0
    
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": settings.app_description,
        "environment": settings.environment.value,
        "debug": settings.debug,
        "uptime_seconds": uptime_seconds,
        "startup_time": _startup_time,
        "vector_store_provider": settings.vector_store_provider.value
    }