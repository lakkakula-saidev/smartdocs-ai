"""
SmartDocs AI Backend - Application Entry Point.

This module provides backward compatibility with existing deployment
and development commands while using the new modular app structure.
"""

from app.main import get_application

# Create the application instance for ASGI servers
app = get_application()

# Backward compatibility: expose the app at module level
# This ensures existing uvicorn commands like 'uvicorn main:app' continue to work
__all__ = ["app"]

# For direct execution (python main.py)
if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings
    
    settings = get_settings()
    
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment.value}")
    print(f"Server: http://{settings.host}:{settings.port}")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.value.lower(),
        access_log=True
    )