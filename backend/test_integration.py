"""
SmartDocs AI Backend - Comprehensive Integration Tests

This test suite validates the complete system functionality including:
- API endpoints and contracts
- Document processing pipeline
- Vector store integration
- Error handling
- Service integration points
- Backward compatibility
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

import pytest
import requests
from fastapi.testclient import TestClient

# Import the application
from main import app
from app.main import create_app, get_application
from app.config import get_settings, Settings, Environment
from app.db.vector_store import get_document_registry, get_vector_store


class IntegrationTestSuite:
    """Comprehensive integration test suite for SmartDocs AI Backend."""
    
    def __init__(self):
        self.client = TestClient(app)
        self.base_url = "http://testserver"
        self.test_results = []
        self.settings = get_settings()
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test results for reporting."""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        status = "✓" if success else "✗"
        print(f"{status} {test_name}: {details}")
        
    def test_app_creation(self):
        """Test that application can be created successfully."""
        try:
            # Test direct app creation
            test_app = create_app()
            assert test_app is not None
            assert len(test_app.routes) > 0
            
            # Test get_application function
            app_instance = get_application()
            assert app_instance is not None
            assert len(app_instance.routes) > 0
            
            self.log_test_result("App Creation", True, "FastAPI app created successfully")
            return True
        except Exception as e:
            self.log_test_result("App Creation", False, f"Failed: {e}")
            return False
    
    def test_health_endpoint(self):
        """Test health check endpoint functionality."""
        try:
            # Basic health check
            response = self.client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            required_fields = ["status", "version", "has_documents", "document_count", "uptime_seconds"]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
            
            assert data["status"] == "ok"
            assert data["version"] == "0.1.0"
            assert isinstance(data["has_documents"], bool)
            assert isinstance(data["document_count"], int)
            assert isinstance(data["uptime_seconds"], int)
            
            # Detailed health check
            response = self.client.get("/health?include_details=true")
            assert response.status_code == 200
            detailed_data = response.json()
            
            # Should have additional details
            assert "services" in detailed_data or len(detailed_data) >= len(data)
            
            self.log_test_result("Health Endpoint", True, "Health checks passed")
            return True
        except Exception as e:
            self.log_test_result("Health Endpoint", False, f"Failed: {e}")
            return False
    
    def test_api_documentation(self):
        """Test that OpenAPI documentation is available."""
        try:
            # Test OpenAPI JSON endpoint
            response = self.client.get("/openapi.json")
            assert response.status_code == 200
            
            openapi_spec = response.json()
            assert "openapi" in openapi_spec
            assert "info" in openapi_spec
            assert "paths" in openapi_spec
            
            # Verify expected endpoints are documented
            paths = openapi_spec["paths"]
            expected_paths = ["/health", "/upload", "/ask"]
            for path in expected_paths:
                assert path in paths, f"Missing API path: {path}"
            
            # Test docs endpoint availability
            response = self.client.get("/docs")
            assert response.status_code == 200
            
            self.log_test_result("API Documentation", True, "OpenAPI docs available")
            return True
        except Exception as e:
            self.log_test_result("API Documentation", False, f"Failed: {e}")
            return False
    
    def test_cors_configuration(self):
        """Test CORS middleware configuration."""
        try:
            # Test preflight request
            response = self.client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            
            # Should allow CORS
            assert response.status_code in [200, 204]
            
            # Test actual CORS headers in response
            response = self.client.get(
                "/health",
                headers={"Origin": "http://localhost:3000"}
            )
            assert response.status_code == 200
            
            self.log_test_result("CORS Configuration", True, "CORS middleware working")
            return True
        except Exception as e:
            self.log_test_result("CORS Configuration", False, f"Failed: {e}")
            return False
    
    def test_upload_endpoint_structure(self):
        """Test upload endpoint structure and validation."""
        try:
            # Test upload endpoint without file (should fail gracefully)
            response = self.client.post("/upload")
            assert response.status_code == 422  # Validation error
            
            # Test upload with invalid file type
            response = self.client.post(
                "/upload",
                files={"file": ("test.txt", b"test content", "text/plain")}
            )
            # Should reject non-PDF files
            assert response.status_code in [400, 422]
            
            self.log_test_result("Upload Endpoint Structure", True, "Upload validation working")
            return True
        except Exception as e:
            self.log_test_result("Upload Endpoint Structure", False, f"Failed: {e}")
            return False
    
    def test_ask_endpoint_structure(self):
        """Test ask endpoint structure and validation."""
        try:
            # Test ask endpoint without required fields
            response = self.client.post("/ask", json={})
            assert response.status_code == 422  # Validation error
            
            # Test ask endpoint with invalid document_id
            response = self.client.post("/ask", json={
                "question": "Test question",
                "document_id": "nonexistent_id"
            })
            assert response.status_code in [400, 404]  # Should fail gracefully
            
            self.log_test_result("Ask Endpoint Structure", True, "Ask validation working")
            return True
        except Exception as e:
            self.log_test_result("Ask Endpoint Structure", False, f"Failed: {e}")
            return False
    
    def test_error_handling(self):
        """Test error handling and HTTP status codes."""
        try:
            # Test 404 for non-existent endpoint
            response = self.client.get("/nonexistent")
            assert response.status_code == 404
            
            # Test method not allowed
            response = self.client.delete("/health")
            assert response.status_code == 405
            
            # Test malformed JSON
            response = self.client.post(
                "/ask",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 422
            
            self.log_test_result("Error Handling", True, "HTTP error codes correct")
            return True
        except Exception as e:
            self.log_test_result("Error Handling", False, f"Failed: {e}")
            return False
    
    def test_vector_store_integration(self):
        """Test vector store abstraction and registry."""
        try:
            # Test vector store initialization
            vector_store = get_vector_store()
            assert vector_store is not None
            
            # Test document registry
            registry = get_document_registry()
            assert registry is not None
            assert hasattr(registry, 'document_count')
            assert hasattr(registry, 'last_document_id')
            
            # Test health check functionality
            async def test_health():
                health = await vector_store.health_check()
                assert isinstance(health, dict)
                assert "status" in health
                
                registry_health = await registry.health_check()
                assert isinstance(registry_health, dict)
                
            asyncio.run(test_health())
            
            self.log_test_result("Vector Store Integration", True, "Vector store accessible")
            return True
        except Exception as e:
            self.log_test_result("Vector Store Integration", False, f"Failed: {e}")
            return False
    
    def test_configuration_system(self):
        """Test configuration loading and validation."""
        try:
            settings = get_settings()
            assert settings is not None
            
            # Test required configuration fields
            assert settings.app_name
            assert settings.app_version
            assert settings.environment in [env.value for env in Environment]
            assert settings.vector_store_provider
            
            # Test environment-specific settings
            if settings.is_development:
                assert settings.debug is True
                assert settings.reload is True
            
            # Test OpenAI configuration
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                assert len(openai_key) > 20  # Basic validation
            
            self.log_test_result("Configuration System", True, "Configuration loaded correctly")
            return True
        except Exception as e:
            self.log_test_result("Configuration System", False, f"Failed: {e}")
            return False
    
    def test_logging_system(self):
        """Test logging configuration and functionality."""
        try:
            from app.logger import get_logger, LogContext
            
            # Test logger creation
            logger = get_logger("test")
            assert logger is not None
            
            # Test log context manager
            with LogContext(component="test"):
                logger.info("Test log message")
            
            self.log_test_result("Logging System", True, "Logging system functional")
            return True
        except Exception as e:
            self.log_test_result("Logging System", False, f"Failed: {e}")
            return False
    
    def test_backward_compatibility(self):
        """Test backward compatibility with existing API contracts."""
        try:
            # Test that all expected endpoints exist
            endpoints_to_test = [
                ("/health", "GET"),
                ("/upload", "POST"),
                ("/ask", "POST"),
            ]
            
            for endpoint, method in endpoints_to_test:
                if method == "GET":
                    response = self.client.get(endpoint)
                else:
                    # For POST endpoints, we expect validation errors, not 404s
                    response = self.client.post(endpoint, json={})
                
                # Should not be 404 (endpoint exists)
                assert response.status_code != 404, f"Endpoint {endpoint} not found"
            
            # Test response format consistency
            health_response = self.client.get("/health")
            health_data = health_response.json()
            
            # Ensure backward-compatible fields are present
            expected_fields = ["status", "version", "has_documents", "document_count"]
            for field in expected_fields:
                assert field in health_data, f"Missing backward-compatible field: {field}"
            
            self.log_test_result("Backward Compatibility", True, "API contracts maintained")
            return True
        except Exception as e:
            self.log_test_result("Backward Compatibility", False, f"Failed: {e}")
            return False
    
    def test_development_endpoints(self):
        """Test development-specific endpoints."""
        try:
            if self.settings.is_development:
                # Test debug endpoint
                response = self.client.get("/debug/env")
                assert response.status_code == 200
                
                debug_data = response.json()
                expected_debug_fields = [
                    "openai_key_present", "environment", "debug_mode",
                    "vector_store_provider", "document_count"
                ]
                
                for field in expected_debug_fields:
                    assert field in debug_data, f"Missing debug field: {field}"
                
                self.log_test_result("Development Endpoints", True, "Debug endpoints available")
            else:
                self.log_test_result("Development Endpoints", True, "Production mode - debug endpoints disabled")
            
            return True
        except Exception as e:
            self.log_test_result("Development Endpoints", False, f"Failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests and return summary."""
        print("=" * 60)
        print("SmartDocs AI Backend - Integration Test Suite")
        print("=" * 60)
        
        test_methods = [
            self.test_app_creation,
            self.test_health_endpoint,
            self.test_api_documentation,
            self.test_cors_configuration,
            self.test_upload_endpoint_structure,
            self.test_ask_endpoint_structure,
            self.test_error_handling,
            self.test_vector_store_integration,
            self.test_configuration_system,
            self.test_logging_system,
            self.test_backward_compatibility,
            self.test_development_endpoints,
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"✗ {test_method.__name__}: Unexpected error: {e}")
                failed += 1
        
        print("=" * 60)
        print(f"Test Results: {passed} passed, {failed} failed")
        print("=" * 60)
        
        summary = {
            "total_tests": len(test_methods),
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / len(test_methods)) * 100,
            "test_results": self.test_results,
            "timestamp": time.time(),
            "environment": self.settings.environment.value,
            "version": self.settings.app_version
        }
        
        return summary


def main():
    """Run integration tests when executed directly."""
    test_suite = IntegrationTestSuite()
    summary = test_suite.run_all_tests()
    
    # Save test results
    results_file = Path("integration_test_results.json")
    with open(results_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    # Exit with appropriate code
    exit_code = 0 if summary["failed"] == 0 else 1
    print(f"Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)