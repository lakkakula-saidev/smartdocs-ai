# SmartDocs AI - Technology Stack

## Backend Technologies

### Core Framework
- **FastAPI**: Modern Python web framework for building APIs
  - Auto-generated OpenAPI documentation
  - Built-in validation with Pydantic models
  - Async support and high performance
  - CORS middleware for frontend integration

### AI & Machine Learning Stack
- **LangChain**: Framework for building applications with language models
  - `langchain`: Core framework for chains and agents
  - `langchain-openai`: OpenAI integration for embeddings and chat models
  - `langchain-chroma`: ChromaDB integration for vector storage
- **OpenAI API**: Large language model services
  - GPT-4o-mini for question answering
  - Text embedding models for semantic search
- **ChromaDB**: Vector database for document embeddings
  - Persistent storage of document chunks
  - Semantic similarity search capabilities

### Document Processing
- **pypdf**: PDF text extraction library
- **tiktoken**: Token counting for OpenAI models
- **RecursiveCharacterTextSplitter**: Intelligent text chunking

### Development & Deployment
- **Uvicorn**: ASGI server for FastAPI applications
- **python-multipart**: File upload handling
- **python-dotenv**: Environment variable management
- **Makefile**: Development workflow automation

### Python Version
- **Python 3.12+**: Required for modern typing and performance features

## Frontend Technologies

### Core Framework
- **React 19**: Latest React with concurrent features
- **TypeScript**: Type-safe JavaScript development
- **Vite**: Modern build tool and development server
  - Hot module replacement (HMR)
  - Fast builds and optimized bundling

### UI & Styling
- **Tailwind CSS**: Utility-first CSS framework
  - Custom design system with brand colors
  - Dark theme with gradient backgrounds
  - Responsive design patterns
- **CSS Custom Properties**: Dynamic theming support
- **Custom Animations**: Fade-in and slide-up transitions

### Routing & Navigation
- **React Router DOM**: Client-side routing
  - Browser history management
  - State passing between routes

### HTTP Client & API Integration
- **Axios**: Promise-based HTTP client
  - Request/response interceptors
  - Upload progress tracking
  - Error handling and retries

### Markdown Processing
- **React Markdown**: Markdown rendering in React
- **remark-gfm**: GitHub Flavored Markdown support
- **Custom Components**: Styled markdown elements

### State Persistence
- **Zustand**: State management with persist middleware for chat histories stored in localStorage (key: "smartdocs-chat-storage")

### Development Tools
- **ESLint**: Code linting with TypeScript support
- **TypeScript ESLint**: TypeScript-specific linting rules
- **PostCSS**: CSS processing with Tailwind
- **Autoprefixer**: Cross-browser CSS compatibility

### Node.js Version
- **Node.js 18+**: Required for modern JavaScript features

## Development Environment

### Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Environment variables
export OPENAI_API_KEY=sk-...

# Development server
make dev  # or fastapi dev main.py
```

### Frontend Setup
```bash
# Install dependencies
npm install  # or yarn/pnpm

# Development server
npm run dev  # or yarn dev
```

### Development Servers
- **Backend**: `http://localhost:8000` (FastAPI with auto-reload)
- **Frontend**: `http://localhost:5173` (Vite dev server)

## Build & Deployment

### Backend Production
- **Uvicorn**: Production ASGI server
- **Docker**: Containerization support (infrastructure ready)
- **Environment Variables**: Configuration via `.env` files

### Frontend Production
- **Vite Build**: Optimized production bundles
- **TypeScript Compilation**: Type checking and compilation
- **Static Hosting**: Compatible with CDN deployment

## Development Dependencies

### Backend Dev Dependencies
- **fastapi[standard]**: Full FastAPI with optional dependencies
- **python-dotenv**: Development environment management

### Frontend Dev Dependencies
- **@vitejs/plugin-react**: React support for Vite
- **TypeScript**: Type checking and compilation
- **ESLint ecosystem**: Code quality and consistency
- **Tailwind CSS**: Styling framework with PostCSS

## Configuration Files

### Backend Configuration
- [`requirements.txt`](../../../backend/requirements.txt:1): Python dependencies
- [`Makefile`](../../../backend/Makefile:1): Development commands
- [`.env`](..): Environment variables (not tracked)

### Frontend Configuration
- [`package.json`](../../../frontend/smartdocs-ui/package.json:1): Node.js dependencies and scripts
- [`vite.config.ts`](../../../frontend/smartdocs-ui/vite.config.ts:1): Vite build configuration
- [`tailwind.config.js`](../../../frontend/smartdocs-ui/tailwind.config.js:1): Tailwind CSS customization
- [`tsconfig.json`](../../../frontend/smartdocs-ui/tsconfig.json:1): TypeScript configuration
- [`eslint.config.js`](../../../frontend/smartdocs-ui/eslint.config.js:1): ESLint rules

## Known Issues & Dependencies

### Backend Issues
- **Missing Dependencies**: `langchain-openai` and `langchain-chroma` need installation
- **Import Path**: Chroma import needs update from `langchain_community` to `langchain_chroma`
- **API Key Required**: OpenAI API key mandatory for full functionality

### Resolution Steps
1. Update `requirements.txt` with missing packages
2. Fix import statements in [`main.py`](../../../backend/main.py:154)
3. Configure OpenAI API key in environment

## Performance Considerations

### Backend Optimizations
- **Lazy Loading**: AI dependencies loaded on-demand
- **Persistent Storage**: Vector embeddings cached between sessions
- **Async Operations**: Non-blocking request handling

### Frontend Optimizations
- **Code Splitting**: React Router with lazy loading support
- **Bundle Optimization**: Vite's tree-shaking and minification
- **Asset Optimization**: Tailwind CSS purging and compression

## Security Configuration

### Development Security
- **CORS**: Permissive settings for local development
- **File Validation**: Upload restrictions and size limits
- **Environment Isolation**: Separate dev/prod configurations

### Production Considerations
- **CORS Tightening**: Restrict origins for production
- **API Key Security**: Secure environment variable management
- **File Upload Security**: Enhanced validation and scanning