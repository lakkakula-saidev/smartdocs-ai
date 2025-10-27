"""
Health service for SmartDocs AI Backend.

This service handles system health monitoring, including API key validation,
vector store status checking, document registry health, and overall system
status reporting.
"""

import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from ..config import Settings, get_settings
from ..exceptions import ConfigurationError, VectorStoreError, ExceptionContext
from ..logger import get_logger
from ..models.schemas import HealthResponse, HealthStatus, SystemMetrics
from ..db.vector_store import get_document_registry, DocumentRegistry


class HealthService:
    """
    Service for system health monitoring and status reporting.
    
    Provides comprehensive health checks across all system components
    including configuration, dependencies, storage, and services.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        document_registry: Optional[DocumentRegistry] = None
    ):
        """
        Initialize health service.
        
        Args:
            settings: Application settings (uses global if None)
            document_registry: Document registry instance (uses global if None)
        """
        self.settings = settings or get_settings()
        self.document_registry = document_registry or get_document_registry()
        self.logger = get_logger("health_service")
        
        # Track service startup time
        self._startup_time = datetime.utcnow()
        
        # Health check cache to avoid excessive API calls
        self._health_cache = {}
        self._cache_duration = timedelta(seconds=30)  # 30-second cache
    
    async def get_health_status(self, include_details: bool = False) -> HealthResponse:
        """
        Get comprehensive system health status.
        
        Args:
            include_details: Whether to include detailed health information
            
        Returns:
            Health response with system status
        """
        self.logger.debug("Performing health check", extra={"include_details": include_details})
        
        start_time = time.time()
        
        try:
            # Check if we have cached results
            cache_key = f"health_status_{include_details}"
            if self._is_cache_valid(cache_key):
                self.logger.debug("Returning cached health status")
                return self._health_cache[cache_key]["data"]
            
            # Perform health checks
            health_checks = await self._perform_health_checks(include_details)
            
            # Determine overall status
            overall_status = self._determine_overall_status(health_checks)
            
            # Get document statistics
            document_count = self.document_registry.document_count
            last_document_id = self.document_registry.last_document_id
            
            # Calculate uptime
            uptime_seconds = int((datetime.utcnow() - self._startup_time).total_seconds())
            
            response = HealthResponse(
                status=overall_status,
                has_documents=document_count > 0,
                last_document_id=last_document_id,
                document_count=document_count,
                uptime_seconds=uptime_seconds,
                version=self.settings.app_version
            )
            
            # Cache the result
            self._cache_health_result(cache_key, response)
            
            check_time_ms = int((time.time() - start_time) * 1000)
            
            self.logger.info(
                f"Health check completed",
                extra={
                    "status": overall_status.value,
                    "document_count": document_count,
                    "uptime_seconds": uptime_seconds,
                    "check_time_ms": check_time_ms,
                    "include_details": include_details
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                f"Health check failed",
                extra={"error": str(e), "include_details": include_details},
                exc_info=True
            )
            
            # Return degraded status if health check fails
            return HealthResponse(
                status=HealthStatus.DEGRADED,
                has_documents=False,
                last_document_id=None,
                document_count=0,
                uptime_seconds=int((datetime.utcnow() - self._startup_time).total_seconds()),
                version=self.settings.app_version
            )
    
    async def check_api_key_status(self) -> Dict[str, Any]:
        """
        Check OpenAI API key configuration and validity.
        
        Returns:
            API key status information
        """
        try:
            from ..config import require_openai_api_key
            
            api_key = require_openai_api_key()
            
            return {
                "configured": True,
                "length": len(api_key),
                "prefix": api_key[:7] + "***" if len(api_key) > 7 else "***",
                "status": "valid"
            }
            
        except Exception as e:
            self.logger.warning(f"OpenAI API key check failed: {e}")
            return {
                "configured": False,
                "status": "invalid",
                "error": str(e)
            }
    
    async def check_vector_store_health(self) -> Dict[str, Any]:
        """
        Check vector store health and connectivity.
        
        Returns:
            Vector store health information
        """
        try:
            return await self.document_registry.health_check()
        except Exception as e:
            self.logger.error(f"Vector store health check failed: {e}", exc_info=True)
            return {
                "registry_status": "unhealthy",
                "error": str(e),
                "vector_store": {
                    "status": "unhealthy",
                    "error": str(e)
                }
            }
    
    async def check_dependencies(self) -> Dict[str, Any]:
        """
        Check availability of required dependencies.
        
        Returns:
            Dependency status information
        """
        dependencies = {}
        
        # Check LangChain components
        dependencies["langchain"] = self._check_dependency("langchain")
        dependencies["langchain_openai"] = self._check_dependency("langchain_openai", fallback="langchain.embeddings.openai")
        dependencies["langchain_chroma"] = self._check_dependency("langchain_chroma", fallback="langchain_community.vectorstores")
        
        # Check PDF processing
        dependencies["pypdf"] = self._check_dependency("pypdf")
        
        # Check FastAPI components
        dependencies["fastapi"] = self._check_dependency("fastapi")
        dependencies["uvicorn"] = self._check_dependency("uvicorn")
        
        # Check data processing
        dependencies["pydantic"] = self._check_dependency("pydantic")
        
        return dependencies
    
    async def get_system_metrics(self) -> SystemMetrics:
        """
        Get comprehensive system metrics.
        
        Returns:
            System metrics object
        """
        # Get document registry stats
        document_count = self.document_registry.document_count
        
        # Calculate storage usage (approximate)
        storage_used = await self._calculate_storage_usage()
        
        # Get session stats from chat service if available
        total_queries = 0
        avg_query_time = None
        last_query_at = None
        
        try:
            # This would be implemented if we had a global chat service instance
            # For now, we'll use placeholder values
            pass
        except Exception:
            pass
        
        return SystemMetrics(
            total_documents=document_count,
            total_queries=total_queries,
            average_query_time_ms=avg_query_time,
            storage_used_bytes=storage_used,
            last_query_at=last_query_at
        )
    
    async def check_file_system_permissions(self) -> Dict[str, Any]:
        """
        Check file system permissions for vector store directory.
        
        Returns:
            File system permission status
        """
        vector_store_path = self.settings.vector_store_path
        
        try:
            # Check if directory exists and is writable
            if not vector_store_path.exists():
                vector_store_path.mkdir(parents=True, exist_ok=True)
            
            # Test write permission
            test_file = vector_store_path / "health_check_test.tmp"
            test_file.write_text("health check")
            test_file.unlink()  # Delete test file
            
            return {
                "path": str(vector_store_path),
                "exists": True,
                "writable": True,
                "readable": True,
                "status": "healthy"
            }
            
        except Exception as e:
            self.logger.error(f"File system permission check failed: {e}")
            return {
                "path": str(vector_store_path),
                "exists": vector_store_path.exists(),
                "writable": False,
                "readable": False,
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _perform_health_checks(self, include_details: bool) -> Dict[str, Any]:
        """
        Perform all health checks.
        
        Args:
            include_details: Whether to include detailed checks
            
        Returns:
            Comprehensive health check results
        """
        checks = {}
        
        # Core checks (always performed)
        checks["api_key"] = await self.check_api_key_status()
        checks["vector_store"] = await self.check_vector_store_health()
        checks["file_system"] = await self.check_file_system_permissions()
        
        # Detailed checks (optional)
        if include_details:
            checks["dependencies"] = await self.check_dependencies()
            checks["system_metrics"] = (await self.get_system_metrics()).dict()
        
        return checks
    
    def _determine_overall_status(self, health_checks: Dict[str, Any]) -> HealthStatus:
        """
        Determine overall system status from individual checks.
        
        Args:
            health_checks: Dictionary of health check results
            
        Returns:
            Overall health status
        """
        # Check critical components
        api_key_ok = health_checks.get("api_key", {}).get("configured", False)
        vector_store_ok = health_checks.get("vector_store", {}).get("registry_status") == "healthy"
        file_system_ok = health_checks.get("file_system", {}).get("status") == "healthy"
        
        # If any critical component is down, system is down
        if not (api_key_ok and vector_store_ok and file_system_ok):
            return HealthStatus.DOWN
        
        # Check for degraded status
        dependencies = health_checks.get("dependencies", {})
        if dependencies:
            missing_deps = [
                name for name, status in dependencies.items()
                if not status.get("available", False)
            ]
            if missing_deps:
                self.logger.warning(f"Missing dependencies: {missing_deps}")
                return HealthStatus.DEGRADED
        
        return HealthStatus.OK
    
    def _check_dependency(self, module_name: str, fallback: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if a Python module is available.
        
        Args:
            module_name: Name of the module to check
            fallback: Optional fallback module name
            
        Returns:
            Dependency status information
        """
        try:
            __import__(module_name)
            return {
                "name": module_name,
                "available": True,
                "source": "primary"
            }
        except ImportError:
            if fallback:
                try:
                    __import__(fallback)
                    return {
                        "name": module_name,
                        "available": True,
                        "source": "fallback",
                        "fallback_module": fallback
                    }
                except ImportError:
                    pass
            
            return {
                "name": module_name,
                "available": False,
                "fallback_tried": fallback is not None
            }
    
    async def _calculate_storage_usage(self) -> int:
        """
        Calculate approximate storage usage in bytes.
        
        Returns:
            Storage usage in bytes
        """
        try:
            vector_store_path = self.settings.vector_store_path
            if not vector_store_path.exists():
                return 0
            
            total_size = 0
            for root, dirs, files in os.walk(vector_store_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, IOError):
                        continue  # Skip files we can't read
            
            return total_size
            
        except Exception as e:
            self.logger.warning(f"Storage calculation failed: {e}")
            return 0
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cached health result is still valid.
        
        Args:
            cache_key: Cache key to check
            
        Returns:
            True if cache is valid
        """
        if cache_key not in self._health_cache:
            return False
        
        cached_at = self._health_cache[cache_key]["cached_at"]
        return datetime.utcnow() - cached_at < self._cache_duration
    
    def _cache_health_result(self, cache_key: str, result: HealthResponse) -> None:
        """
        Cache health check result.
        
        Args:
            cache_key: Cache key
            result: Health response to cache
        """
        self._health_cache[cache_key] = {
            "data": result,
            "cached_at": datetime.utcnow()
        }
        
        # Clean up old cache entries (simple cleanup)
        cutoff_time = datetime.utcnow() - self._cache_duration * 2
        keys_to_remove = [
            key for key, value in self._health_cache.items()
            if value["cached_at"] < cutoff_time
        ]
        
        for key in keys_to_remove:
            del self._health_cache[key]
    
    # Diagnostic methods for debugging
    
    async def get_diagnostic_info(self) -> Dict[str, Any]:
        """
        Get comprehensive diagnostic information for debugging.
        
        Returns:
            Diagnostic information dictionary
        """
        return {
            "startup_time": self._startup_time.isoformat(),
            "current_time": datetime.utcnow().isoformat(),
            "uptime_seconds": int((datetime.utcnow() - self._startup_time).total_seconds()),
            "settings": {
                "app_name": self.settings.app_name,
                "app_version": self.settings.app_version,
                "environment": self.settings.environment.value,
                "debug": self.settings.debug,
                "vector_store_provider": self.settings.vector_store_provider.value,
                "openai_model": self.settings.openai_model,
                "chunk_size": self.settings.chunk_size,
                "chunk_overlap": self.settings.chunk_overlap,
                "retrieval_k": self.settings.retrieval_k
            },
            "cache_info": {
                "cache_entries": len(self._health_cache),
                "cache_duration_seconds": self._cache_duration.total_seconds()
            },
            "document_registry": {
                "document_count": self.document_registry.document_count,
                "last_document_id": self.document_registry.last_document_id
            }
        }