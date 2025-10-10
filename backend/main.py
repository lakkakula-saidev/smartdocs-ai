import os
import uuid
import tempfile
import shutil
import re
from typing import Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, status
try:
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
except ImportError as e:
    raise RuntimeError(
        "FastAPI dependencies missing. Install with: pip install fastapi uvicorn python-multipart"
    ) from e

# Lazy imports (LangChain / OpenAI / pypdf) done inside functions to reduce cold start cost if desired

# Load environment variables from .env if present (so OPENAI_API_KEY works without manual export)
# Added diagnostic logging to investigate missing OPENAI_API_KEY reports.
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        print(f"[env] Located .env file at: {dotenv_path}")
    else:
        print("[env] No .env file discovered via find_dotenv()")
    loaded = load_dotenv(dotenv_path or None)
    print(f"[env] load_dotenv loaded={loaded}")
except Exception as e:
    # Non-fatal; continue with existing environment
    print(f"[env] dotenv load error: {e}")
    pass
# Immediate post-load inspection (masked)
_raw_key = os.getenv("OPENAI_API_KEY", "")
if _raw_key:
    print(f"[env] OPENAI_API_KEY present (len={len(_raw_key)} prefix={_raw_key[:7]}*** masked)")
else:
    print("[env] OPENAI_API_KEY still empty right after load_dotenv()")

# ---- Environment / Config ----
# Initial load (may be empty if .env added after startup)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

def require_openai_api_key() -> str:
    """
    Return a fresh OpenAI API key each call.
    Reloads .env so adding the key after the server starts works without a restart.
    Raises 503 if still missing.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:
        pass
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY not configured."
        )
    return key

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set at startup. Add it to .env and reuse endpoints without restart.")

# ---- FastAPI App ----
app = FastAPI(
    title="SmartDocs AI Backend",
    version="0.1.0",
    description="PDF ingestion and retrieval QA service using FastAPI + LangChain + ChromaDB."
)

# ---- Diagnostic Endpoint (non-sensitive) ----
@app.get("/debug/env")
def debug_env():
    """
    Returns masked diagnostics about the OPENAI_API_KEY loading state.
    DO NOT expose this endpoint publicly in production.
    """
    key = os.getenv("OPENAI_API_KEY", "")
    return {
        "present": bool(key),
        "length": len(key),
        "prefix": key[:7] + ("***" if key else ""),
        "cwd": os.getcwd(),
        "vectorstores_loaded": len(VECTOR_STORES),
    }

# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- In-Memory Registry ----
# Map document_id -> { 'vectorstore': Chroma, 'collection_name': str }
VECTOR_STORES: Dict[str, Dict[str, Any]] = {}
LAST_DOC_ID: Optional[str] = None


# ---- Utility Functions ----
def extract_pdf_text(upload_path: str) -> str:
    """Extract raw text from a PDF using pypdf (lazy import)."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="pypdf not installed. Install with: pip install pypdf"
        ) from e
    try:
        reader = PdfReader(upload_path)
        pages: list[str] = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            pages.append(txt)
        text = "\n".join(pages).strip()
        if not text:
            raise ValueError("No extractable text")
        return text
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read PDF: {e}"
        )


