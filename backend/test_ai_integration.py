"""
Test script for AI integration module.

This script tests the core functionality of our direct OpenAI integration
to ensure it works correctly without LangChain dependencies.
"""

import asyncio
import os
from typing import List

# Set up test environment
os.environ.setdefault("OPENAI_API_KEY", "test-key-placeholder")

async def test_openai_client():
    """Test OpenAI client initialization and basic functionality."""
    print("Testing OpenAI client...")
    
    try:
        from ai import get_openai_client
        client = get_openai_client()
        
        print(f"✓ OpenAI client initialized successfully")
        print(f"  - Embedding model: {client.embedding_model}")
        print(f"  - Chat model: {client.chat_model}")
        
        # Test token counting
        test_text = "This is a test sentence for token counting."
        token_count = client.count_tokens(test_text)
        print(f"  - Token count for test text: {token_count}")
        
        return True
        
    except Exception as e:
        print(f"✗ OpenAI client test failed: {e}")
        return False

async def test_text_chunker():
    """Test text chunking functionality."""
    print("\nTesting text chunker...")
    
    try:
        from ai import get_text_chunker, chunk_text
        
        test_text = """
        This is a test document with multiple paragraphs. 
        It contains several sentences that should be chunked appropriately.
        
        This is the second paragraph of our test document.
        It has different content to test the chunking algorithm.
        The chunker should preserve sentence boundaries when possible.
        
        This is the third paragraph with even more content.
        We want to make sure the chunking works correctly across paragraph boundaries.
        The overlap functionality should also work properly between chunks.
        """
        
        chunks = chunk_text(test_text.strip())
        
        print(f"✓ Text chunking completed successfully")
        print(f"  - Original text length: {len(test_text.strip())} characters")
        print(f"  - Number of chunks: {len(chunks)}")
        print(f"  - Average chunk size: {sum(len(chunk.content) for chunk in chunks) // len(chunks) if chunks else 0} characters")
        
        # Show first chunk preview
        if chunks:
            preview = chunks[0].content[:100] + "..." if len(chunks[0].content) > 100 else chunks[0].content
            print(f"  - First chunk preview: {preview}")
        
        return True
        
    except Exception as e:
        print(f"✗ Text chunker test failed: {e}")
        return False

async def test_rag_pipeline():
    """Test RAG pipeline functionality."""
    print("\nTesting RAG pipeline...")
    
    try:
        from ai import get_rag_pipeline
        from ai import TextChunk
        
        pipeline = get_rag_pipeline()
        
        # Create mock chunks for testing
        mock_chunks = [
            TextChunk(
                content="The SmartDocs AI system is designed to process PDF documents and provide intelligent question answering capabilities.",
                metadata={"chunk_id": "test_1", "source": "test_doc"}
            ),
            TextChunk(
                content="The system uses OpenAI embeddings for semantic search and GPT models for response generation.",
                metadata={"chunk_id": "test_2", "source": "test_doc"}
            )
        ]
        
        # Test context building
        context = pipeline.build_context_from_chunks(mock_chunks)
        print(f"✓ RAG pipeline initialized successfully")
        print(f"  - Context building works")
        print(f"  - Generated context length: {len(context)} characters")
        
        # Test prompt creation
        test_query = "What is SmartDocs AI?"
        messages = pipeline.create_qa_prompt(test_query, context)
        print(f"  - QA prompt creation works")
        print(f"  - Generated {len(messages)} messages for chat completion")
        
        return True
        
    except Exception as e:
        print(f"✗ RAG pipeline test failed: {e}")
        return False

async def test_compatibility_layer():
    """Test LangChain compatibility layer."""
    print("\nTesting compatibility layer...")
    
    try:
        from langchain_compat import OpenAIEmbeddingsCompat, DocumentCompat, create_documents_from_texts
        
        # Test document compatibility
        docs = create_documents_from_texts(
            ["Test document 1", "Test document 2"],
            [{"source": "test1"}, {"source": "test2"}]
        )
        
        print(f"✓ Compatibility layer working")
        print(f"  - Created {len(docs)} compatible documents")
        print(f"  - Documents have page_content and metadata attributes")
        
        # Test embeddings compatibility wrapper
        embeddings_compat = OpenAIEmbeddingsCompat()
        print(f"  - Embeddings compatibility wrapper initialized")
        print(f"  - Model: {embeddings_compat.model}")
        
        return True
        
    except Exception as e:
        print(f"✗ Compatibility layer test failed: {e}")
        return False

async def test_integration_imports():
    """Test that all imports work correctly."""
    print("\nTesting module imports...")
    
    try:
        # Test main AI module imports
        from ai import (
            DirectOpenAIClient, TextChunker, RAGPipeline,
            get_openai_client, get_text_chunker, get_rag_pipeline,
            embed_texts, chunk_text, generate_rag_response, health_check
        )
        
        # Test compatibility layer imports
        from langchain_compat import (
            DocumentCompat, OpenAIEmbeddingsCompat, RetrieverCompat,
            ChatOpenAICompat, create_documents_from_chunks, create_documents_from_texts
        )
        
        # Test updated services
        from app.services.chat_service import ChatService
        from app.utils.text_processing import split_text_into_chunks, enhance_markdown
        
        print("✓ All imports successful")
        print("  - AI integration module imports: ✓")
        print("  - Compatibility layer imports: ✓")
        print("  - Updated services imports: ✓")
        
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("SmartDocs AI - Direct Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_integration_imports),
        ("OpenAI Client", test_openai_client),
        ("Text Chunker", test_text_chunker),
        ("RAG Pipeline", test_rag_pipeline),
        ("Compatibility Layer", test_compatibility_layer),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<50} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! AI integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)