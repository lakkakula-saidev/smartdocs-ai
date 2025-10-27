"""
Chat and question-answering routes for SmartDocs AI Backend.

Simplified chat processing using direct AI integration.
"""

import time
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from config import get_settings
from models import AskRequest, AskResponse, ErrorResponse
from storage import get_unified_storage, DocumentNotFoundError
from security import InputSanitizer
import ai

# Create router
router = APIRouter(
    prefix="",
    tags=["chat"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - validation error"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    }
)


def enhance_markdown(text: str) -> str:
    """
    Simple markdown enhancement for better readability.
    
    Args:
        text: Raw text to enhance
        
    Returns:
        Enhanced text with better markdown formatting
    """
    if not text:
        return text
    
    lines = text.split('\n')
    enhanced_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            enhanced_lines.append('')
            continue
            
        # Bold important keywords
        important_keywords = [
            'summary', 'conclusion', 'key points', 'important', 'note',
            'findings', 'results', 'recommendations', 'main', 'primary'
        ]
        
        for keyword in important_keywords:
            if keyword.lower() in line.lower() and not line.startswith('#'):
                # Make the keyword bold if not already formatted
                if f'**{keyword}**' not in line.lower():
                    line = line.replace(keyword, f'**{keyword}**')
                    line = line.replace(keyword.title(), f'**{keyword.title()}**')
        
        enhanced_lines.append(line)
    
    return '\n'.join(enhanced_lines)


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask Question About Document",
    description="""
    Ask a natural language question about a previously uploaded document.
    
    This endpoint uses Retrieval-Augmented Generation (RAG) to:
    1. Retrieve relevant document chunks based on semantic similarity
    2. Generate a contextual answer using OpenAI's GPT model
    3. Enhance the response with improved markdown formatting
    """
)
async def ask_question(request: AskRequest) -> AskResponse:
    """
    Ask a question about a document using RAG-based question answering.
    
    Args:
        request: Question request with query and document ID
        
    Returns:
        AI-generated answer with enhanced formatting
        
    Raises:
        HTTPException: Various HTTP errors for validation, processing, or service issues
    """
    start_time = time.time()
    
    # Sanitize user input
    sanitized_query = InputSanitizer.sanitize_query(request.query)
    if not sanitized_query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty after sanitization"
        )
    
    print(f"[chat] Question asked about document {request.document_id}")
    
    try:
        # Check if OpenAI API key is configured
        settings = get_settings()
        if not settings.has_openai_key:
            print("[chat] ERROR: Question asked without OpenAI API key")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI processing service not available. OpenAI API key not configured."
            )
        
        # Get storage system
        storage = get_unified_storage()
        
        # Step 1: Verify document exists
        try:
            await storage.get_document(request.document_id)
        except DocumentNotFoundError:
            print(f"[chat] Document not found: {request.document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{request.document_id}' not found"
            )
        
        # Step 2: Query document for relevant chunks
        try:
            relevant_chunks = await storage.query_document(
                document_id=request.document_id,
                query=sanitized_query,
                k=settings.retrieval_k
            )
            
            print(f"[chat] Retrieved {len(relevant_chunks)} relevant chunks")
            
        except Exception as e:
            print(f"[chat] ERROR: Failed to retrieve document chunks: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve relevant information from document"
            )
        
        # Step 3: Generate AI response using RAG
        try:
            # Convert chunks to the format expected by RAG pipeline
            formatted_chunks = []
            for chunk in relevant_chunks:
                # Create a simple object with content attribute
                class ChunkObj:
                    def __init__(self, content):
                        self.content = content
                        self.page_content = content  # For compatibility
                
                formatted_chunks.append(ChunkObj(chunk['content']))
            
            # Generate response using RAG pipeline
            raw_answer = await ai.generate_rag_response(
                query=sanitized_query,
                retrieved_chunks=formatted_chunks,
                document_id=request.document_id
            )
            
            # Enhance response formatting
            enhanced_answer = enhance_markdown(raw_answer)
            
        except Exception as e:
            print(f"[chat] ERROR: Failed to generate AI response: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Question answering service temporarily unavailable"
            )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        response = AskResponse(
            answer=enhanced_answer,
            document_id=request.document_id,
            processing_time_ms=processing_time_ms,
            source_chunks_count=len(relevant_chunks)
        )
        
        print(f"[chat] Question answered successfully in {processing_time_ms}ms")
        
        return response
        
    except HTTPException:
        raise
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log error securely without exposing details
        error_id = __import__('secrets').token_hex(8)
        print(f"[chat] ERROR [{error_id}]: Question answering failed: {type(e).__name__}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Question answering failed due to internal error"
        )


