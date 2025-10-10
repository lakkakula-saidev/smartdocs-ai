import axios, { AxiosError, type AxiosRequestConfig } from "axios";

/**
 * Backend base URL resolution:
 * - Uses VITE_API_URL if set and non-empty.
 * - Falls back to localhost:8000 (FastAPI default in this repo).
 */
const FALLBACK_BASE = "http://0.0.0.0:8000";
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
}

export interface UploadResult {
  documentId: string;
  id: string; // backward alias
  chunks?: number;
  bytes?: number;
  raw?: ServerUploadResponse;
}

export interface AskResponse {
  answer: string;
  document_id?: string | null;
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
 * Ask a question (document context currently implicit on backend last upload).
 * Returns only { answer } to match existing ChatBox usage, but preserves raw if needed later.
 */
export async function askQuestion(
  query: string
): Promise<{ answer: string; raw?: AskResponse }> {
  try {
    const { data } = await api.post<AskResponse>("/ask", { query });
    // Use console.debug to allow filtered inspection without polluting production logs.
    console.debug("[api.askQuestion] raw response:", data);
    return { answer: data.answer, raw: data };
  } catch (err) {
    const ax = err as AxiosError<BackendErrorShape>;
    const detail = extractErrorDetail(ax, "Query failed.");
    throw new Error(detail);
  }
}
