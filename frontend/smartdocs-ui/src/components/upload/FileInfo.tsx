import React from "react";
import { ProgressBar } from "./ProgressBar";

/**
 * FileInfo
 *
 * Displays selected file metadata (name, size) plus upload progress and
 * lightweight actions (clear/remove). Purely presentational; all state
 * mutations must be supplied via props.
 */
export interface FileInfoProps {
  file: File | null;
  /**
   * Current progress fraction (0..1). When undefined and file exists,
   * a minimal placeholder bar (e.g. initial 8%) can be shown by parent.
   */
  progress?: number;
  /**
   * True when upload in-flight and not yet completed.
   */
  uploading: boolean;
  /**
   * True when progress reached 100% (post finalize).
   */
  complete: boolean;
  /**
   * Invoked to remove / clear current file.
   */
  onClear: () => void;
  /**
   * Optional additional className.
   */
  className?: string;
  /**
   * Optional label override for the clear control.
   */
  clearLabel?: string;
  /**
   * If provided, renders a right-aligned status badge (e.g. "Uploaded").
   */
  statusLabel?: string | null;
}

export const FileInfo: React.FC<FileInfoProps> = ({
  file,
  progress = 0,
  uploading,
  complete,
  onClear,
  className = "",
  clearLabel = "Clear",
  statusLabel
}) => {
  if (!file) return null;

  const sizeKB = (file.size / 1024).toFixed(0);

  return (
    <div
      className={["mt-4 w-full max-w-sm text-left space-y-2", className].join(
        " "
      )}
    >
      <div className="flex items-center justify-between text-[0.65rem] text-neutral-400">
        <span className="truncate max-w-[60%]" title={file.name}>
          {file.name}
        </span>
        <span>{sizeKB} KB</span>
      </div>
      <ProgressBar
        value={progress}
        complete={complete}
        aria-label="File upload progress"
      />
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onClear}
          className="text-[0.6rem] text-neutral-500 hover:text-neutral-300 transition"
          disabled={uploading}
        >
          {clearLabel}
        </button>
        {statusLabel && (
          <span className="text-[0.6rem] text-brand-300 uppercase tracking-wide">
            {statusLabel}
          </span>
        )}
      </div>
    </div>
  );
};
