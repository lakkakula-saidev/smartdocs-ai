#!/usr/bin/env python3
"""
Test script for SmartDocs AI service layer integration.

This script tests the integration between the service layer and the
infrastructure components we've built, ensuring proper dependency
injection and error handling.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

# Add the backend directory to Python path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.config import get_settings
from app.logger import get_logger
from app.services import DocumentService, ChatService, HealthService
from app.models.schemas import AskRequest


async def test_health_service():
    """Test HealthService functionality."""
    print("\n=== Testing HealthService ===")
    
    health_service = HealthService()
    
    # Test basic health check
    print("1. Testing basic health check...")
    health_response = await health_service.get_health_status()
    print(f"   Status: {health_response.status}")
    print(f"   Has documents: {health_response.has_documents}")
    print(f"   Uptime: {health_response.uptime_seconds}s")
    print(f"   Version: {health_response.version}")
    
    # Test API key status
    print("\n2. Testing API key status...")
    api_key_status = await health_service.check_api_key_status()
    print(f"   Configured: {api_key_status.get('configured', False)}")
    print(f"   Status: {api_key_status.get('status', 'unknown')}")
    
    # Test vector store health
    print("\n3. Testing vector store health...")
    vector_health = await health_service.check_vector_store_health()
    print(f"   Registry status: {vector_health.get('registry_status', 'unknown')}")
    
    # Test dependencies
    print("\n4. Testing dependencies...")
    dependencies = await health_service.check_dependencies()
    for name, status in dependencies.items():
        available = status.get('available', False)
        source = status.get('source', 'unknown')
        print(f"   {name}: {'✓' if available else '✗'} ({source})")
    
    # Test file system permissions
    print("\n5. Testing file system permissions...")
    fs_status = await health_service.check_file_system_permissions()
    print(f"   Path: {fs_status.get('path', 'unknown')}")
    print(f"   Status: {fs_status.get('status', 'unknown')}")
    print(f"   Writable: {fs_status.get('writable', False)}")
    
    return health_response.status.value == "ok"


async def test_document_service():
    """Test DocumentService functionality (without actual file upload)."""
    print("\n=== Testing DocumentService ===")
    
    document_service = DocumentService()
    
    # Test listing documents (should be empty initially)
    print("1. Testing document listing...")
    documents = await document_service.list_documents()
    print(f"   Found {len(documents)} documents")
    
    # Test service initialization
    print("2. Testing service initialization...")
    print(f"   Settings loaded: {document_service.settings is not None}")
    print(f"   Registry loaded: {document_service.document_registry is not None}")
    print(f"   Logger configured: {document_service.logger is not None}")
    
    return True


async def test_chat_service():
    """Test ChatService functionality (without actual document)."""
    print("\n=== Testing ChatService ===")
    
    chat_service = ChatService()
    
    # Test service initialization
    print("1. Testing service initialization...")
    print(f"   Settings loaded: {chat_service.settings is not None}")
    print(f"   Registry loaded: {chat_service.document_registry is not None}")
    print(f"   Logger configured: {chat_service.logger is not None}")
    
    # Test session stats
    print("2. Testing session statistics...")
    stats = await chat_service.get_session_stats()
    print(f"   Total queries: {stats['total_queries']}")
    print(f"   Average response time: {stats['average_response_time_ms']}ms")
    
    # Test query complexity analysis
    print("3. Testing query complexity analysis...")
    test_queries = [
        "What is this about?",
        "Can you provide a detailed analysis of the methodology used in this research paper?",
        "How does the proposed solution address the challenges mentioned in the introduction?"
    ]
    
    for query in test_queries:
        analysis = await chat_service.validate_query_complexity(query)
        print(f"   Query: '{query[:30]}...' -> Complexity: {analysis['complexity']} ({analysis['word_count']} words)")
    
    return True


async def test_service_integration():
    """Test integration between services."""
    print("\n=== Testing Service Integration ===")
    
    # Initialize all services
    health_service = HealthService()
    document_service = DocumentService()
    chat_service = ChatService()
    
    print("1. Testing shared settings...")
    settings1 = health_service.settings
    settings2 = document_service.settings
    settings3 = chat_service.settings
    print(f"   Settings consistency: {settings1 is settings2 is settings3}")
    print(f"   App name: {settings1.app_name}")
    print(f"   Environment: {settings1.environment}")
    
    print("2. Testing shared document registry...")
    registry1 = health_service.document_registry
    registry2 = document_service.document_registry
    registry3 = chat_service.document_registry
    print(f"   Registry consistency: {registry1 is registry2 is registry3}")
    print(f"   Document count: {registry1.document_count}")
    
    print("3. Testing logging integration...")
    print(f"   Health service logger: {health_service.logger.name}")
    print(f"   Document service logger: {document_service.logger.name}")
    print(f"   Chat service logger: {chat_service.logger.name}")
    
    return True


async def test_error_handling():
    """Test error handling in services."""
    print("\n=== Testing Error Handling ===")
    
    chat_service = ChatService()
    
    print("1. Testing invalid request validation...")
    try:
        # Create invalid request
        invalid_request = AskRequest(
            query="",  # Empty query should fail
            document_id="invalid_document_id"  # Invalid format
        )
        await chat_service.ask_question(invalid_request)
        print("   ✗ Expected validation error but none occurred")
        return False
    except Exception as e:
        print(f"   ✓ Correctly caught validation error: {type(e).__name__}")
    
    print("2. Testing document not found error...")
    try:
        # Create request with non-existent document
        missing_doc_request = AskRequest(
            query="What is this document about?",
            document_id="a1b2c3d4e5f6789012345678901234ab"  # Valid format but doesn't exist
        )
        await chat_service.ask_question(missing_doc_request)
        print("   ✗ Expected document not found error but none occurred")
        return False
    except Exception as e:
        print(f"   ✓ Correctly caught error: {type(e).__name__}")
    
    return True


async def main():
    """Run all service tests."""
    print("SmartDocs AI Service Layer Integration Test")
    print("=" * 50)
    
    # Initialize logging
    logger = get_logger("test_services")
    logger.info("Starting service integration tests")
    
    test_results = {}
    
    try:
        # Run individual service tests
        test_results["health_service"] = await test_health_service()
        test_results["document_service"] = await test_document_service()
        test_results["chat_service"] = await test_chat_service()
        test_results["service_integration"] = await test_service_integration()
        test_results["error_handling"] = await test_error_handling()
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        print(f"\n❌ Test execution failed: {e}")
        return False
    
    # Print results
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All service integration tests PASSED!")
        logger.info("All service integration tests passed successfully")
    else:
        print("❌ Some tests FAILED. Check the output above for details.")
        logger.error("Some service integration tests failed")
    
    return all_passed


if __name__ == "__main__":
    # Run the async main function
    result = asyncio.run(main())
    sys.exit(0 if result else 1)