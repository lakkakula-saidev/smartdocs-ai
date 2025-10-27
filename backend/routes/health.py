"""
Health check routes for SmartDocs AI Backend.

Simplified health monitoring using direct module imports.
"""

import time
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from config import get_settings
from models import HealthResponse, HealthStatus, ErrorResponse
from storage import get_unified_storage
import ai

# Create router
router = APIRouter(
    prefix="",
    tags=["health"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    }
)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health Check",
    description="""
    Get comprehensive system health status including:
    
    - Overall system status (ok/degraded/down)
    - Document registry status and count
    - AI integration status
    - Vector store connectivity
    - System uptime and version
    """
)
async def get_health() -> HealthResponse:
    """
    Get system health status.
    
    Returns:
        System health response
        
    Raises:
        HTTPException: 503 if system is critically down
    """
    start_time = time.time()
    
    print("[health] Health check requested")
    
    try:
        settings = get_settings()
        storage = get_unified_storage()
        
        # Perform health checks
        health_issues = []
        
        # Check OpenAI API key
        if not settings.has_openai_key:
            health_issues.append("OpenAI API key not configured")
        
        # Check storage system
        storage_health = await storage.health_check()
        if storage_health.get("status") != "healthy":
            health_issues.append(f"Storage system unhealthy: {storage_health.get('error', 'unknown')}")
        
        # Check AI integration
        try:
            ai_health = await ai.health_check()
            if ai_health.get("status") != "healthy":
                health_issues.append("AI integration unhealthy")
        except Exception as e:
            health_issues.append(f"AI integration failed: {str(e)}")
        
        # Determine overall status
        if len(health_issues) > 2:
            overall_status = HealthStatus.DOWN
        elif len(health_issues) > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.OK
        
        # Calculate uptime (simplified)
        uptime_seconds = int(time.time()) - int(start_time)  # Simplified uptime calculation
        
        response = HealthResponse(
            status=overall_status,
            has_documents=storage.document_count > 0,
            last_document_id=storage.last_document_id,
            document_count=storage.document_count,
            uptime_seconds=max(uptime_seconds, 0),
            version=settings.app_version
        )
        
        # Return 503 if system is down
        if response.status == HealthStatus.DOWN:
            print(f"[health] System health check indicates service is down: {health_issues}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="System is currently unavailable"
            )
        
        check_time_ms = int((time.time() - start_time) * 1000)
        
        print(f"[health] Health check completed: {response.status} ({check_time_ms}ms)")
        
        return response
        
    except HTTPException:
        raise
        
    except Exception as e:
        print(f"[health] ERROR: Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed due to internal error"
        )


@router.get(
    "/health/detailed",
    response_model=Dict[str, Any], 
    summary="Detailed System Health Check",
    description="""
    Get detailed system health information including:
    
    - All basic health information
    - AI component status
    - Storage system details
    - Configuration status
    """
)
async def get_detailed_health() -> Dict[str, Any]:
    """
    Get detailed system health status with diagnostic information.
    
    Returns:
        Detailed health information dictionary
    """
    start_time = time.time()
    
    print("[health] Detailed health check requested")
    
    try:
        settings = get_settings()
        storage = get_unified_storage()
        
        # Get basic health info
        basic_health = await get_health()
        
        # Get additional diagnostic information
        diagnostic_info = {
            "current_time": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "configuration": {
                "environment": settings.environment,
                "debug_mode": settings.debug,
                "vector_store_provider": settings.vector_store_provider,
                "openai_model": settings.openai_model,
                "chunk_size": settings.chunk_size,
                "retrieval_k": settings.retrieval_k
            },
            "ai_integration": {},
            "storage_system": {}
        }
        
        # Test AI integration
        try:
            ai_health = await ai.health_check()
            diagnostic_info["ai_integration"] = ai_health
        except Exception as e:
            diagnostic_info["ai_integration"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Get storage details
        try:
            storage_health = await storage.health_check()
            diagnostic_info["storage_system"] = storage_health
        except Exception as e:
            diagnostic_info["storage_system"] = {
                "status": "error", 
                "error": str(e)
            }
        
        # Combine responses
        detailed_response = {
            **basic_health.dict(),
            "diagnostics": diagnostic_info
        }
        
        check_time_ms = int((time.time() - start_time) * 1000)
        
        print(f"[health] Detailed health check completed ({check_time_ms}ms)")
        
        return detailed_response
        
    except Exception as e:
        print(f"[health] ERROR: Detailed health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detailed health check failed due to internal error"
        )