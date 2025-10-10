import { useCallback, useRef, useState } from "react";
import { uploadFile } from "../api/api";

interface Props {
  onUploaded: (docId: string) => void;
  accept?: string;
  maxSizeMB?: number;
}

interface PendingMeta {
  progress: number;
  start: number;
  est: number;
}

const ACCEPT_DEFAULT =
  ".pdf,.txt,.md,.mdx,.csv,.json,.doc,.docx,.ppt,.pptx,.rtf";

export function UploadDocument({
  onUploaded,
  accept = ACCEPT_DEFAULT,
  maxSizeMB = 20
}: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string>("");
  const [pending, setPending] = useState<PendingMeta | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const reset = () => {
    setFile(null);
    setPending(null);
    setError("");
    setSuccessId(null);
  };

  const validateFile = (f: File | null) => {
    if (!f) return;
    const sizeMB = f.size / (1024 * 1024);
    if (sizeMB > maxSizeMB) {
      setError(`File too large (${sizeMB.toFixed(1)}MB). Max ${maxSizeMB}MB.`);
      setFile(null);
      return;
    }
    setError("");
    setSuccessId(null);
    setFile(f);
  };

  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    validateFile(e.target.files?.[0] || null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.length) {
      validateFile(e.dataTransfer.files[0]);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    if (e.type === "dragleave") setDragActive(false);
  };

  const startUpload = async () => {
    if (!file || pending) return;
    setError("");
    setSuccessId(null);

    // Backend only supports PDF
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
    // Fallback simulated progress if browser / network stack does not emit progress events
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
    setTimeout(simulateProgress, 300); // give real progress a chance first

    try {
      const { id } = await uploadFile(file, (fraction) => {
        gotProgress = true;
        setPending((p) =>
          p ? { ...p, progress: Math.min(0.98, fraction) } : p
        );
      });
      // finalize bar
      setPending((p) => (p ? { ...p, progress: 1 } : p));
      setTimeout(() => {
        setSuccessId(id);
        onUploaded(id);
      }, 120);
    } catch (err) {
      console.error("Upload failed", err);
      const detail = (err as Error)?.message || "Upload failed. Try again.";
      setError(detail);
      setPending(null);
    }
  };

  const openPicker = () => inputRef.current?.click();

  const removeFile = useCallback(() => {
    reset();
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  return (
    <div className="space-y-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          startUpload();
        }}
        className="contents"
      >
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          className={[
            "relative group rounded-2xl border transition-colors overflow-hidden",
            "bg-neutral-900/50 backdrop-blur-sm border-white/5",
            dragActive ? "border-brand-400/60" : "hover:border-brand-500/30"
          ].join(" ")}
        >
          <div
            className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition
              bg-[radial-gradient(circle_at_30%_20%,rgba(43,165,255,0.10),transparent_60%)]"
          />
          <div className="relative p-6 md:p-8 space-y-6">
            <div className="space-y-3">
              <h2 className="text-lg font-semibold tracking-tight flex items-center gap-2">
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-brand-600/20 text-brand-300 text-xs font-bold ring-1 ring-inset ring-brand-500/30">
                  1
                </span>
                Upload a Document
              </h2>
              <p className="text-[0.7rem] md:text-xs text-neutral-400 leading-relaxed max-w-prose">
                Drag and drop a file or browse from your device. Once uploaded,
                you can open the Chat to ask contextual questions.
              </p>
            </div>

            <div
              className={[
                "rounded-xl border-dashed border flex flex-col items-center justify-center gap-3 px-4 py-12 text-center cursor-pointer transition",
                dragActive
                  ? "border-brand-400 bg-brand-600/5"
                  : "border-neutral-700/60 hover:border-brand-500/40 bg-neutral-950/40"
              ].join(" ")}
              onClick={openPicker}
            >
              <input
                ref={inputRef}
                type="file"
                accept={accept}
                className="hidden"
                onChange={handleSelect}
              />
              <div className="flex flex-col items-center gap-2">
                <div
                  className="h-12 w-12 rounded-full flex items-center justify-center
                      bg-gradient-to-br from-brand-500/20 to-brand-600/10 ring-1 ring-inset ring-brand-500/30"
                >
                  <svg
                    className="h-6 w-6 text-brand-300"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.6}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 7.5 12 3m0 0L7.5 7.5M12 3v13.5"
                    />
                  </svg>
                </div>
                <p className="text-sm">
                  <span className="text-brand-300">Click to browse</span> or
                  drag & drop
                </p>
                <p className="text-[0.65rem] text-neutral-500 font-medium uppercase tracking-wide">
                  {accept.split(",").slice(0, 4).join(" • ")}{" "}
                  {accept.split(",").length > 4 && "…"} • Max {maxSizeMB}MB
                </p>
              </div>
              {file && (
                <div className="mt-4 w-full max-w-sm text-left space-y-2">
                  <div className="flex items-center justify-between text-[0.65rem] text-neutral-400">
                    <span className="truncate max-w-[60%]">{file.name}</span>
                    <span>{(file.size / 1024).toFixed(0)} KB</span>
                  </div>
                  <div className="h-2 w-full rounded bg-neutral-800 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-brand-400 via-brand-500 to-brand-600 transition-all duration-300"
                      style={{
                        width: `${Math.round(
                          (pending?.progress ?? (file ? 0.08 : 0)) * 100
                        )}%`
                      }}
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={removeFile}
                      className="text-[0.6rem] text-neutral-500 hover:text-neutral-300 transition"
                    >
                      Clear
                    </button>
                    {pending?.progress === 1 && (
                      <span className="text-[0.6rem] text-brand-300 uppercase tracking-wide">
                        Uploaded
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-3 text-[0.6rem] text-neutral-500">
              <span className="badge bg-neutral-800/60 ring-white/5 text-neutral-300">
                Secure (demo)
              </span>
              <span className="badge bg-neutral-800/60 ring-white/5 text-neutral-300">
                Private
              </span>
              <span className="badge bg-neutral-800/60 ring-white/5 text-neutral-300">
                Fast Mock
              </span>
            </div>

            {error && (
              <p className="text-[0.65rem] text-red-400 font-medium">{error}</p>
            )}
            {successId && !error && (
              <p className="text-[0.65rem] text-emerald-400 font-medium">
                Upload successful. ID:{" "}
                <code className="text-emerald-300">{successId}</code>
              </p>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={!file || !!pending}
                className="btn disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {pending
                  ? pending.progress < 1
                    ? `Uploading ${Math.round(pending.progress * 100)}%`
                    : "Finalizing..."
                  : "Upload"}
              </button>
              {file && !pending && (
                <button
                  type="button"
                  onClick={removeFile}
                  className="btn-outline disabled:opacity-40"
                >
                  Remove
                </button>
              )}
              {successId && (
                <button
                  type="button"
                  onClick={reset}
                  className="btn-outline text-[0.65rem]"
                >
                  New Upload
                </button>
              )}
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
