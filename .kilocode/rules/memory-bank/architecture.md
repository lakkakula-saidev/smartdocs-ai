# SmartDocs AI - System Architecture

## High-Level Architecture

SmartDocs AI follows a modern full-stack architecture with clear separation between frontend, backend, and AI processing components.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React SPA     │────│   FastAPI API    │────│   AI Services   │
│  (Frontend)     │    │   (Backend)      │    │   (LangChain)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────────────┐         ┌─────────────┐        ┌─────────────┐
    │  Vite Dev  │         │ Vector DB   │        │  OpenAI     │
    │  Server    │         │ (ChromaDB)  │        │  API        │
    └────────────┘         └─────────────┘        └─────────────┘
```

## Core Components

### Frontend Architecture ([`frontend/smartdocs-ui/`](../../../frontend/smartdocs-ui/))

#### Application Structure
- **Entry Point**: [`main.tsx`](../../../frontend/smartdocs-ui/src/main.tsx:1) - React app initialization with BrowserRouter
- **Root Component**: [`App.tsx`](../../../frontend/smartdocs-ui/src/App.tsx:1) - Global layout with navigation and routing
- **Pages**: 
  - [`Home.tsx`](../../../frontend/smartdocs-ui/src/pages/Home.tsx:1) - Landing page with upload functionality
  - [`Chat.tsx`](../../../frontend/smartdocs-ui/src/pages/Chat.tsx:1) - Conversational interface

#### Key Components
- **Document Upload** ([`UploadDocument.tsx`](../../../frontend/smartdocs-ui/src/components/UploadDocument.tsx:1)): 
  - Drag-and-drop file upload with progress tracking
  - File validation and error handling
  - PDF-only restriction (backend constraint)
- **Chat Interface** ([`ChatBox.tsx`](../../../frontend/smartdocs-ui/src/components/ChatBox.tsx:1)):
  - Message state management with React hooks
  - Auto-scrolling chat history
  - Built-in markdown test commands
- **Message Rendering** ([`MessageBubble.tsx`](../../../frontend/smartdocs-ui/src/components/MessageBubble.tsx:1)):
  - React Markdown with GFM support
  - Custom styled components for code, tables, lists
  - Heuristic title bolding for better readability

#### State Management
- React hooks for local component state
- URL state for document context passing between pages
- No global state management (suitable for current scope)

#### API Integration
- **API Client** ([`api.ts`](../../../frontend/smartdocs-ui/src/api/api.ts:1)):
  - Axios-based HTTP client with error handling
  - Environment-aware base URL configuration
  - Progress tracking for file uploads
  - Normalized response handling

### Backend Architecture ([`backend/`](../../../backend/))

#### Application Core
- **Main Application** ([`main.py`](../../../backend/main.py:1)): FastAPI app with CORS, error handling, and health checks
- **Lazy Loading**: AI dependencies loaded on-demand to reduce cold start times
- **Environment Management**: Dynamic OpenAI API key loading with fallback support

#### API Endpoints
- **Health Check** (`GET /health`): System status and document registry state
- **Document Upload** (`POST /upload`): PDF processing and vector embedding creation
- **Question Answering** (`POST /ask`): Retrieval-augmented generation with document context

#### Document Processing Pipeline
1. **PDF Text Extraction**: Using `pypdf` for text extraction
2. **Text Chunking**: `RecursiveCharacterTextSplitter` with 1000-character chunks, 150-character overlap
3. **Vector Embeddings**: OpenAI embeddings via `langchain-openai`
4. **Vector Storage**: ChromaDB with persistent collections per document
5. **Retrieval**: Semantic search with k=4 chunk retrieval
6. **Generation**: GPT-4o-mini with retrieved context

#### Storage Architecture
- **Vector Store Registry**: In-memory mapping of document IDs to ChromaDB collections
- **Persistent Storage**: Document collections stored in `backend/vectorstores/<document_id>/`
- **Collection Naming**: Predictable naming pattern `doc_<document_id>`

#### Error Handling
- Comprehensive HTTP exception handling with structured error responses
- Graceful fallbacks for missing dependencies
- Clear error messages for common configuration issues

## Data Flow

### Document Upload Flow
```
User Upload → PDF Validation → Text Extraction → Text Chunking → 
Embedding Creation → Vector Storage → Registry Update → Response
```

### Question Answering Flow  
```
User Query → Document Retrieval → Context Assembly → 
LLM Processing → Response Enhancement → Markdown Formatting → Response
```

## Key Design Patterns

### Frontend Patterns
- **Component Composition**: Small, focused components with clear responsibilities
- **Custom Hooks**: State management abstractions (implicit in current design)
- **Error Boundaries**: Component-level error handling
- **Progressive Enhancement**: Graceful degradation for API failures

### Backend Patterns
- **Dependency Injection**: Lazy loading of heavy AI dependencies
- **Repository Pattern**: Vector store abstraction and management
- **Chain of Responsibility**: Request processing pipeline
- **Factory Pattern**: Dynamic vector store creation

### AI Processing Patterns
- **RAG Architecture**: Retrieval-Augmented Generation with semantic search
- **Chunking Strategy**: Overlap-based text segmentation for context preservation
- **Prompt Enhancement**: Post-processing for improved markdown formatting
- **Lazy Initialization**: On-demand model loading

## Critical Implementation Paths

### Document Processing Path
1. [`UploadDocument.tsx`](../../../frontend/smartdocs-ui/src/components/UploadDocument.tsx:1) → [`api.ts`](../../../frontend/smartdocs-ui/src/api/api.ts:102) → [`main.py:upload_pdf`](../../../backend/main.py:409)
2. [`extract_pdf_text()`](../../../backend/main.py:106) → [`build_and_store_embeddings()`](../../../backend/main.py:134)
3. Vector storage in [`backend/vectorstores/`](../../../backend/vectorstores/)

### Chat Interaction Path
1. [`ChatBox.tsx`](../../../frontend/smartdocs-ui/src/components/ChatBox.tsx:1) → [`api.ts:askQuestion`](../../../frontend/smartdocs-ui/src/api/api.ts:135) → [`main.py:ask`](../../../backend/main.py:440)
2. [`run_retrieval_qa()`](../../../backend/main.py:222) → [`enhance_markdown()`](../../../backend/main.py:344)
3. Response rendering in [`MessageBubble.tsx`](../../../frontend/smartdocs-ui/src/components/MessageBubble.tsx:1)

## Security Considerations

### Frontend Security
- Environment variable handling for API endpoints
- Input validation on file uploads
- XSS prevention through React's built-in protections

### Backend Security
- CORS configuration (currently permissive for development)
- API key management with environment variables
- File upload validation and size limits
- Temporary file cleanup after processing

## Scalability Considerations

### Current Limitations
- In-memory document registry (doesn't persist across restarts)
- Single-threaded processing (suitable for prototype)
- Local file storage (not distributed)

### Scaling Paths
- Database-backed document registry
- Async processing with task queues
- Distributed vector storage
- Authentication and multi-tenancy