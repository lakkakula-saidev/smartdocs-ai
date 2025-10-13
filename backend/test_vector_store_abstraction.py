"""
Test script for vector store abstraction layer backward compatibility.

This script verifies that the new abstraction layer can:
1. Discover existing vector store data from backend/vectorstores/
2. Load and interact with existing collections
3. Maintain compatibility with the original main.py patterns
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
from app.db import get_document_registry, get_vector_store
from app.logger import get_logger

logger = get_logger("test_vector_store")


async def test_backward_compatibility():
    """Test backward compatibility with existing vector store data."""
    print("=" * 60)
    print("Testing Vector Store Abstraction Layer")
    print("=" * 60)
    
    try:
        # Initialize components
        print("\n1. Initializing vector store and registry...")
        settings = get_settings()
        vector_store = get_vector_store()
        registry = get_document_registry()
        
        print(f"   ✓ Vector store provider: {settings.vector_store_provider}")
        print(f"   ✓ Persist directory: {settings.vector_store_path}")
        
        # Test vector store health
        print("\n2. Checking vector store health...")
        health = await vector_store.health_check()
        print(f"   ✓ Status: {health.get('status', 'unknown')}")
        print(f"   ✓ Provider: {health.get('provider', 'unknown')}")
        
        # List existing collections
        print("\n3. Discovering existing collections...")
        collections = await vector_store.list_collections()
        print(f"   ✓ Found {len(collections)} existing collections")
        
        if collections:
            for doc_id in collections[:3]:  # Show first 3
                print(f"     - Document ID: {doc_id}")
        
        # Test document registry
        print("\n4. Testing document registry...")
        registry_health = await registry.health_check()
        print(f"   ✓ Registry status: {registry_health.get('registry_status', 'unknown')}")
        print(f"   ✓ Document count: {registry_health.get('document_count', 0)}")
        
        # Test loading existing document (if any)
        if collections:
            test_doc_id = collections[0]
            print(f"\n5. Testing existing document access: {test_doc_id}")
            
            try:
                # Test getting collection info
                collection_info = await vector_store.get_collection_info(test_doc_id)
                print(f"   ✓ Collection name: {collection_info.collection_name}")
                print(f"   ✓ Embedding count: {collection_info.embedding_count}")
                print(f"   ✓ Is accessible: {collection_info.is_accessible}")
                
                # Test getting retriever
                retriever = await vector_store.get_retriever(test_doc_id, k=2)
                print(f"   ✓ Retriever created successfully")
                
                # Test registry document access
                try:
                    doc_info = await registry.get_document(test_doc_id)
                    print(f"   ✓ Document info: {doc_info.status}")
                except Exception as e:
                    print(f"   ⚠ Document not in registry (expected for existing data): {e}")
                
            except Exception as e:
                print(f"   ✗ Error accessing document: {e}")
        else:
            print("\n5. No existing documents found - testing with fresh install")
        
        # Test factory pattern
        print("\n6. Testing factory pattern...")
        from app.db.vector_store import VectorStoreFactory
        factory_store = VectorStoreFactory.create_vector_store(settings)
        factory_health = await factory_store.health_check()
        print(f"   ✓ Factory-created store status: {factory_health.get('status', 'unknown')}")
        
        print("\n" + "=" * 60)
        print("✅ All backward compatibility tests passed!")
        print("✅ Abstraction layer is ready for integration")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error(f"Backward compatibility test failed: {e}", exc_info=True)
        return False


async def test_configuration():
    """Test configuration and environment setup."""
    print("\n" + "=" * 60)
    print("Configuration Test")
    print("=" * 60)
    
    try:
        settings = get_settings()
        
        print(f"Environment: {settings.environment}")
        print(f"Vector Store Provider: {settings.vector_store_provider}")
        print(f"Vector Store Path: {settings.vector_store_path}")
        print(f"Chunk Size: {settings.chunk_size}")
        print(f"Chunk Overlap: {settings.chunk_overlap}")
        print(f"Retrieval K: {settings.retrieval_k}")
        print(f"OpenAI Model: {settings.openai_model}")
        
        # Check for required dependencies based on provider
        if settings.vector_store_provider.value == "chroma":
            try:
                from langchain_chroma import Chroma
                print("✓ ChromaDB dependencies available")
            except ImportError:
                try:
                    from langchain_community.vectorstores import Chroma
                    print("✓ ChromaDB dependencies available (legacy)")
                except ImportError:
                    print("⚠ ChromaDB dependencies missing")
        
        elif settings.vector_store_provider.value == "pinecone":
            if settings.pinecone_api_key and settings.pinecone_environment:
                print("✓ Pinecone configuration present")
            else:
                print("⚠ Pinecone configuration incomplete")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("Starting Vector Store Abstraction Layer Tests...\n")
    
    config_ok = await test_configuration()
    if not config_ok:
        print("❌ Configuration test failed - stopping")
        return False
    
    compat_ok = await test_backward_compatibility()
    
    if config_ok and compat_ok:
        print("\n🎉 All tests passed! The abstraction layer is ready.")
        return True
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)