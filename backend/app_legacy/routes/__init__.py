"""
Route handlers for SmartDocs AI Backend API.

This module contains FastAPI route handlers organized by functionality:
- health: System health monitoring endpoints
- upload: Document upload and processing endpoints  
- chat: Question-answering and chat endpoints

Each route module exports a router that can be included in the main FastAPI app.
"""

from .health import router as health_router
from .upload import router as upload_router
from .chat import router as chat_router

__all__ = [
    "health_router",
    "upload_router", 
    "chat_router"
]