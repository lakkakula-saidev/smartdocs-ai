# SmartDocs AI

> Intelligent document upload and conversational Q&A over your PDFs using Retrieval-Augmented Generation (RAG).

![Status](https://img.shields.io/badge/status-prototype-blue) ![Frontend](https://img.shields.io/badge/frontend-React%2019-informational) ![Backend](https://img.shields.io/badge/backend-FastAPI-green) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [Running the App](#running-the-app)
- [Usage Examples](#usage-examples)
- [Development Workflow](#development-workflow)
- [Known Issues & Troubleshooting](#known-issues--troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Project Overview
SmartDocs AI enables natural language interaction with PDF documents. Users upload a PDF, the system extracts and chunks the text, generates vector embeddings, and serves retrieval-augmented answers to questions through a chat interface.

Core goals:
- Reduce time-to-insight for large / technical documents
- Provide a reference full-stack AI application
- Demonstrate a pragmatic RAG pipeline (OpenAI + LangChain + ChromaDB)

## Features
- PDF upload with validation and progress feedback via [`UploadDocument.tsx`](frontend/smartdocs-ui/src/components/UploadDocument.tsx:1)
- Automatic text extraction (`pypdf`) and semantic chunking (`RecursiveCharacterTextSplitter`)
- Embedding generation (OpenAI) and persistent vector storage (ChromaDB)
- Retrieval-Augmented Generation (RAG) answering via [`main.py`](backend/main.py)
- Clean chat UI with markdown + GFM rendering in [`MessageBubble.tsx`](frontend/smartdocs-ui/src/components/MessageBubble.tsx:1)
- Error handling with structured responses
- Dark themed, Tailwind-driven UI
- Lazy backend loading of AI dependencies for faster cold starts

## Architecture & Tech Stack
High-level architecture (see detailed description in [`architecture.md`](.kilocode/rules/memory-bank/architecture.md:1)):

```
React SPA ⇄ FastAPI API ⇄ LangChain (OpenAI Models + ChromaDB)
```

Backend:
- FastAPI, LangChain (`langchain`, `langchain-openai`, `langchain-chroma`)
- OpenAI GPT-4o-mini (chat) + embeddings
- ChromaDB persistent vector store
- PDF processing: `pypdf`
- Token utilities: `tiktoken`

Frontend:
- React 19 + TypeScript + Vite
- Tailwind CSS
- Axios HTTP client in [`api.ts`](frontend/smartdocs-ui/src/api/api.ts:1)
- React Markdown + remark-gfm for answer rendering

For deeper stack info see [`tech.md`](.kilocode/rules/memory-bank/tech.md:1).

## Project Structure
```
.
├── backend
│   ├── main.py
│   ├── requirements.txt
│   ├── Makefile
│   └── vectorstores/               # Persistent Chroma collections
├── frontend
│   └── smartdocs-ui
│       ├── src
│       │   ├── api/api.ts
│       │   ├── components/
│       │   │   ├── UploadDocument.tsx
│       │   │   ├── ChatBox.tsx
│       │   │   └── MessageBubble.tsx
│       │   ├── pages/
│       │   │   ├── Home.tsx
│       │   │   └── Chat.tsx
│       │   └── main.tsx
│       ├── index.html
│       └── package.json
└── .kilocode/rules/memory-bank     # Project knowledge base (docs)
```

## Prerequisites
- Python 3.12+
- Node.js 18+
- OpenAI API key
- (Optional) Make (for backend shortcuts)

## Installation
Clone repository:
```bash
git clone https://github.com/your-org/smartdocs-ai.git
cd smartdocs-ai
```

Install backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

Install frontend:
```bash
cd frontend/smartdocs-ui
npm install   # or yarn / pnpm install
cd ../..
```

## Environment Configuration
Create a `.env` file in `backend/` (or export directly) with:
```bash
OPENAI_API_KEY=sk-...yourkey...
```
Optional variables:
- `OPENAI_API_BASE` (for Azure/OpenAI compatible endpoints)
- `PORT` (override default FastAPI dev port)

Ensure the frontend knows the backend base URL. By default Axios client in [`api.ts`](frontend/smartdocs-ui/src/api/api.ts:1) derives it from `window.location` or `VITE_API_BASE_URL`. You can set:
```bash
# frontend/smartdocs-ui/.env.local
VITE_API_BASE_URL=http://localhost:8000
```

## Running the App
Start backend (from project root):
```bash
cd backend
make dev  # or: fastapi dev main.py
```

Start frontend (in a second terminal):
```bash
cd frontend/smartdocs-ui
npm run dev
```

Access UI: http://localhost:5173  
API docs: http://localhost:8000/docs

## Usage Examples
1. Upload a PDF via UI (Home page).  
2. After processing completes you are redirected (or navigate) to Chat page with a document ID in state / URL.
3. Ask natural language questions; system retrieves top-k (k=4) relevant chunks then generates answer.

cURL examples:

Health check:
```bash
curl http://localhost:8000/health
```

Upload (PDF):
```bash
curl -X POST -F "file=@example.pdf" http://localhost:8000/upload
```

Ask question:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"document_id": "YOUR_DOC_ID", "question": "Summarize section 2."}'
```

## Development Workflow
- Edit backend logic in [`main.py`](backend/main.py)
- Frontend components under `frontend/smartdocs-ui/src/components/`
- Maintain architecture docs in `.kilocode/rules/memory-bank/`
- Use feature branches (`git checkout -b feature/xyz`)
- Preferred commit style: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- Run lightweight manual tests via UI; (Add automated tests TBD)

### RAG Pipeline Summary
1. Extract PDF text
2. Chunk (size≈1000, overlap≈150)
3. Embed with OpenAI
4. Store in Chroma (`backend/vectorstores/`)
5. Retrieve top-k
6. Generate answer (GPT-4o-mini) and enhance markdown

## Known Issues & Troubleshooting
| Issue | Symptom | Resolution |
|-------|---------|------------|
| Missing `langchain-openai` / `langchain-chroma` | ImportError at startup | Add to `backend/requirements.txt` then `pip install -r requirements.txt` |
| Wrong Chroma import path | ModuleNotFoundError `langchain_community.vectorstores` | Update to `langchain_chroma` |
| No OpenAI key | 401 / runtime error | Set `OPENAI_API_KEY` in environment |
| Empty answers | Retrieval returns no chunks | Verify PDF extracted text (some PDFs may be image-only) |
| Vector store not persisting | Answers lost after restart | Ensure `backend/vectorstores/` writable; not cleared |

Logs & Debug:
- Check FastAPI logs in backend terminal
- Verify embeddings directory creation under `backend/vectorstores/`
- Use `/health` to inspect registered documents

## Contributing
1. Fork repository & create branch (`kilocode/your-feature`)
2. Ensure changes align with architecture in [`architecture.md`](.kilocode/rules/memory-bank/architecture.md:1)
3. Update docs / comments if behavior changes
4. Open PR with clear description & screenshots (if UI)
5. Respond to review feedback promptly

### Code Style
- Python: PEP8 + type hints
- Frontend: ESLint + TypeScript strictness
- Keep components small & focused

## License
MIT License (intended). Add a root `LICENSE` file before production release. Until then, contributions are assumed under MIT terms.

## Roadmap (High-Level)
- Persist document registry (DB)
- Authentication & multi-tenancy
- Async/background processing queue
- Improved PDF OCR for image-based docs
- Test suite (unit + integration)

## Acknowledgements
- OpenAI, LangChain, ChromaDB communities
- FastAPI & React ecosystems

---
For architecture details read [`architecture.md`](.kilocode/rules/memory-bank/architecture.md:1) and tech decisions in [`tech.md`](.kilocode/rules/memory-bank/tech.md:1).