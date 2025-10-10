import { useCallback, useRef, useState, useEffect } from "react";
import { uploadFile, type UploadResult } from "../api/api";

/**
 * ACCEPT_DEFAULT
 * Backend is currently PDF-only. Exposing the prop for future compatibility,
 * but any non-PDF file will be rejected during validation.
 */
export const ACCEPT_DEFAULT = ".pdf";

/* -------------------------------------------------------------------------- */
/* Types                                                                      */
/* -------------------------------------------------------------------------- */

/**
 * Upload progress state (internal). Kept minimal; estimation removed until implemented.
 */
export interface PendingMeta {
  progress: number; // 0..1
}

export interface UseFileUploadOptions {
  /**
   * Called after successful upload.
   * @param docId backend-assigned document id
   * @param meta optional extra metadata (e.g. title)
   */
  onUploaded?: (docId: string, meta?: { title?: string }) => void;
  accept?: string;
  maxSizeMB?: number;
}

/**
 * Public hook contract returned by useFileUpload.
 */
export interface UseFileUpload {
  accept: string;
  maxSizeMB: number;

  inputRef: React.RefObject<HTMLInputElement | null>;

  file: File | null;
  pending: PendingMeta | null;
  successId: string | null;
  error: string;
  dragActive: boolean;

  progress: number;
  isUploading: boolean;
  isFinalizing: boolean;
  canUpload: boolean;

  reset: () => void;
  removeFile: () => void;
  openPicker: () => void;
  startUpload: () => Promise<void>;
  abortUpload: () => void;
  validateAndSetFile: (f: File | null) => void;

  handleSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleDrag: (e: React.DragEvent) => void;
}

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const PDF_ONLY_MSG = "Only PDF files are currently supported.";

/* -------------------------------------------------------------------------- */
/* Hook Implementation                                                        */
/* -------------------------------------------------------------------------- */

/**
 * useFileUpload
 *
 * Responsibilities:
 * - File selection & early validation (size + PDF restriction)
 * - Drag / drop state management
 * - Upload initiation with simulated progress fallback
 * - Success & error state handling
 * - Abort (logical) to prevent state updates after user cancels
 *
 * NOTE: Network abort of the underlying request is not implemented yet because
 * uploadFile currently does not accept a signal. A future enhancement can pass
 * an AbortSignal into uploadFile / axios config. For now, abortUpload prevents
 * UI state churn after a user cancels.
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

  // Track timeouts for simulated progress to ensure cleanup
  const timeoutsRef = useRef<number[]>([]);
  // Logical abort flag (prevents late setState after user aborts)
  const abortedRef = useRef(false);

  const reset = useCallback(() => {
    abortedRef.current = false;
    setFile(null);
    setPending(null);
    setError("");
    setSuccessId(null);
  }, []);

  useEffect(
    () => () => {
      timeoutsRef.current.forEach((id) => clearTimeout(id));
      timeoutsRef.current = [];
      abortedRef.current = true;
    },
    []
  );

  const clearSimTimers = () => {
    timeoutsRef.current.forEach((id) => clearTimeout(id));
    timeoutsRef.current = [];
  };

  const validateAndSetFile = useCallback(
    (f: File | null) => {
      if (!f) return;
      // Size check
      const sizeMB = f.size / (1024 * 1024);
      if (sizeMB > maxSizeMB) {
        setError(
          `File too large (${sizeMB.toFixed(1)}MB). Max ${maxSizeMB}MB.`
        );
        setFile(null);
        return;
      }
      // PDF only (backend constraint)
      const isPdf =
        f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf");
      if (!isPdf) {
        setError(`${PDF_ONLY_MSG} (selected: ${f.type || f.name})`);
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

  const abortUpload = useCallback(() => {
    abortedRef.current = true;
    clearSimTimers();
    setPending(null);
  }, []);

  const startUpload = useCallback(async () => {
    if (!file || pending) return;
    abortedRef.current = false;
    setError("");
    setSuccessId(null);

    // File already validated during selection
    setPending({ progress: 0 });

    let gotProgress = false;

    const simulateProgress = () => {
      if (abortedRef.current) return;
      setPending((p) => {
        if (!p || gotProgress) return p;
        const increment = 0.015 + Math.random() * 0.02;
        const next = Math.min(0.9, p.progress + increment);
        return { ...p, progress: next };
      });
      if (!gotProgress && !abortedRef.current) {
        const id = window.setTimeout(simulateProgress, 160);
        timeoutsRef.current.push(id);
      }
    };

    // Give real network progress callbacks a moment first
    const initialId = window.setTimeout(simulateProgress, 300);
    timeoutsRef.current.push(initialId);

    try {
      const { id, title: backendTitle }: UploadResult = await uploadFile(
        file,
        (fraction) => {
          if (abortedRef.current) return;
          gotProgress = true;
          // Real progress arrived -> clear simulated timers
          clearSimTimers();
          setPending((p) =>
            p ? { ...p, progress: Math.min(0.98, fraction) } : p
          );
        }
      );

      if (abortedRef.current) return;
      // Finalize bar then mark success & clear pending for stable post-success state
      setPending((p) => (p ? { ...p, progress: 1 } : p));
      const finalizeId = window.setTimeout(() => {
        if (abortedRef.current) return;
        setSuccessId(id);
        // Prefer backend-provided title; fallback to filename stem.
        let derived: string | undefined;
        if (file) {
          derived =
            file.name
              .replace(/\.[^.]+$/, "")
              .slice(0, 120)
              .trim() || file.name;
        }
        const finalTitle = backendTitle || derived;
        try {
          if (finalTitle) {
            localStorage.setItem(`docTitle:${id}`, finalTitle);
          }
        } catch {
          /* non-fatal storage failure */
        }
        onUploaded?.(id, { title: finalTitle });
        setPending(null); // not "finalizing" anymore; success state stable
      }, 120);
      timeoutsRef.current.push(finalizeId);
    } catch (err) {
      if (abortedRef.current) return;
      console.error("Upload failed", err);
      const detail = (err as Error)?.message || "Upload failed. Try again.";
      setError(detail);
      setPending(null);
    }
  }, [file, pending, onUploaded]);

  // Derived
  const progress = pending?.progress ?? 0;
  const isUploading = !!pending && pending.progress < 1;
  const isFinalizing = false; // We clear pending once success is set, so no stuck finalizing state.
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
    abortUpload,
    validateAndSetFile,
    handleSelect,
    handleDrop,
    handleDrag
  };
}
