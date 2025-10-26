import axios, { AxiosError, type AxiosRequestConfig } from "axios";

/**
 * Backend base URL resolution:
 * - Uses VITE_API_URL if set and non-empty.
 * - Falls back to localhost:8000 (FastAPI default in this repo).
 */
const FALLBACK_BASE = "http://0.0.0.0:800";
const envBase = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
const baseURL = envBase && envBase.length ? envBase : FALLBACK_BASE;

/**
 * Axios instance (JSON default). Multipart overrides per request.
 */
export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json"
  }
});

/* -------------------------------- Types ----------------------------------- */

interface BackendErrorShape {
  detail?: string;
  error?: boolean;
  status_code?: number;
  message?: string;
  [k: string]: unknown;
}

interface ServerUploadResponse {
  document_id: string;
  chunks: number;
  bytes: number;
  filename?: string;
  processing_time_ms?: number;
  display_name: string;
}

export interface UploadResult {
  documentId: string;
  id: string; // backward alias
  chunks?: number;
  bytes?: number;
  filename?: string;
  displayName: string;
  processingTimeMs?: number;
  raw?: ServerUploadResponse;
}

export interface AskResponse {
  answer: string;
  document_id?: string | null;
  document_display_name?: string;
}

export interface DocumentInfo {
  document_id: string;
  filename?: string;
  file_size_bytes?: number;
  text_size_bytes: number;
  chunk_count: number;
  status: string;
  collection_name: string;
  processing_time_ms?: number;
  extracted_title?: string;
  display_name?: string;
  created_at: string;
  updated_at?: string;
}

export interface DocumentMetadata {
  id: string;
  displayName: string;
  filename?: string;
  extractedTitle?: string;
  userDisplayName?: string;
}

/* -------------------------- Error Helper Logic ---------------------------- */

/**
 * If user accidentally points to front-end dev server (e.g. :3000 or :5173),
 * provide clearer hint on Network Error.
 */
function deriveHelpfulNetworkMessage(err: unknown): string | null {
  if (!(err instanceof AxiosError)) return null;
  if (err.code === "ERR_NETWORK") {
    const target = api.defaults.baseURL || "";
    if (/:(3000|5173)\b/.test(target) && !/8000/.test(target)) {
      return `Network Error connecting to ${target}. Backend likely running on :8000. Set VITE_API_URL=http://localhost:8000 in .env before starting Vite.`;
    }
    return `Network Error connecting to ${target}. Is the FastAPI server running?`;
  }
  return null;
}

function extractErrorDetail(
  ax: AxiosError<BackendErrorShape>,
  fallback: string
) {
  return (
    deriveHelpfulNetworkMessage(ax) ||
    ax?.response?.data?.detail ||
    ax?.response?.data?.message ||
    ax.message ||
    fallback
  );
}

/* -------------------------- Normalization Helpers ------------------------- */

function normalizeUploadResponse(data: ServerUploadResponse): UploadResult {
  const documentId = data?.document_id ?? "";
  return {
    documentId,
    id: documentId,
    chunks: data?.chunks,
    bytes: data?.bytes,
    filename: data?.filename,
    displayName:
      data?.display_name ??
      data?.filename ??
      `Document ${documentId.slice(0, 8)}...`,
    processingTimeMs: data?.processing_time_ms,
    raw: data
  };
}

/* ------------------------------- API Calls -------------------------------- */

/**
 * File upload helper (PDF only backend). Maps backend fields (document_id) to camelCase.
 * Supports optional progress callback (0..1).
 * NOTE: Backend currently only supports PDF (application/pdf).
 */
export async function uploadFile(
  file: File,
  onProgress?: (fraction: number) => void
): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);

  try {
    const config: AxiosRequestConfig = {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (evt) => {
        if (evt.total) {
          onProgress?.(evt.loaded / evt.total);
        }
      }
    };
    const { data } = await api.post<ServerUploadResponse>(
      "/upload",
      form,
      config
    );
    return normalizeUploadResponse(data);
  } catch (err) {
    const ax = err as AxiosError<BackendErrorShape>;
    const detail = extractErrorDetail(ax, "Upload failed.");
    throw new Error(detail);
  }
}

/**
 * Ask a question.
 * Document context MUST be explicit; backend no longer falls back silently.
 */
export async function askQuestion(
  query: string,
  documentId: string | null = null
): Promise<{ answer: string; raw?: AskResponse }> {
  try {
    const payload: Record<string, unknown> = { query };
    if (documentId) {
      payload.document_id = documentId;
    }
    const { data } = await api.post<AskResponse>("/ask", payload);
    console.debug("[api.askQuestion] raw response:", data);
    return { answer: data.answer, raw: data };
  } catch (err) {
    const ax = err as AxiosError<BackendErrorShape>;
    const detail = extractErrorDetail(ax, "Query failed.");
    throw new Error(detail);
  }
}

/**
 * Fetch document information by ID.
 */
export async function fetchDocumentInfo(
  documentId: string
): Promise<DocumentInfo> {
  try {
    const { data } = await api.get<DocumentInfo>(`/documents/${documentId}`);
    return data;
  } catch (err) {
    const ax = err as AxiosError<BackendErrorShape>;
    const detail = extractErrorDetail(ax, "Failed to fetch document info.");
    throw new Error(detail);
  }
}

/**
 * Response from the rename document API.
 */
export interface RenameDocumentResponse {
  document_id: string;
  old_display_name: string;
  new_display_name: string;
  success: boolean;
}

/**
 * Rename document display name using the new PUT endpoint.
 */
export async function renameDocument(
  documentId: string,
  newDisplayName: string
): Promise<RenameDocumentResponse> {
  try {
    const { data } = await api.put<RenameDocumentResponse>(
      `/documents/${documentId}/rename`,
      {
        document_id: documentId,
        new_display_name: newDisplayName
      }
    );
    return data;
  } catch (err) {
    const ax = err as AxiosError<BackendErrorShape>;
    const detail = extractErrorDetail(ax, "Failed to rename document.");
    throw new Error(detail);
  }
}

/**
 * Fetch all uploaded documents.
 */
export async function fetchDocuments(): Promise<DocumentInfo[]> {
  try {
    const { data } = await api.get<DocumentInfo[]>("/documents/");
    return data;
  } catch (err) {
    const ax = err as AxiosError<BackendErrorShape>;
    const detail = extractErrorDetail(ax, "Failed to fetch documents.");
    throw new Error(detail);
  }
}

/**
 * Convert DocumentInfo to DocumentMetadata for frontend use.
 */
export function documentInfoToMetadata(
  docInfo: DocumentInfo
): DocumentMetadata {
  return {
    id: docInfo.document_id,
    displayName:
      docInfo.display_name ||
      docInfo.filename ||
      `Document ${docInfo.document_id.slice(0, 8)}...`,
    filename: docInfo.filename,
    userDisplayName: docInfo.display_name
  };
}
