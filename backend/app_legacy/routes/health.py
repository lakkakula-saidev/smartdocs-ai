"""
Health check route handlers for SmartDocs AI Backend.

This module provides endpoints for system health monitoring, including
API key validation, vector store status, document registry health,
and overall system status reporting.
"""

import time
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..exceptions import SmartDocsException
from ..logger import get_logger
from ..models.schemas import HealthResponse, ErrorResponse
from ..services.health_service import HealthService

# Create router with proper tags and metadata
router = APIRouter(
    prefix="",
    tags=["health"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    }
)

logger = get_logger("health_routes")


def get_health_service(settings: Settings = Depends(get_settings)) -> HealthService:
    """
    Dependency to provide HealthService instance.
    
    Args:
        settings: Application settings from dependency injection
        
    Returns:
        Configured HealthService instance
    """
    return HealthService(settings=settings)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health Check",
    description="""
    Get comprehensive system health status including:
    
    - Overall system status (ok/degraded/down)
    - Document registry status and count
    - API key configuration status
    - Vector store connectivity
    - System uptime and version
    
    This endpoint is designed for monitoring and health checks by load balancers,
    monitoring systems, and frontend applications.
    """,
    responses={
        200: {
            "description": "System health information",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy_system": {
                            "summary": "Healthy system with documents",
                            "value": {
                                "status": "ok",
                                "has_documents": True,
                                "last_document_id": "a1b2c3d4e5f6789012345678901234ab",
                                "document_count": 5,
                                "uptime_seconds": 86400,
                                "version": "0.1.0"
                            }
                        },
                        "new_system": {
                            "summary": "Healthy system without documents",
                            "value": {
                                "status": "ok",
                                "has_documents": False,
                                "last_document_id": None,
                                "document_count": 0,
                                "uptime_seconds": 3600,
                                "version": "0.1.0"
                            }
                        },
                        "degraded_system": {
                            "summary": "System with configuration issues",
                            "value": {
                                "status": "degraded",
                                "has_documents": True,
                                "last_document_id": "a1b2c3d4e5f6789012345678901234ab",
                                "document_count": 3,
                                "uptime_seconds": 1800,
                                "version": "0.1.0"
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable due to critical system failures",
            "content": {
                "application/json": {
                    "examples": {
                        "service_down": {
                            "summary": "Critical system failure",
                            "value": {
                                "error": True,
                                "status_code": 503,
                                "message": "System is currently unavailable",
                                "error_code": "SERVICE_UNAVAILABLE",
                                "details": {
                                    "api_key_configured": False,
                                    "vector_store_healthy": False
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_health(
    health_service: HealthService = Depends(get_health_service),
    include_details: bool = False
) -> HealthResponse:
    """
    Get system health status.
    
    Args:
        health_service: Health service dependency
        include_details: Whether to include detailed diagnostic information
        
    Returns:
        System health response
        
    Raises:
        HTTPException: 503 if system is critically down
    """
    start_time = time.time()
    
    logger.info(
        "Health check requested",
        extra={"include_details": include_details}
    )
    
    try:
        health_response = await health_service.get_health_status(include_details)
        
        # Return 503 if system is down
        if health_response.status.value == "down":
            logger.warning(
                "System health check indicates service is down",
                extra={
                    "status": health_response.status.value,
                    "document_count": health_response.document_count
                }
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="System is currently unavailable"
            )
        
        check_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Health check completed successfully",
            extra={
                "status": health_response.status.value,
                "document_count": health_response.document_count,
                "check_time_ms": check_time_ms
            }
        )
        
        return health_response
        
    except HTTPException:
        raise
        
    except SmartDocsException as e:
        logger.error(
            "Health check failed with SmartDocs error",
            extra={"error_code": e.error_code, "message": e.message},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
        
    except Exception as e:
        logger.error(
            "Health check failed with unexpected error",
            extra={"error": str(e)},
            exc_info=True
        )
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
    - Dependency status for all packages
    - System metrics and resource usage
    - Vector store detailed status
    - File system permissions
    
    This endpoint provides comprehensive diagnostic information useful for
    debugging and system monitoring. It may take longer to respond than
    the basic health check.
    """,
    responses={
        200: {
            "description": "Detailed system health information",
            "content": {
                "application/json": {
                    "examples": {
                        "detailed_health": {
                            "summary": "Detailed health response",
                            "value": {
                                "status": "ok",
                                "has_documents": True,
                                "last_document_id": "a1b2c3d4e5f6789012345678901234ab",
                                "document_count": 5,
                                "uptime_seconds": 86400,
                                "version": "0.1.0",
                                "diagnostics": {
                                    "startup_time": "2024-01-15T10:00:00.000Z",
                                    "current_time": "2024-01-16T10:00:00.000Z",
                                    "dependencies": {
                                        "langchain": {"available": True, "source": "primary"},
                                        "langchain_openai": {"available": True, "source": "primary"}
                                    },
                                    "system_metrics": {
                                        "total_documents": 5,
                                        "total_queries": 150,
                                        "storage_used_bytes": 104857600
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_detailed_health(
    health_service: HealthService = Depends(get_health_service)
) -> Dict[str, Any]:
    """
    Get detailed system health status with diagnostic information.
    
    Args:
        health_service: Health service dependency
        
    Returns:
        Detailed health information dictionary
    """
    start_time = time.time()
    
    logger.info("Detailed health check requested")
    
    try:
        # Get basic health info with details
        health_response = await health_service.get_health_status(include_details=True)
        
        # Get additional diagnostic information
        diagnostic_info = await health_service.get_diagnostic_info()
        
        # Combine responses
        detailed_response = {
            **health_response.dict(),
            "diagnostics": diagnostic_info
        }
        
        check_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Detailed health check completed",
            extra={
                "status": health_response.status.value,
                "check_time_ms": check_time_ms
            }
        )
        
        return detailed_response
        
    except SmartDocsException as e:
        logger.error(
            "Detailed health check failed with SmartDocs error",
            extra={"error_code": e.error_code, "message": e.message},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
        
    except Exception as e:
        logger.error(
            "Detailed health check failed with unexpected error",
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detailed health check failed due to internal error"
        )