import React from "react";

/**
 * DropZone
 *
 * Presentational, accessible drag & drop + click-to-select area.
 * Does NOT own upload logic; expects parent (or hook) to supply handlers & state.
 *
 * Accessibility:
 * - role="button" + tabIndex=0 for keyboard focus
 * - Space / Enter trigger openPicker
 * - ARIA live announcement hook via ariaStatus (optional)
 */
export interface DropZoneProps {
  accept: string;
  maxSizeMB: number;
  dragActive: boolean;
  file: File | null;
  /**
   * True when upload is in-flight (disables selecting new file).
   */
  disabled?: boolean;

  /**
   * Current progress fraction (0..1) to optionally drive visual hints (not rendered here).
   */
  progress?: number;

  /**
   * Trigger native file picker (hook provided).
   */
  openPicker: () => void;

  /**
   * Handler from hook for file input change.
   */
  onSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;

  /**
   * Drag handlers from hook.
   */
  onDrag: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;

  /**
   * Input ref from hook so parent can clear it.
   */
  inputRef: React.RefObject<HTMLInputElement | null>;

  /**
   * Optional children rendered beneath the base prompt (e.g. FileInfo, status messages).
   */
  children?: React.ReactNode;

  /**
   * Optional custom className for root container.
   */
  className?: string;

  /**
   * Optional ARIA status text to be announced (consumer can manage a visually hidden region).
   */
  ariaStatus?: string;
}

export const DropZone: React.FC<DropZoneProps> = ({
  accept,
  maxSizeMB,
  dragActive,
  file,
  disabled,
  progress,
  openPicker,
  onSelect,
  onDrag,
  onDrop,
  inputRef,
  children,
  className = "",
  ariaStatus
}) => {
  // Derive simple booleans for data attributes (helps styling / debugging, satisfies lint for unused vars)
  const hasFile = !!file;
  const pct =
    typeof progress === "number" ? Math.max(0, Math.min(1, progress)) : null;

  return (
    <div
      onDragEnter={onDrag}
      onDragOver={onDrag}
      onDragLeave={onDrag}
      onDrop={onDrop}
      data-has-file={hasFile ? "true" : "false"}
      data-progress={pct !== null ? pct.toFixed(2) : undefined}
      className={[
        "relative group rounded-2xl border transition-colors overflow-hidden",
        "bg-neutral-900/50 backdrop-blur-sm border-white/5",
        dragActive ? "border-brand-400/60" : "hover:border-brand-500/30",
        className
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
            Drag and drop a file or browse from your device. Once uploaded, you
            can open the Chat to ask contextual questions.
          </p>
        </div>

        <div
          className={[
            "rounded-xl border-dashed border flex flex-col items-center justify-center gap-3 px-4 py-12 text-center cursor-pointer transition",
            dragActive
              ? "border-brand-400 bg-brand-600/5"
              : "border-neutral-700/60 hover:border-brand-500/40 bg-neutral-950/40",
            disabled ? "opacity-60 pointer-events-none" : "",
            // Accessible focus outline (removed outline-none; provide custom ring)
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-900"
          ].join(" ")}
          role="button"
          tabIndex={0}
          aria-disabled={disabled ? "true" : "false"}
          aria-label="File upload drop zone. Press Enter or Space to open file picker."
          onClick={() => {
            if (!disabled) openPicker();
          }}
          onKeyDown={(e) => {
            if (disabled) return;
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              openPicker();
            }
          }}
          data-drag-active={dragActive ? "true" : "false"}
        >
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={onSelect}
            aria-hidden="true"
            tabIndex={-1}
            disabled={disabled}
          />
          <div className="flex flex-col items-center gap-2 select-none">
            <div
              className="h-12 w-12 rounded-full flex items-center justify-center
                  bg-gradient-to-br from-brand-500/20 to-brand-600/10 ring-1 ring-inset ring-brand-500/30"
              aria-hidden="true"
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
              <span className="text-brand-300">Click to browse</span> or drag &
              drop
            </p>
            <p className="text-[0.65rem] text-neutral-500 font-medium uppercase tracking-wide">
              {accept.split(",").slice(0, 4).join(" • ")}{" "}
              {accept.split(",").length > 4 && "…"} • Max {maxSizeMB}MB
            </p>
          </div>

          {/* Slot for file info / progress elements */}
          {children}
        </div>

        {/* Badges replicate original design; could be made configurable later */}
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

        {/* Optional ARIA status region consumer can drive */}
        {(ariaStatus || dragActive) && (
          <p
            className="sr-only"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            {dragActive
              ? "Drag active. Release to select file."
              : ariaStatus || ""}
          </p>
        )}
      </div>
    </div>
  );
};
