#!/usr/bin/env python3
"""
Test script for SmartDocs AI Backend infrastructure.

This script tests the core configuration, logging, and utility modules
to ensure they work correctly before integrating with the main application.
"""

import sys
import os

# Add the current directory to Python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_configuration():
    """Test configuration loading and validation."""
    print("=" * 50)
    print("Testing Configuration Module")
    print("=" * 50)
    
    try:
        from app.config import get_settings, load_settings, require_openai_api_key
        
        # Test settings loading
        print("✓ Loading settings...")
        settings = get_settings()
        
        # Test basic properties
        print(f"✓ App name: {settings.app_name}")
        print(f"✓ App version: {settings.app_version}")
        print(f"✓ Environment: {settings.environment}")
        print(f"✓ Debug mode: {settings.debug}")
        print(f"✓ OpenAI model: {settings.openai_model}")
        print(f"✓ Vector store provider: {settings.vector_store_provider}")
        print(f"✓ Chunk size: {settings.chunk_size}")
        print(f"✓ Max upload size: {settings.max_upload_size_mb}MB")
        
        # Test computed properties
        print(f"✓ Is development: {settings.is_development}")
        print(f"✓ Is production: {settings.is_production}")
        print(f"✓ Max upload bytes: {settings.max_upload_size_bytes}")
        print(f"✓ Vector store path: {settings.vector_store_path}")
        
        # Test OpenAI API key validation
        try:
            api_key = require_openai_api_key()
            print(f"✓ OpenAI API key validated (length: {len(api_key)})")
        except Exception as e:
            print(f"⚠ OpenAI API key validation failed: {e}")
        
        print("✓ Configuration module test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Configuration module test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging():
    """Test logging infrastructure."""
    print("\n" + "=" * 50)
    print("Testing Logging Module")
    print("=" * 50)
    
    try:
        from app.logger import get_logger, setup_logging, LogContext, log_function_call
        
        # Test basic logger
        print("✓ Getting logger...")
        logger = get_logger("test")
        
        # Test different log levels
        print("✓ Testing log levels...")
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        
        # Test structured logging with extra fields
        print("✓ Testing structured logging...")
        logger.info(
            "Structured log message",
            extra={
                "user_id": "test_user",
                "operation": "test_operation",
                "metadata": {"key": "value"}
            }
        )
        
        # Test log context
        print("✓ Testing log context...")
        with LogContext(request_id="req_123", session_id="sess_456"):
            logger.info("Message with context")
        
        # Test function decorator
        print("✓ Testing function logging decorator...")
        
        @log_function_call(include_args=True, include_result=True)
        def test_function(x: int, y: int) -> int:
            return x + y
        
        result = test_function(2, 3)
        print(f"Function result: {result}")
        
        print("✓ Logging module test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Logging module test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_utilities():
    """Test utility modules.""" 
    print("\n" + "=" * 50)
    print("Testing Utility Modules")
    print("=" * 50)
    
    try:
        # Test validation utilities
        from app.utils.validation import (
            validate_query, validate_document_id, sanitize_filename,
            generate_document_id, validate_api_key_format
        )
        
        print("✓ Testing validation utilities...")
        
        # Test query validation
        query = validate_query("What is the main topic?")
        print(f"✓ Query validation: '{query}'")
        
        # Test document ID generation and validation
        doc_id = generate_document_id()
        validated_doc_id = validate_document_id(doc_id)
        print(f"✓ Document ID: {validated_doc_id}")
        
        # Test filename sanitization
        safe_filename = sanitize_filename("unsafe<>filename|test.pdf")
        print(f"✓ Sanitized filename: '{safe_filename}'")
        
        # Test API key format validation
        valid_key = validate_api_key_format("sk-test123456789")
        invalid_key = validate_api_key_format("invalid-key")
        print(f"✓ API key validation: valid={valid_key}, invalid={invalid_key}")
        
        # Test text processing utilities
        from app.utils.text_processing import (
            enhance_markdown, clean_text, truncate_text, count_tokens_estimate
        )
        
        print("✓ Testing text processing utilities...")
        
        # Test markdown enhancement
        test_text = """
        1. First item: This is important information
        2. Second item: Another key point
        "Document Title" contains valuable insights.
        """
        enhanced = enhance_markdown(test_text.strip())
        print(f"✓ Markdown enhanced: {len(enhanced)} characters")
        
        # Test text cleaning
        messy_text = "  This   has   lots\n\n\n\nof   whitespace  "
        cleaned = clean_text(messy_text)
        print(f"✓ Text cleaned: '{cleaned}'")
        
        # Test text truncation
        long_text = "This is a very long text that should be truncated properly"
        truncated = truncate_text(long_text, max_length=30)
        print(f"✓ Text truncated: '{truncated}'")
        
        # Test token estimation
        token_count = count_tokens_estimate("Hello world, this is a test message.")
        print(f"✓ Token count estimate: {token_count}")
        
        print("✓ Utility modules test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Utility modules test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_exceptions():
    """Test exception handling."""
    print("\n" + "=" * 50)
    print("Testing Exception Module")
    print("=" * 50)
    
    try:
        from app.exceptions import (
            SmartDocsException, ConfigurationError, DocumentNotFoundError,
            ExceptionContext, raise_if_missing_api_key, create_error_response
        )
        
        print("✓ Testing custom exceptions...")
        
        # Test base exception
        try:
            raise SmartDocsException(
                "This is a test exception",
                error_code="TEST_ERROR",
                details={"key": "value"}
            )
        except SmartDocsException as e:
            print(f"✓ SmartDocsException: {e.message}, code: {e.error_code}")
        
        # Test specific exception
        try:
            raise DocumentNotFoundError("test_doc_123")
        except DocumentNotFoundError as e:
            print(f"✓ DocumentNotFoundError: {e.message}")
        
        # Test error response creation
        error_response = create_error_response(
            status_code=404,
            message="Test error",
            error_code="TEST_ERROR",
            details={"test": True}
        )
        print(f"✓ Error response: {error_response}")
        
        # Test exception context
        try:
            with ExceptionContext(ConfigurationError, "Test context error"):
                raise ValueError("Original error")
        except ConfigurationError as e:
            print(f"✓ Exception context: {e.message}")
        
        print("✓ Exception module test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Exception module test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test integration between modules."""
    print("\n" + "=" * 50)
    print("Testing Module Integration")
    print("=" * 50)
    
    try:
        from app.config import get_settings
        from app.logger import get_logger
        from app.utils.validation import validate_query
        from app.exceptions import ValidationError
        
        settings = get_settings()
        logger = get_logger("integration_test")
        
        print("✓ All modules imported successfully")
        
        # Test config -> logger integration
        logger.info(f"Testing with environment: {settings.environment}")
        
        # Test validation -> exception integration
        try:
            validate_query("")  # Should raise ValidationError
        except Exception as e:
            logger.info(f"Expected validation error: {e}")
        
        print("✓ Module integration test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Module integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all infrastructure tests."""
    print("SmartDocs AI Backend - Infrastructure Test Suite")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Logging", test_logging),
        ("Utilities", test_utilities), 
        ("Exceptions", test_exceptions),
        ("Integration", test_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All infrastructure tests PASSED!")
        return 0
    else:
        print("❌ Some infrastructure tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())