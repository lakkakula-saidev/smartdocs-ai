# SmartDocs AI

Minimal full‑stack Retrieval Augmented Generation (RAG) demo.
Upload a PDF, get contextual answers via chat.

## Stack (Essentials Only)
Backend: FastAPI + LangChain (OpenAI embeddings + Chroma) in [`backend/app/main.py`](backend/app/main.py:1)  
Frontend: React 19 + TypeScript + Vite in [`frontend/smartdocs-ui/src/main.tsx`](frontend/smartdocs-ui/src/main.tsx:1)  
Vector Store: Chroma (persistent folders under `backend/vectorstores/`)

## Quick Start

Clone & enter:
```bash
git clone <repo-url> smartdocs-ai
cd smartdocs-ai
```

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...   # or place in .env
fastapi dev main.py
```

### Frontend
```bash
cd frontend/smartdocs-ui
npm install
npm run dev
```

Open UI: http://localhost:5173  
API Docs: http://localhost:8000/docs

## Environment Variables (Backend)
Required:
- OPENAI_API_KEY

Optional:
- OPENAI_API_BASE (Azure / proxy)
- PORT (override default dev port)

Frontend optional `.env`:
```
VITE_API_BASE_URL=http://localhost:8000
```

## Typical Flow
1. Upload PDF (Home) via [`UploadDocument.tsx`](frontend/smartdocs-ui/src/components/UploadDocument.tsx:1)  
2. Backend extracts text (`pypdf`), chunks, embeds (OpenAI), stores in Chroma.  
3. Chat page (`Chat.tsx`) sends question with document id.  
4. Service retrieves top‑k chunks, calls model, returns markdown enhanced answer rendered by [`MessageBubble.tsx`](frontend/smartdocs-ui/src/components/MessageBubble.tsx:1).  

## Minimal Architecture
```
Frontend (React) → FastAPI Routes → Services → LangChain:
 PDF → extract → chunk → embed → store (Chroma)
 Question → retrieve (k=4) → LLM → answer
```

Core backend entry: [`backend/main.py`](backend/main.py:1) (delegates to app).  
Routes: [`backend/app/routes/upload.py`](backend/app/routes/upload.py:1), [`backend/app/routes/chat.py`](backend/app/routes/chat.py:1), [`backend/app/routes/health.py`](backend/app/routes/health.py:1)

## Clean Repo Philosophy
This repository intentionally removes:
- Large narrative docs
- Sample template assets (Vite boilerplate)
- Unused tests & prototype scripts

Retained files focus on executable code and minimal instructions.

Note: Automated tests were intentionally removed during cleanup. Reintroduce a minimal smoke/integration test suite in a future iteration to validate ingestion and QA flow.

## Troubleshooting (Condensed)
| Symptom | Fix |
|--------|-----|
| ImportError langchain-openai/chroma | Confirm packages in `requirements.txt` |
| 401 / OpenAI auth error | Set OPENAI_API_KEY |
| Empty answers | PDF may have no extractable text (scanned images) |
| No persistence | Ensure `backend/vectorstores/` writable |

Health check: `curl http://localhost:8000/health`

## Roadmap (Short List)
- Persist document registry (DB)
- Auth / multi‑tenant
- OCR for image PDFs
- Background ingestion
- Tests

## License
Add a LICENSE file (MIT recommended) before distribution.

## Contribution
Use short branches: `kilocode/<change>` and keep PRs minimal.

---
Slim README produced as part of repository cleanup initiative.