def build_and_store_embeddings(document_id: str, text: str):
    """Split, embed, and store text in a new Chroma collection for this document."""
    # Defer API key validation to runtime (supports late injection)
    try:
        # Lazy import heavy deps
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        # Handle possible variations in package names (Pylance may flag 'langchain_openai' if not installed)
        try:
            from langchain_openai import OpenAIEmbeddings  # modern package 'langchain-openai'
        except ImportError:
            try:
                from langchain.embeddings.openai import OpenAIEmbeddings  # legacy fallback
            except ImportError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OpenAIEmbeddings not available. Install dependency: pip install langchain-openai"
                ) from e
        # Updated import path for Chroma (separate package 'langchain-chroma'); provide legacy fallback
        try:
            from langchain_chroma import Chroma
        except ImportError:
            try:
                from langchain_community.vectorstores import Chroma  # legacy path
            except ImportError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Chroma vectorstore not available. Install dependency: pip install langchain-chroma"
                ) from e

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", " ", ""]
        )
        docs = splitter.create_documents([text])

        api_key = require_openai_api_key()
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)

        # Use per-document persistent directory (optional persistence)
        persist_dir = os.path.join("backend", "vectorstores", document_id)
        os.makedirs(persist_dir, exist_ok=True)

        vectorstore = Chroma.from_documents(
            docs,
            embedding=embeddings,
            collection_name=f"doc_{document_id}",
            persist_directory=persist_dir,
        )
        # NOTE: Newer langchain-chroma versions may auto-persist when a persist_directory
        # is supplied and do not expose a .persist() method. Guard to avoid attribute error.
        if hasattr(vectorstore, "persist"):
            vectorstore.persist()

        VECTOR_STORES[document_id] = {
            "vectorstore": vectorstore,
            "collection_name": f"doc_{document_id}",
            "persist_directory": persist_dir
        }
        global LAST_DOC_ID
        LAST_DOC_ID = document_id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding pipeline failed: {e}"
        )


def get_vectorstore(document_id: Optional[str]) -> Any:
    """Retrieve a vector store by explicit id or fallback to last uploaded."""
    if document_id and document_id in VECTOR_STORES:
        return VECTOR_STORES[document_id]["vectorstore"]
    if document_id and document_id not in VECTOR_STORES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document ID not found."
        )
    # fallback
    if LAST_DOC_ID and LAST_DOC_ID in VECTOR_STORES:
        return VECTOR_STORES[LAST_DOC_ID]["vectorstore"]
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No documents have been uploaded yet."
    )


def run_retrieval_qa(query: str, document_id: Optional[str] = None) -> str:
    # API key validated lazily below (supports adding key after startup)
    try:
        from langchain.chains import RetrievalQA
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            try:
                from langchain.chat_models import ChatOpenAI  # legacy fallback
            except ImportError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="ChatOpenAI not available. Install dependency: pip install langchain-openai"
                ) from e
        vectorstore = get_vectorstore(document_id)
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 4}
        )
        api_key = require_openai_api_key()
        llm = ChatOpenAI(
            temperature=0.1,
            model_name="gpt-4o-mini",
            openai_api_key=api_key
        )
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            return_source_documents=False
        )
        result = chain.invoke({"query": query})
        # LangChain's RetrievalQA returns dict; answer under 'result' or 'output_text' depending on version
        answer = result.get("result") or result.get("output_text") or ""
        return answer.strip()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval QA failed: {e}"
        )


# ---- Markdown Enhancement Utilities ----
LIST_TITLE_PATTERN = re.compile(r'^(\s*(?:\d+\.|[-*])\s+)([A-Z][^:\n]{2,80}?)(:)(\s+)')
QUOTED_PATTERN = re.compile(r'"([^"\n]{3,120})"')
LIST_SENTENCE_PATTERN = re.compile(r'^(\s*(?:\d+\.|[-*])\s+)([A-Za-z][^\n]*)$')

AUX_OR_VERB = {
    "is", "are", "was", "were", "be", "being", "been",
    "has", "have", "had",
    "can", "could", "may", "might", "must",
    "shall", "should", "will", "would",
    "does", "do", "did"
}


def _bold_list_titles(line: str) -> str:
    def repl(m: re.Match) -> str:
        prefix, title, colon, space = m.groups()
        if '**' in title:
            return m.group(0)
        return f'{prefix}**{title.strip()}**{colon}{space}'
    return LIST_TITLE_PATTERN.sub(repl, line)


def _bold_first_quoted_phrase(text: str) -> str:
    """
    Bold the first quoted phrase if it looks like a document title (no existing ** inside).
    """
    def repl(m: re.Match) -> str:
        phrase = m.group(1)
        if '**' in phrase:
            return m.group(0)
        # Keep surrounding quotes out of bold for clarity:
        return f'"**{phrase.strip()}**"'
    return QUOTED_PATTERN.sub(repl, text, count=1)


