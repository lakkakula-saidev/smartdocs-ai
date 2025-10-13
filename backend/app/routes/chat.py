"""
Chat and question-answering route handlers for SmartDocs AI Backend.

This module provides endpoints for conversational document interaction,
including question answering, context retrieval, and chat session
management using retrieval-augmented generation (RAG).
"""

import time
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..exceptions import (
    SmartDocsException,
    DocumentNotFoundError
)
from ..logger import get_logger
from ..models.schemas import (
    AskRequest,
    AskResponse,
    ErrorResponse
)
from ..services.chat_service import ChatService

# Create router with proper tags and metadata
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

logger = get_logger("chat_routes")


def get_chat_service(settings: Settings = Depends(get_settings)) -> ChatService:
    """
    Dependency to provide ChatService instance.
    
    Args:
        settings: Application settings from dependency injection
        
    Returns:
        Configured ChatService instance
    """
    return ChatService(settings=settings)


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
    
    **Query Guidelines:**
    - Use natural language questions (e.g., "What is the main topic?")
    - Be specific for better results (e.g., "What are the technical specifications for the API?")
    - Questions can be analytical (e.g., "Summarize the key findings")
    - Follow-up questions are supported within the same document context
    
    **Response Features:**
    - Markdown-formatted answers with enhanced readability
    - Contextual information based on document content
    - Processing time and source chunk metadata
    - Consistent formatting for lists, headings, and emphasis
    
    **Processing Time:**
    - Simple queries: ~1-3 seconds
    - Complex analytical queries: ~3-8 seconds
    - Large document context: ~5-12 seconds
    """,
    responses={
        200: {
            "description": "Question answered successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "simple_question": {
                            "summary": "Simple factual question",
                            "value": {
                                "answer": "The document discusses **machine learning algorithms** with focus on:\n\n1. **Neural Networks**: Deep learning approaches for pattern recognition\n2. **Decision Trees**: Classification methods for structured data\n3. **Clustering**: Unsupervised learning techniques for data grouping\n\nThe main emphasis is on practical applications in **data science** and **artificial intelligence**.",
                                "document_id": "a1b2c3d4e5f6789012345678901234ab",
                                "processing_time_ms": 1250,
                                "source_chunks_count": 4
                            }
                        },
                        "analytical_question": {
                            "summary": "Complex analytical query",
                            "value": {
                                "answer": "## Key Findings Summary\n\nThe research presents several important discoveries:\n\n**Primary Results:**\n- **Performance Improvement**: 23% increase in accuracy over baseline models\n- **Processing Speed**: 40% reduction in computation time\n- **Resource Efficiency**: 15% decrease in memory usage\n\n**Technical Innovations:**\n- Novel attention mechanism for better context understanding\n- Optimized training pipeline with reduced data requirements\n- Enhanced model architecture supporting larger input sequences\n\n**Implications:**\nThese findings suggest that the proposed approach could significantly impact production systems requiring **real-time processing** with **high accuracy** demands.",
                                "document_id": "a1b2c3d4e5f6789012345678901234ab",
                                "processing_time_ms": 2800,
                                "source_chunks_count": 6
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid request - empty query or validation error",
            "content": {
                "application/json": {
                    "examples": {
                        "empty_query": {
                            "summary": "Empty or invalid query",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "message": "Query cannot be empty or only whitespace",
                                "error_code": "VALIDATION_ERROR",
                                "details": {
                                    "field": "query",
                                    "received_value": "   "
                                }
                            }
                        },
                        "invalid_document_id": {
                            "summary": "Invalid document ID format",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "message": "Document ID must be a 32-character hex string",
                                "error_code": "VALIDATION_ERROR",
                                "details": {
                                    "field": "document_id",
                                    "received_value": "invalid123",
                                    "expected_format": "32-character hex string"
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Document not found",
            "content": {
                "application/json": {
                    "examples": {
                        "document_not_found": {
                            "summary": "Document ID not found",
                            "value": {
                                "error": True,
                                "status_code": 404,
                                "message": "Document with ID 'a1b2c3d4e5f6789012345678901234ab' not found",
                                "error_code": "DOCUMENT_NOT_FOUND",
                                "details": {
                                    "document_id": "a1b2c3d4e5f6789012345678901234ab",
                                    "suggestion": "Verify the document ID or upload the document first"
                                }
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable (OpenAI API issues)",
            "content": {
                "application/json": {
                    "examples": {
                        "openai_unavailable": {
                            "summary": "OpenAI API service unavailable",
                            "value": {
                                "error": True,
                                "status_code": 503,
                                "message": "Question answering service temporarily unavailable",
                                "error_code": "OPENAI_API_UNAVAILABLE",
                                "details": {
                                    "service": "OpenAI Chat Completions API",
                                    "retry_after_seconds": 30
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def ask_question(
    request: AskRequest,
    chat_service: ChatService = Depends(get_chat_service)
) -> AskResponse:
    """
    Ask a question about a document using RAG-based question answering.
    
    Args:
        request: Question request with query and document ID
        chat_service: Chat service dependency
        
    Returns:
        AI-generated answer with enhanced formatting
        
    Raises:
        HTTPException: Various HTTP errors for validation, processing, or service issues
    """
    start_time = time.time()
    
    logger.info(
        "Question answering requested",
        extra={
            "document_id": request.document_id,
            "query_length": len(request.query),
            "query_preview": request.query[:100] + "..." if len(request.query) > 100 else request.query
        }
    )
    
    try:
        # Process the question using chat service
        chat_response = await chat_service.ask_question(request)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Create response with processing metadata
        response = AskResponse(
            answer=chat_response.answer,
            document_id=request.document_id,
            processing_time_ms=processing_time_ms,
            source_chunks_count=chat_response.source_chunks_count
        )
        
        logger.info(
            "Question answered successfully",
            extra={
                "document_id": request.document_id,
                "processing_time_ms": processing_time_ms,
                "answer_length": len(response.answer),
                "source_chunks": chat_response.source_chunks_count
            }
        )
        
        return response
        
    except DocumentNotFoundError as e:
        logger.warning(
            "Document not found for question answering",
            extra={
                "document_id": request.document_id,
                "query_preview": request.query[:100]
            }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{request.document_id}' not found"
        )
        
    except SmartDocsException as e:
        logger.error(
            "SmartDocs error during question answering",
            extra={
                "document_id": request.document_id,
                "error_code": e.error_code,
                "message": e.message
            },
            exc_info=True
        )
        
        # Map processing errors to HTTP status codes
        if "OPENAI" in e.error_code or "API" in e.error_code:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif "VALIDATION" in e.error_code:
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
        raise HTTPException(
            status_code=status_code,
            detail=e.message
        )
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.error(
            "Unexpected error during question answering",
            extra={
                "document_id": request.document_id,
                "error": str(e),
                "processing_time_ms": processing_time_ms
            },
            exc_info=True
        )
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
    
    Chat sessions can help maintain context across multiple questions
    and provide more coherent conversation flows. While not required
    for individual questions, sessions can improve response quality
    for follow-up questions and contextual conversations.
    
    **Note**: This is a placeholder endpoint for future session management.
    Currently, all questions are stateless and don't require session initialization.
    """,
    responses={
        200: {
            "description": "Chat session created successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "session_created": {
                            "summary": "New chat session",
                            "value": {
                                "session_id": "session_a1b2c3d4e5f6789012345678",
                                "document_id": "a1b2c3d4e5f6789012345678901234ab",
                                "created_at": "2024-01-15T10:30:00.000Z",
                                "status": "active",
                                "message": "Chat session created successfully. You can now ask questions about the document."
                            }
                        }
                    }
                }
            }
        }
    }
)
async def start_chat_session(
    document_id: str,
    chat_service: ChatService = Depends(get_chat_service)
) -> Dict[str, Any]:
    """
    Start a new chat session for a document.
    
    Args:
        document_id: Document identifier for the chat session
        chat_service: Chat service dependency
        
    Returns:
        Chat session information
        
    Note:
        This is a placeholder implementation. Future versions may include
        proper session management with conversation history and context.
    """
    logger.info(
        "Chat session creation requested",
        extra={"document_id": document_id}
    )
    
    try:
        # Verify document exists by attempting to get its info
        # This will raise DocumentNotFoundError if document doesn't exist
        await chat_service.validate_document_access(document_id)
        
        # For now, return a simple session response
        # Future implementation could include proper session management
        session_response = {
            "session_id": f"session_{document_id[:24]}",
            "document_id": document_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "status": "active",
            "message": "Chat session created successfully. You can now ask questions about the document."
        }
        
        logger.info(
            "Chat session created successfully",
            extra={
                "document_id": document_id,
                "session_id": session_response["session_id"]
            }
        )
        
        return session_response
        
    except DocumentNotFoundError:
        logger.warning(
            "Cannot create chat session - document not found",
            extra={"document_id": document_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found"
        )
        
    except Exception as e:
        logger.error(
            "Error creating chat session",
            extra={"document_id": document_id, "error": str(e)},
            exc_info=True
        )
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
    - LangChain dependencies
    - Vector store access
    
    Useful for debugging and system verification.
    """,
    responses={
        200: {
            "description": "Chat service test results",
            "content": {
                "application/json": {
                    "examples": {
                        "test_success": {
                            "summary": "All tests passed",
                            "value": {
                                "status": "healthy",
                                "tests": {
                                    "service_initialization": "passed",
                                    "openai_connectivity": "passed",
                                    "langchain_dependencies": "passed",
                                    "vector_store_access": "passed"
                                },
                                "message": "Chat service is functioning correctly",
                                "timestamp": "2024-01-15T10:30:00.000Z"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def test_chat_service(
    chat_service: ChatService = Depends(get_chat_service)
) -> Dict[str, Any]:
    """
    Test chat service functionality.
    
    Args:
        chat_service: Chat service dependency
        
    Returns:
        Test results and service status
    """
    logger.info("Chat service test requested")
    
    try:
        # Perform service health check
        test_results = await chat_service.health_check()
        
        logger.info(
            "Chat service test completed",
            extra={"test_status": test_results.get("status", "unknown")}
        )
        
        return {
            **test_results,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        }
        
    except Exception as e:
        logger.error(
            "Chat service test failed",
            extra={"error": str(e)},
            exc_info=True
        )
        
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Chat service test failed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        }