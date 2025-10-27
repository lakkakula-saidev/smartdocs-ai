"""
LangChain Compatibility Layer for SmartDocs AI Backend.

This module provides compatibility wrappers that allow existing code expecting
LangChain interfaces to work with our direct AI integration module.

Key Components:
- OpenAIEmbeddingsCompat: Wrapper to make our OpenAI client compatible with LangChain embeddings interface
- DocumentCompat: Simple document wrapper for text chunks
- RetrieverCompat: Compatibility wrapper for retrievers
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from ai import get_openai_client, get_rag_pipeline, TextChunk


@dataclass
class DocumentCompat:
    """
    Simple document wrapper compatible with LangChain Document interface.
    
    Provides page_content and metadata attributes expected by existing code.
    """
    page_content: str
    metadata: Dict[str, Any]
    
    def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
        self.page_content = page_content
        self.metadata = metadata or {}


class OpenAIEmbeddingsCompat:
    """
    Compatibility wrapper for OpenAI embeddings that mimics LangChain interface.
    
    This allows existing vector store code to work with our direct OpenAI integration
    without requiring extensive rewrites.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize embeddings compatibility wrapper.
        
        Args:
            openai_api_key: OpenAI API key (not used, for compatibility only)
        """
        self.client = get_openai_client()
        self.model = self.client.embedding_model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed documents synchronously (compatibility method).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Use asyncio to run async method
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we need to use a different approach
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._embed_async(texts))
                result = future.result()
        else:
            result = loop.run_until_complete(self._embed_async(texts))
        
        return result.embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else []
    
    async def _embed_async(self, texts: List[str]):
        """Internal async embedding method."""
        return await self.client.generate_embeddings(texts)


class RetrieverCompat:
    """
    Compatibility wrapper for retrievers.
    
    Provides interface expected by existing code while using our direct implementations.
    """
    
    def __init__(self, vector_store, k: int = 4):
        """
        Initialize retriever compatibility wrapper.
        
        Args:
            vector_store: Vector store instance
            k: Number of chunks to retrieve
        """
        self.vector_store = vector_store
        self.k = k
    
    def invoke(self, query: str) -> List[DocumentCompat]:
        """
        Retrieve documents for query (sync interface for compatibility).
        
        Args:
            query: Search query
            
        Returns:
            List of compatible document objects
        """
        # For now, return empty list as we're using the RAG pipeline directly
        # In a full implementation, this would interface with the vector store
        return []
    
    def get_relevant_documents(self, query: str) -> List[DocumentCompat]:
        """
        Alternative method name for compatibility.
        
        Args:
            query: Search query
            
        Returns:
            List of compatible document objects
        """
        return self.invoke(query)


def create_documents_from_chunks(chunks: List[TextChunk]) -> List[DocumentCompat]:
    """
    Convert TextChunk objects to LangChain-compatible Document objects.
    
    Args:
        chunks: List of TextChunk objects
        
    Returns:
        List of DocumentCompat objects
    """
    return [
        DocumentCompat(
            page_content=chunk.content,
            metadata=chunk.metadata
        )
        for chunk in chunks
    ]


def create_documents_from_texts(texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[DocumentCompat]:
    """
    Create Document objects from texts and metadata.
    
    Args:
        texts: List of text content
        metadatas: Optional list of metadata dictionaries
        
    Returns:
        List of DocumentCompat objects
    """
    if metadatas is None:
        metadatas = [{}] * len(texts)
    
    return [
        DocumentCompat(page_content=text, metadata=metadata)
        for text, metadata in zip(texts, metadatas)
    ]


# Convenience functions for backward compatibility
def get_openai_embeddings(api_key: Optional[str] = None) -> OpenAIEmbeddingsCompat:
    """Get OpenAI embeddings compatibility wrapper."""
    return OpenAIEmbeddingsCompat(api_key)


class ChatOpenAICompat:
    """
    Compatibility wrapper for ChatOpenAI that uses our direct integration.
    
    Provides interface expected by existing code.
    """
    
    def __init__(self, temperature: float = 0.1, model_name: str = None, openai_api_key: str = None):
        """
        Initialize chat compatibility wrapper.
        
        Args:
            temperature: Sampling temperature
            model_name: Model name (not used, for compatibility)
            openai_api_key: API key (not used, for compatibility)
        """
        self.client = get_openai_client()
        self.temperature = temperature
        self.model_name = model_name or self.client.chat_model
    
    def invoke(self, messages) -> Any:
        """
        Invoke chat completion (sync interface for compatibility).
        
        Args:
            messages: Messages to send
            
        Returns:
            Response object with content attribute
        """
        # Convert LangChain message format to our format
        if hasattr(messages, 'to_messages'):
            # Handle prompt templates
            formatted_messages = messages.to_messages()
        elif isinstance(messages, list):
            formatted_messages = messages
        else:
            formatted_messages = [{"role": "user", "content": str(messages)}]
        
        # Convert to our expected format
        our_messages = []
        for msg in formatted_messages:
            if hasattr(msg, 'content') and hasattr(msg, 'type'):
                # LangChain message object
                role = "user" if msg.type == "human" else msg.type
                our_messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                our_messages.append(msg)
            else:
                our_messages.append({"role": "user", "content": str(msg)})
        
        # Use asyncio to run async method
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._chat_async(our_messages))
                result = future.result()
        else:
            result = loop.run_until_complete(self._chat_async(our_messages))
        
        # Return object with content attribute for compatibility
        class ResponseCompat:
            def __init__(self, content: str):
                self.content = content
        
        return ResponseCompat(result.content)
    
    async def _chat_async(self, messages: List[Dict[str, str]]):
        """Internal async chat method."""
        return await self.client.chat_completion(
            messages=messages,
            temperature=self.temperature
        )


# Export compatibility classes for import
__all__ = [
    'DocumentCompat',
    'OpenAIEmbeddingsCompat', 
    'RetrieverCompat',
    'ChatOpenAICompat',
    'create_documents_from_chunks',
    'create_documents_from_texts',
    'get_openai_embeddings'
]