@router.post(
    "/chat/session",
    response_model=Dict[str, Any],
    summary="Start Chat Session",
    description="""
    Start a new chat session for a document.
    
    Note: This is a placeholder endpoint for future session management.
    Currently, all questions are stateless and don't require session initialization.
    """
)
async def start_chat_session(document_id: str) -> Dict[str, Any]:
    """
    Start a new chat session for a document.
    
    Args:
        document_id: Document identifier for the chat session
        
    Returns:
        Chat session information
    """
    print(f"[chat] Chat session creation requested for document {document_id}")
    
    try:
        # Verify document exists
        storage = get_unified_storage()
        await storage.get_document(document_id)
        
        # For now, return a simple session response
        session_response = {
            "session_id": f"session_{document_id[:24]}",
            "document_id": document_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "status": "active",
            "message": "Chat session created successfully. You can now ask questions about the document."
        }
        
        print(f"[chat] Chat session created: {session_response['session_id']}")
        
        return session_response
        
    except DocumentNotFoundError:
        print(f"[chat] Cannot create session - document not found: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found"
        )
        
    except Exception as e:
        print(f"[chat] ERROR: Failed to create chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.get(
    "/chat/test",
    response_model=Dict[str, Any],
    summary="Test Chat Service",
    description="""
    Test endpoint to verify chat service functionality and configuration.
    
    This endpoint performs basic checks including:
    - Chat service initialization
    - OpenAI API connectivity
    - AI integration status
    - Storage system access
    """
)
async def test_chat_service() -> Dict[str, Any]:
    """
    Test chat service functionality.
    
    Returns:
        Test results and service status
    """
    print("[chat] Chat service test requested")
    
    test_results = {
        "status": "healthy",
        "tests": {
            "service_initialization": "passed",
            "openai_connectivity": "unknown",
            "ai_integration": "unknown",
            "storage_access": "unknown"
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    }
    
    try:
        # Test AI integration
        try:
            ai_health = await ai.health_check()
            if ai_health.get("status") == "healthy":
                test_results["tests"]["ai_integration"] = "passed"
                test_results["tests"]["openai_connectivity"] = "passed"
            else:
                test_results["tests"]["ai_integration"] = "failed"
                test_results["status"] = "degraded"
        except Exception as e:
            test_results["tests"]["ai_integration"] = f"failed: {str(e)}"
            test_results["status"] = "unhealthy"
        
        # Test storage access
        try:
            storage = get_unified_storage()
            storage_health = await storage.health_check()
            if storage_health.get("status") == "healthy":
                test_results["tests"]["storage_access"] = "passed"
            else:
                test_results["tests"]["storage_access"] = "failed: storage unhealthy"
                test_results["status"] = "degraded"
        except Exception as e:
            test_results["tests"]["storage_access"] = f"failed: {str(e)}"
            test_results["status"] = "unhealthy"
        
        print(f"[chat] Chat service test completed: {test_results['status']}")
        
        return test_results
        
    except Exception as e:
        print(f"[chat] ERROR: Chat service test failed: {e}")
        
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Chat service test failed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        }