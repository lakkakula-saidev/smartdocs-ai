# SmartDocs AI Backend - Core Infrastructure

This document describes the core configuration and logging infrastructure created for the modular FastAPI backend refactoring.

## Created Components

### 1. Configuration Management (`app/config.py`)
- **Pydantic BaseSettings** for environment variable management
- **Environment-aware configuration** with development/production modes
- **Comprehensive validation** with field validators
- **OpenAI API key management** with runtime validation
- **Vector store provider configuration** (Chroma/Pinecone support)
- **File upload constraints** and processing parameters
- **CORS and server configuration**

Key features:
- Automatic `.env` file discovery with diagnostic logging
- Computed properties for derived values
- Singleton pattern for consistent configuration access
- Backward compatibility with original `main.py` patterns

### 2. Structured Logging (`app/logger.py`)
- **JSON-structured logging** for production environments
- **Colored console logging** for development
- **Context management** for request tracking
- **Function decoration** for automatic call logging
- **Multiple log levels** with proper formatting
- **Exception handling** with full traceback capture

Key features:
- Configurable log formats (structured/simple)
- Extra field support for contextual information
- Logger mixins for easy class integration
- Environment-aware formatting (colors in dev only)

### 3. Utility Modules (`app/utils/`)

#### File Utilities (`file_utils.py`)
- **PDF text extraction** with pypdf integration
- **File validation** against configured constraints
- **Temporary file management** with automatic cleanup
- **Secure filename sanitization**
- **Upload progress tracking**

#### Text Processing (`text_processing.py`)
- **Intelligent text chunking** with LangChain integration
- **Markdown enhancement** for better readability
- **Text cleaning and normalization**
- **Token counting** with tiktoken support
- **File size formatting utilities**

#### Validation (`validation.py`)
- **Query validation** with length and content checks
- **Document ID validation** with format enforcement
- **Pagination parameter validation**
- **API key format validation**
- **Security pattern detection**

### 4. Exception Handling (`app/exceptions.py`)
- **Custom exception hierarchy** for domain-specific errors
- **Standardized error responses** with structured format
- **FastAPI exception handlers** with proper HTTP status codes
- **Development vs production error exposure**
- **Context managers** for exception mapping
- **Utility functions** for common error scenarios

Key exception types:
- `ConfigurationError` - Environment/setup issues
- `DocumentProcessingError` - PDF/text processing failures
- `VectorStoreError` - Database operation failures
- `AIServiceError` - LLM/API service issues
- `ValidationError` - Input validation failures
- `DocumentNotFoundError` - Resource not found

## Configuration Features

### Environment Variables Supported
```bash
# Core Configuration
ENVIRONMENT=development|production|testing
DEBUG=true|false
HOST=0.0.0.0
PORT=8000

# AI/LLM Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1

# Vector Store Configuration
VECTOR_STORE_PROVIDER=chroma|pinecone
VECTOR_STORE_PERSIST_DIR=backend/vectorstores

# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
RETRIEVAL_K=4

# File Upload Configuration
MAX_UPLOAD_SIZE_MB=50
ALLOWED_FILE_TYPES=application/pdf

# Logging Configuration
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
LOG_FORMAT=structured|simple

# CORS Configuration
CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true

# Pinecone Configuration (optional)
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...
PINECONE_INDEX_NAME=smartdocs-ai
```

### Computed Properties
- `max_upload_size_bytes` - Upload size in bytes
- `vector_store_path` - Path object for storage directory
- `is_development` / `is_production` - Environment checks

## Testing

A comprehensive test suite (`test_infrastructure.py`) validates all components:

```bash
cd backend
python test_infrastructure.py
```

Test coverage includes:
- ✅ Configuration loading and validation
- ✅ Structured logging functionality
- ✅ Utility function operations
- ✅ Exception handling and formatting
- ✅ Module integration

## Integration with FastAPI

The infrastructure is designed to integrate seamlessly with FastAPI applications:

```python
from app.config import get_settings
from app.logger import get_logger
from app.exceptions import setup_exception_handlers

# Get configuration
settings = get_settings()

# Get logger
logger = get_logger("api")

# Setup FastAPI app with exception handlers
app = FastAPI(title=settings.app_name, version=settings.app_version)
setup_exception_handlers(app)
```

## Dependencies Added

Updated `requirements.txt` includes:
- `pydantic-settings` - For Pydantic v2 BaseSettings support

## File Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── logger.py              # Structured logging
│   ├── exceptions.py          # Exception handling
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py      # File operations
│       ├── text_processing.py # Text manipulation
│       └── validation.py      # Input validation
├── test_infrastructure.py     # Infrastructure tests
├── requirements.txt           # Updated dependencies
└── INFRASTRUCTURE.md          # This documentation
```

## Next Steps

This infrastructure provides the foundation for:
1. **Service Layer** - Business logic modules
2. **Repository Layer** - Data access abstractions  
3. **API Routes** - Endpoint definitions
4. **Model Definitions** - Pydantic schemas
5. **Dependency Injection** - FastAPI dependencies

The modular design ensures clean separation of concerns and makes the codebase more maintainable and testable.