def _bold_initial_noun_phrase(line: str) -> str:
    """
    For enumerated list sentences WITHOUT a colon, bold a concise leading noun phrase.
    Heuristic:
      - Stop before first auxiliary/verb token (AUX_OR_VERB) or punctuation.
      - Limit to max 6 tokens, min 2 tokens.
      - Skip if line already contains **.
    """
    if '**' in line:
        return line
    m = LIST_SENTENCE_PATTERN.match(line)
    if not m:
        return line
    prefix, rest = m.groups()
    if ':' in rest:  # already handled by title heuristic
        return line
    tokens = rest.split()
    if len(tokens) < 2:
        return line
    end_idx = 0
    for i, tok in enumerate(tokens):
        raw = tok.rstrip('.,;:!?')
        lower = raw.lower()
        if i > 0 and (lower in AUX_OR_VERB or raw.endswith(':')):
            break
        if i == 5:  # cap at 6 tokens (0..5)
            end_idx = i
            break
        end_idx = i
        if lower in AUX_OR_VERB:
            break
    phrase_tokens = tokens[: end_idx + 1]
    # Avoid bolding pronoun-only phrase
    if len(phrase_tokens) == 1 and phrase_tokens[0].lower() in {"it", "there", "this", "that"}:
        return line
    phrase = " ".join(phrase_tokens)
    # Reconstruct
    remainder = " ".join(tokens[end_idx + 1 :])
    if not remainder:
        return line
    return f"{prefix}**{phrase}** {remainder}"


def enhance_markdown(answer: str) -> str:
    """
    Add lightweight markdown emphasis to improve readability when the LLM
    output does not include formatting on its own.

    Heuristics (in order):
      1. Bold list item 'title' segments before first colon.
      2. Bold first quoted phrase (likely a document or section title).
      3. For plain enumerated sentences, bold an initial noun phrase.
    """
    lines = answer.splitlines()
    # 1: title segments with colon
    lines = [_bold_list_titles(l) for l in lines]
    # 3: noun phrase for enumerated sentences lacking colon
    lines = [_bold_initial_noun_phrase(l) for l in lines]
    enhanced = "\n".join(lines)
    # 2: quoted phrase after structural per-line adjustments
    enhanced = _bold_first_quoted_phrase(enhanced)
    return enhanced


# ---- Schemas ----
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(..., description="Natural language question to ask.")
    document_id: Optional[str] = Field(
        None,
        description="Optional document id to scope retrieval. If omitted, last uploaded is used."
    )


class AskResponse(BaseModel):
    answer: str
    document_id: Optional[str] = None


class UploadResponse(BaseModel):
    document_id: str
    chunks: int
    bytes: int


class HealthResponse(BaseModel):
    status: str
    has_documents: bool
    last_document_id: Optional[str]


# ---- Endpoints ----
@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        has_documents=bool(VECTOR_STORES),
        last_document_id=LAST_DOC_ID
    )


@app.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type not in {"application/pdf"} and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )
    temp_dir = tempfile.mkdtemp(prefix="upload_pdf_")
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as f:
            data = await file.read()
            f.write(data)
        text = extract_pdf_text(temp_path)
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extractable text found in PDF."
            )
        document_id = uuid.uuid4().hex
        build_and_store_embeddings(document_id, text)
        # Count chunks from stored vectorstore (metadata not always directly accessible; approximate)
        chunks = len(VECTOR_STORES[document_id]["vectorstore"]._collection.get()["ids"])
        return UploadResponse(
            document_id=document_id,
            chunks=chunks,
            bytes=len(text.encode("utf-8"))
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    if not req.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must not be empty."
        )
    raw_answer = run_retrieval_qa(req.query, req.document_id)
    enhanced = enhance_markdown(raw_answer)
    return AskResponse(answer=enhanced, document_id=req.document_id or LAST_DOC_ID)


# ---- Exception Handlers (Optional JSON normalization) ----
@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )


# ---- Dev Convenience ----
# Dev run commands:
#   fastapi dev main.py        # auto-reload with rich tracebacks
#   uvicorn main:app --reload  # alternative
# Production example:
#   uvicorn main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )