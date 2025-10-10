import { useCallback, useRef, useState } from "react";
import { uploadFile, type UploadResult } from "../api/api";

/**
 * Default accepted file extensions. (Frontend can visually allow more,
 * but backend currently enforces PDF; hook will validate that at upload time.)
 */
export const ACCEPT_DEFAULT =
  ".pdf,.txt,.md,.mdx,.csv,.json,.doc,.docx,.ppt,.pptx,.rtf";

/**
 * Internal pending upload meta state.
 */
export interface PendingMeta {
  progress: number; // 0..1
  start: number; // performance.now timestamp
  est: number; // (future use) estimated remaining ms
}

/**
 * Options accepted by useFileUpload.
 */
export interface UseFileUploadOptions {
  onUploaded?: (docId: string) => void;
  accept?: string;
  maxSizeMB?: number;
}

/**
 * Consolidated error shape for the hook.
 */
export interface UploadHookError {
  message: string;
  code?: string;
}

/**
 * Public API returned by useFileUpload.
 */
export interface UseFileUpload {
  // Config
  accept: string;
  maxSizeMB: number;

  // Refs
  inputRef: React.RefObject<HTMLInputElement | null>;

  // State
  file: File | null;
  pending: PendingMeta | null;
  successId: string | null;
  error: string;
  dragActive: boolean;

  // Derived
  progress: number;
  isUploading: boolean;
  isFinalizing: boolean;
  canUpload: boolean;

  // Actions
  reset: () => void;
  removeFile: () => void;
  openPicker: () => void;
  startUpload: () => Promise<void>;
  validateAndSetFile: (f: File | null) => void;

  // DOM Event Handlers (safe to spread)
  handleSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleDrag: (e: React.DragEvent) => void;
}

/**
 * useFileUpload
 *
 * Encapsulates:
 * - File selection & validation (size limit)
 * - Drag & drop management
 * - Upload invocation with progress simulation fallback
 * - Success / error state management
 * - Accessibility-ready handlers to be bound to a drop zone
 *
 * The simulated progress covers cases where browsers / network stack
 * fail to emit granular onUploadProgress events; it advances up to 90-98%
 * until real progress updates or completion occurs.
 */
export function useFileUpload(
  options: UseFileUploadOptions = {}
): UseFileUpload {
  const { onUploaded, accept = ACCEPT_DEFAULT, maxSizeMB = 20 } = options;

  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<PendingMeta | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const reset = useCallback(() => {
    setFile(null);
    setPending(null);
    setError("");
    setSuccessId(null);
  }, []);

  const validateAndSetFile = useCallback(
    (f: File | null) => {
      if (!f) return;
      const sizeMB = f.size / (1024 * 1024);
      if (sizeMB > maxSizeMB) {
        setError(
          `File too large (${sizeMB.toFixed(1)}MB). Max ${maxSizeMB}MB.`
        );
        setFile(null);
        return;
      }
      setError("");
      setSuccessId(null);
      setFile(f);
    },
    [maxSizeMB]
  );

  const handleSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      validateAndSetFile(e.target.files?.[0] || null);
    },
    [validateAndSetFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files?.length) {
        validateAndSetFile(e.dataTransfer.files[0]);
      }
    },
    [validateAndSetFile]
  );

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    if (e.type === "dragleave") setDragActive(false);
  }, []);

  const openPicker = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const removeFile = useCallback(() => {
    reset();
    if (inputRef.current) inputRef.current.value = "";
  }, [reset]);

  const startUpload = useCallback(async () => {
    if (!file || pending) return;
    setError("");
    setSuccessId(null);

    // Back-end currently PDF only.
    const isPdf =
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setError(
        `Only PDF files are supported by backend (selected: ${
          file.type || file.name
        }).`
      );
      return;
    }

    setPending({ progress: 0, start: performance.now(), est: 0 });

    let gotProgress = false;
    const simulateProgress = () => {
      setPending((p) => {
        if (!p || gotProgress) return p;
        const next = Math.min(0.9, p.progress + 0.015 + Math.random() * 0.02);
        return { ...p, progress: next };
      });
      if (!gotProgress) {
        setTimeout(simulateProgress, 160);
      }
    };
    setTimeout(simulateProgress, 300);

    try {
      const { id }: UploadResult = await uploadFile(file, (fraction) => {
        gotProgress = true;
        setPending((p) =>
          p ? { ...p, progress: Math.min(0.98, fraction) } : p
        );
      });

      // finalize bar
      setPending((p) => (p ? { ...p, progress: 1 } : p));
      setTimeout(() => {
        setSuccessId(id);
        onUploaded?.(id);
      }, 120);
    } catch (err) {
      console.error("Upload failed", err);
      const detail = (err as Error)?.message || "Upload failed. Try again.";
      setError(detail);
      setPending(null);
    }
  }, [file, pending, onUploaded]);

  const progress = pending?.progress ?? (file ? 0.08 : 0);
  const isUploading = !!pending && pending.progress < 1;
  const isFinalizing = !!pending && pending.progress === 1;
  const canUpload = !!file && !pending;

  return {
    accept,
    maxSizeMB,
    inputRef,
    file,
    pending,
    successId,
    error,
    dragActive,
    progress,
    isUploading,
    isFinalizing,
    canUpload,
    reset,
    removeFile,
    openPicker,
    startUpload,
    validateAndSetFile,
    handleSelect,
    handleDrop,
    handleDrag
  };
}
