# Development Guide

This document describes how to run and develop the SmartDocs AI backend with hot reload.

## Prerequisites

- Python 3.12+
- pip (user install is fine)
- An OpenAI API key (for /ask)

## Install dependencies

```bash
pip install -r requirements.txt
```

## Environment variables

Minimal required for full functionality:

- OPENAI_API_KEY=sk-...

Optionally place these in a .env (not yet auto-loaded; export in shell or use direnv).

## Running in development (auto-reload)

Option A (preferred for richer error output):

```bash
fastapi dev main.py --host 0.0.0.0 --port 8000
```

Option B (uvicorn directly):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Option C (Makefile helpers):

```bash
make dev          # fastapi dev main.py
make uvicorn      # uvicorn main:app --reload
make prod         # uvicorn main:app (no reload)
```

## Smoke test critical imports

```bash
make test-imports
```

## API Endpoints

- GET /health
- POST /upload (multipart/form-data, field: file)
- POST /ask (JSON: { "query": "...", "document_id": optional })

## Typical flow

1. Start server with hot reload.
2. Upload a PDF via /upload.
3. Note returned document_id.
4. Query with /ask providing document_id or rely on last uploaded.

## Vector store persistence

Collections are persisted under backend/vectorstores/<document_id>.

## Troubleshooting

- 503 on /ask: OPENAI_API_KEY not exported.
- Empty chunks: PDF had no extractable text.
- Import errors: Re-run pip install -r requirements.txt

## Production considerations

- Add version pinning in requirements.txt
- Deploy behind a process manager (systemd, Docker, etc.)
- Consider auth / rate limiting

## License

Internal prototype; add license when open sourced.