# Convenience Makefile for FastAPI development
SHELL := /bin/bash

APP := main.py
MODULE := main:app
HOST ?= 0.0.0.0
PORT ?= 8000

.PHONY: dev
dev:
	@echo "Starting FastAPI dev server (auto-reload, rich errors)..."
	fastapi dev $(APP) --host $(HOST) --port $(PORT)

.PHONY: uvicorn
uvicorn:
	@echo "Starting Uvicorn in reload mode..."
	uvicorn $(MODULE) --host $(HOST) --port $(PORT) --reload --log-level info

.PHONY: prod
prod:
	@echo "Starting Uvicorn (production style)..."
	uvicorn $(MODULE) --host $(HOST) --port $(PORT) --log-level info

.PHONY: test-imports
test-imports:
	@echo "Verifying critical runtime imports..."
	python -c "from fastapi import FastAPI; from langchain_openai import OpenAIEmbeddings; from langchain_chroma import Chroma; print('Imports OK')"

.PHONY: help
help:
	@echo "Targets:"
	@echo "  make dev         - FastAPI dev server with auto-reload"
	@echo "  make uvicorn     - Uvicorn reload server"
	@echo "  make prod        - Production style run (no reload)"
	@echo "  make test-imports- Smoke test key imports"
	@echo ""
	@echo "Override HOST / PORT: make dev PORT=9000"